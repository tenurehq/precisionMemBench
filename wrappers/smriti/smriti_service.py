"""
Smriti — PrecisionMemBench Wrapper
====================================
Self-contained FastAPI service implementing the PrecisionMemBench
three-endpoint contract (/add, /search, /reset) for Smriti, the
temporal memory layer from Chronos OS.

  Source:  https://github.com/RemanenetSpy/chronos-os
  Author:  Reman (Spy9191)

No external dependencies beyond chromadb and sentence-transformers —
everything runs in-process with a local ChromaDB vector store.

Environment variables:
  SMRITI_SIMILARITY_THRESHOLD   cosine-distance cutoff   (default 0.45)
  SMRITI_EMBED_MODEL            sentence-transformer     (default all-MiniLM-L6-v2)
"""

from __future__ import annotations

import os
import functools
import logging
import time
from typing import Optional

# ── Silence HF network checks (model pre-cached in image) ────────────────────
os.environ["HF_HUB_OFFLINE"]           = "1"
os.environ["TRANSFORMERS_OFFLINE"]     = "1"
os.environ["HF_DATASETS_OFFLINE"]      = "1"
os.environ["ANONYMIZED_TELEMETRY"]     = "False"
os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"
# ─────────────────────────────────────────────────────────────────────────────

import chromadb
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("smriti.wrapper")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EMBED_MODEL          = os.getenv("SMRITI_EMBED_MODEL", "all-MiniLM-L6-v2")
PORT                 = int(os.getenv("SMRITI_PORT", "8080"))
SIMILARITY_THRESHOLD = float(os.getenv("SMRITI_SIMILARITY_THRESHOLD", "0.45"))

# ---------------------------------------------------------------------------
# Embedding model  (loaded once at startup — cached inside the Docker image)
# ---------------------------------------------------------------------------

print(f"[smriti] Loading embedding model: {EMBED_MODEL} …", flush=True)
_model = SentenceTransformer(EMBED_MODEL)
print(f"[smriti] Model ready.  threshold={SIMILARITY_THRESHOLD}", flush=True)


@functools.lru_cache(maxsize=512)
def _embed_cached(text: str) -> tuple:
    """LRU-cached embedding — avoids re-encoding repeated query strings."""
    return tuple(_model.encode(text, normalize_embeddings=True).tolist())


def _embed(text: str) -> list[float]:
    return list(_embed_cached(text))


# ---------------------------------------------------------------------------
# In-process vector store (ChromaDB ephemeral client)
# ---------------------------------------------------------------------------

def _new_chroma_client() -> chromadb.ClientAPI:
    return chromadb.Client(chromadb.Settings(anonymized_telemetry=False))


_chroma: chromadb.ClientAPI                               = _new_chroma_client()
_collections: dict[str, chromadb.Collection]              = {}   # user_id → Collection
_belief_map:  dict[str, dict[str, str]]                   = {}   # user_id → {beliefId: doc}


def _get_or_create_collection(user_id: str) -> chromadb.Collection:
    if user_id not in _collections:
        safe = user_id.replace(":", "_").replace("-", "_")[:50]
        name = f"smriti_{safe}"
        try:
            col = _chroma.get_collection(name)
        except Exception:
            col = _chroma.create_collection(name, metadata={"hnsw:space": "cosine"})
        _collections[user_id] = col
    return _collections[user_id]


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Smriti · PrecisionMemBench Wrapper",
    version="1.0.0",
    description=(
        "Temporal memory layer from Chronos OS. "
        "Source: https://github.com/RemanenetSpy/chronos-os"
    ),
)


# ── Request / Response models ────────────────────────────────────────────────

class AddRequest(BaseModel):
    text:     str
    user_id:  str
    metadata: dict = {}


class SearchRequest(BaseModel):
    query:   str
    user_id: str
    limit:   int = 20


# ── POST /add ────────────────────────────────────────────────────────────────

@app.post("/add")
async def add(req: AddRequest):
    """Ingest a single belief into Smriti's vector store."""
    belief_id = req.metadata.get("beliefId") or req.metadata.get("belief_id")
    if not belief_id:
        return JSONResponse({"ok": False, "error": "metadata.beliefId is required"}, status_code=400)

    embedding = _embed(req.text)
    col       = _get_or_create_collection(req.user_id)

    col.upsert(
        ids        =[belief_id],
        embeddings =[embedding],
        documents  =[req.text],
        metadatas  =[{"beliefId": belief_id, "user_id": req.user_id}],
    )

    # Also persist in the in-process dict for fast id resolution
    _belief_map.setdefault(req.user_id, {})[belief_id] = req.text

    return {"ok": True}


# ── POST /search ─────────────────────────────────────────────────────────────

@app.post("/search")
async def search(req: SearchRequest):
    """Search for beliefs by query text, scoped to a user_id."""
    if not req.query.strip():
        return {"results": []}

    if req.user_id not in _collections:
        return {"results": []}

    col   = _collections[req.user_id]
    count = col.count()
    if count == 0:
        return {"results": []}

    n = min(req.limit * 3, count)   # over-fetch, then threshold-filter

    try:
        res = col.query(
            query_embeddings=[ _embed(req.query) ],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        logger.warning(f"ChromaDB query error: {e}")
        return {"results": []}

    output: list[dict] = []
    seen:   set[str]   = set()

    for doc, meta, dist in zip(
        res["documents"][0],
        res["metadatas"][0],
        res["distances"][0],
    ):
        if dist > SIMILARITY_THRESHOLD:
            continue

        bid = meta.get("beliefId", "")
        if not bid or bid in seen:
            continue
        seen.add(bid)

        output.append({
            "id":     bid,
            "memory": doc,
            "score":  round(1.0 - dist, 6),
        })

        if len(output) >= req.limit:
            break

    return {"results": output}


# ── DELETE /reset ─────────────────────────────────────────────────────────────

@app.delete("/reset")
async def reset():
    """Clear all stored beliefs for all users."""
    global _chroma, _collections, _belief_map
    try:
        for col in _chroma.list_collections():
            _chroma.delete_collection(col.name)
    except Exception:
        pass
    _chroma      = _new_chroma_client()
    _collections  = {}
    _belief_map   = {}
    _embed_cached.cache_clear()
    return {"ok": True}


# ── GET /health ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status":      "ok",
        "model":       EMBED_MODEL,
        "threshold":   SIMILARITY_THRESHOLD,
        "users":       len(_collections),
        "beliefs":     sum(len(v) for v in _belief_map.values()),
    }


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"[smriti] Listening on port {PORT}", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")

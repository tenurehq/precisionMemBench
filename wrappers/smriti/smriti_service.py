"""
Smriti — PrecisionMemBench Wrapper
====================================
Self-contained FastAPI adapter for the Smriti Temporal Memory Layer.
Instead of running heavy models locally, this proxies benchmark 
requests directly to the remote Smriti API provider.

Source Repository: https://github.com/RemanenetSpy/smriti
"""

import os
import logging
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("smriti.wrapper")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PORT = int(os.getenv("SMRITI_PORT", "8080"))
SMRITI_API_URL = os.getenv("SMRITI_API_URL", "https://spy9191-chronos-api-backend.hf.space")
SMRITI_API_KEY = os.getenv("SMRITI_API_KEY", "")
SIMILARITY_THRESHOLD = float(os.getenv("SMRITI_SIMILARITY_THRESHOLD", "0.45"))

_client: httpx.AsyncClient | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _client
    _client = httpx.AsyncClient(
        base_url=SMRITI_API_URL,
        headers={"X-API-Key": SMRITI_API_KEY, "Content-Type": "application/json"},
        timeout=httpx.Timeout(30.0),
    )
    yield
    await _client.aclose()

app = FastAPI(
    title="Smriti · PrecisionMemBench Adapter",
    version="1.0.0",
    description="Adapter for Smriti API (https://github.com/RemanenetSpy/smriti)",
    lifespan=lifespan,
)

# ── Request Models ────────────────────────────────────────────────────────────

class AddRequest(BaseModel):
    text: str
    user_id: str
    metadata: dict = {}

class SearchRequest(BaseModel):
    query: str
    user_id: str
    limit: int = 20

# ── POST /add ────────────────────────────────────────────────────────────────

@app.post("/add")
async def add(req: AddRequest):
    """Forward an event ingestion request to the remote Smriti API."""
    belief_id = req.metadata.get("beliefId") or req.metadata.get("belief_id")
    if not belief_id:
        return JSONResponse({"ok": False, "error": "metadata.beliefId is required"}, status_code=400)

    # Translate to Smriti's /ingest format
    smriti_payload = {
        "source_id": f"bench-{req.user_id}",
        "scope": req.user_id,
        "parse_svo": False,
        "events": [{
            "text": req.text,
            "metadata": {"beliefId": belief_id, "user_id": req.user_id}
        }]
    }

    try:
        r = await _client.post("/ingest", json=smriti_payload)
        r.raise_for_status()
    except Exception as e:
        logger.error(f"Smriti API error during /add: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=502)

    return {"ok": True}

# ── POST /search ─────────────────────────────────────────────────────────────

@app.post("/search")
async def search(req: SearchRequest):
    """Forward a search query to the remote Smriti API."""
    if not req.query.strip():
        return {"results": []}

    smriti_payload = {
        "query": req.query,
        "scope": req.user_id,
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "max_results": req.limit,
        "semantic_weight": 1.0,
    }

    try:
        r = await _client.post("/query", json=smriti_payload)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning(f"Smriti API error during /search: {e}")
        return {"results": []}

    # Map Smriti results back to PrecisionMemBench format
    output = []
    seen = set()

    for item in data.get("results", []):
        event = item.get("event", {})
        meta = event.get("metadata", {})
        bid = meta.get("beliefId", "")
        
        if not bid or bid in seen:
            continue
            
        seen.add(bid)
        output.append({
            "id": bid,
            "memory": event.get("raw_text", "") or event.get("text", ""),
            "score": item.get("relevance_score", 0.0),
        })

        if len(output) >= req.limit:
            break

    return {"results": output}

# ── DELETE /reset ─────────────────────────────────────────────────────────────

@app.delete("/reset")
async def reset():
    """PrecisionMemBench relies on scoped user_ids per test. 
    The Smriti cloud API automatically isolates by scope, so no global reset is needed."""
    return {"ok": True}

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("smriti_service:app", host="0.0.0.0", port=PORT, log_level="warning")

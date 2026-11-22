"""PrecisionMemBench wrapper for hippo: maps /add, /search and /reset onto `hippo serve`'s HTTP API."""

import json
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

BASE = os.getenv("HIPPO_URL", "http://127.0.0.1:6789").rstrip("/")
KEY_FILE = Path(os.getenv("HIPPO_KEY_FILE", "/data/key.json"))
TIMEOUT = float(os.getenv("HIPPO_TIMEOUT_SECONDS", "60"))

app = FastAPI()
# hippo's recall rows carry no caller metadata, so beliefIds are kept by hippo memory id.
_belief_map: dict[str, str] = {}


class Metadata(BaseModel):
    beliefId: str
    scope: str = ""


class AddRequest(BaseModel):
    text: str
    user_id: str
    metadata: Metadata


class SearchRequest(BaseModel):
    query: str
    user_id: str
    limit: int = 20
    scope: str = ""


def hippo_scope(user_id: str, scope: str) -> str:
    # hippo filters recall by one scope string; the user keeps users apart, the belief scope keeps domains apart.
    return f"{user_id}/{scope}" if scope else user_id


def call(method: str, path: str, **kwargs) -> dict:
    # The hippo container mints a new key on each start, so it is read per call.
    headers = {"Authorization": f"Bearer {json.loads(KEY_FILE.read_text())['plaintext']}"}
    try:
        response = httpx.request(method, f"{BASE}{path}", headers=headers, timeout=TIMEOUT, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else {}
    except (httpx.HTTPError, OSError) as exc:
        raise HTTPException(status_code=502, detail=f"hippo {method} {path}: {exc}") from exc


@app.post("/add")
def add(req: AddRequest):
    scope = hippo_scope(req.user_id, req.metadata.scope)
    data = call("POST", "/v1/memories", json={"content": req.text, "scope": scope})
    _belief_map[data["id"]] = req.metadata.beliefId
    return {"ok": True}


@app.post("/search")
def search(req: SearchRequest):
    scope = hippo_scope(req.user_id, req.scope)
    data = call("GET", "/v1/memories", params={"q": req.query, "limit": req.limit, "scope": scope})
    results, seen = [], set()
    for row in data.get("results", []):
        belief = _belief_map.get(row["id"])
        if belief is None or belief in seen:
            continue
        seen.add(belief)
        results.append({"id": belief, "memory": row["content"], "score": row.get("score", 0.0)})
    return {"results": results}


@app.delete("/reset")
def reset():
    for memory_id in list(_belief_map):
        call("DELETE", f"/v1/memories/{memory_id}")
        del _belief_map[memory_id]
    return {"ok": True}


@app.get("/health")
def health():
    return call("GET", "/health")

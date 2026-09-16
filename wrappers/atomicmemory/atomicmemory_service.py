import logging
import os

import httpx2
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("uvicorn.error")

ATOMICMEMORY_URL = os.getenv("ATOMICMEMORY_URL", "http://localhost:17350")
API_KEY = os.getenv("ATOMICMEMORY_API_KEY", "local-dev-key")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

TIMEOUT = httpx2.Timeout(120.0)

app = FastAPI()
id_map: dict[str, str] = {}


class Metadata(BaseModel):
    beliefId: str
    scope: str


class AddRequest(BaseModel):
    text: str
    user_id: str
    metadata: Metadata


class SearchRequest(BaseModel):
    query: str
    user_id: str
    limit: int = 20
    scope: str


def atomicmemory_request(method: str, path: str, **kwargs) -> httpx2.Response:
    url = f"{ATOMICMEMORY_URL}{path}"
    try:
        with httpx2.Client(
            headers=HEADERS,
            timeout=TIMEOUT,
            trust_env=False,
        ) as client:
            response = client.request(method, url, **kwargs)
        response.raise_for_status()
        return response
    except httpx2.TimeoutException as exc:
        logger.exception(
            "AtomicMemory request timed out: %s %s",
            method,
            url,
        )
        raise HTTPException(
            status_code=504,
            detail="AtomicMemory request timed out",
        ) from exc
    except httpx2.HTTPStatusError as exc:
        logger.error(
            "AtomicMemory returned HTTP %s for %s %s: %s",
            exc.response.status_code,
            method,
            url,
            exc.response.text[:2000],
        )
        raise HTTPException(
            status_code=502,
            detail=f"AtomicMemory returned HTTP {exc.response.status_code}",
        ) from exc
    except httpx2.RequestError as exc:
        logger.exception(
            "AtomicMemory request failed: %s %s: %r",
            method,
            url,
            exc,
        )
        raise HTTPException(
            status_code=502,
            detail="AtomicMemory request failed",
        ) from exc


def atomicmemory_json(method: str, path: str, **kwargs) -> dict:
    response = atomicmemory_request(method, path, **kwargs)
    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail="AtomicMemory returned an invalid JSON response",
        ) from exc
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=502,
            detail="AtomicMemory returned an unexpected JSON response",
        )
    return data


@app.post("/add")
def add(req: AddRequest):
    belief_id = req.metadata.beliefId
    payload = {
        "user_id": req.user_id,
        "conversation": f"user: {req.text}",
        "source_site": "precisionmembench",
        "agent_scope": req.metadata.scope,
    }
    data = atomicmemory_json("POST", "/v1/memories/ingest", json=payload)
    if belief_id:
        for internal_id in data.get("stored_memory_ids", []):
            id_map[internal_id] = belief_id
        for internal_id in data.get("updated_memory_ids", []):
            id_map[internal_id] = belief_id
    return {"ok": True}


@app.post("/search")
def search(req: SearchRequest):
    payload = {
        "user_id": req.user_id,
        "query": req.query,
        "limit": req.limit,
        "agent_scope": req.scope,
    }
    data = atomicmemory_json("POST", "/v1/memories/search", json=payload)
    memories = data.get("memories", [])

    normalized = []
    seen = set()
    for r in memories:
        internal_id = r.get("id")
        belief_id = id_map.get(internal_id)
        if not belief_id or belief_id in seen:
            continue
        seen.add(belief_id)
        normalized.append(
            {
                "id": belief_id,
                "memory": r.get("content", ""),
                "score": r.get("score", r.get("similarity", 1.0)),
            }
        )

    return {"results": normalized}


@app.delete("/reset")
def reset():

    data = atomicmemory_json(
        "POST",
        "/v1/memories/search",
        json={"query": "*", "limit": 1000},
    )
    memories = data.get("memories", [])
    for m in memories:
        memory_id = m.get("id")
        if memory_id:
            atomicmemory_request("DELETE", f"/v1/memories/{memory_id}")
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)

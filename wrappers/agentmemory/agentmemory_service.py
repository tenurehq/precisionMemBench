import os

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

BASE = os.getenv("AGENTMEMORY_URL", "http://127.0.0.1:3111").rstrip("/")
TIMEOUT = float(os.getenv("AGENTMEMORY_TIMEOUT_SECONDS", "180"))

app = FastAPI()
_belief_map: dict[str, str] = {}


class Metadata(BaseModel):
    beliefId: str
    scope: str = ""


class AddRequest(BaseModel):
    text: str
    user_id: str
    metadata: Metadata
    aliases: list[str] = Field(default_factory=list)


class SearchRequest(BaseModel):
    query: str
    user_id: str
    limit: int = 20
    scope: str = ""


class UpdateRequest(BaseModel):
    beliefId: str
    text: str
    user_id: str
    metadata: dict = Field(default_factory=dict)


def post(path: str, payload: dict) -> dict:
    try:
        response = httpx.post(f"{BASE}{path}", json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json() if response.content else {}
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=502, detail="AgentMemory returned invalid JSON"
        ) from exc


def memory_id(data: dict) -> str | None:
    value = (
        (data.get("memory") or {}).get("id") or data.get("id") or data.get("memoryId")
    )
    return str(value) if value is not None else None


@app.post("/add")
def add(req: AddRequest):

    print(f"{BASE}")

    data = post(
        "/agentmemory/remember",
        {
            "content": req.text,
            "project": req.metadata.scope,
            "agentId": req.user_id,
            "title": req.metadata.beliefId,
            "metadata": {
                "beliefId": req.metadata.beliefId,
                "scope": req.metadata.scope,
            },
            "concepts": req.aliases,
        },
    )
    mem_id = memory_id(data)
    if mem_id:
        _belief_map[mem_id] = req.metadata.beliefId
    return {"ok": True}


@app.put("/update")
def update(req: UpdateRequest):
    mem_id = next(
        (key for key, value in _belief_map.items() if value == req.beliefId), None
    )
    if mem_id is None:
        raise HTTPException(
            status_code=404, detail=f"beliefId {req.beliefId} not in belief map"
        )

    post("/agentmemory/forget", {"memoryId": mem_id})
    _belief_map.pop(mem_id, None)

    scope = str(req.metadata.get("scope", ""))
    data = post(
        "/agentmemory/remember",
        {
            "content": req.text,
            "project": scope,
            "agentId": req.user_id,
            "title": req.beliefId,
            "metadata": {
                "beliefId": req.beliefId,
                "scope": scope,
            },
        },
    )
    new_id = memory_id(data)
    if new_id:
        _belief_map[new_id] = req.beliefId
    return {"ok": True}


@app.post("/search")
def search(req: SearchRequest):
    data = post(
        "/agentmemory/smart-search",
        {
            "query": req.query,
            "project": req.scope,
            "agentId": req.user_id,
            "limit": req.limit,
        },
    )
    memories = data.get("results") or data.get("memories") or []
    results = []
    seen = set()
    for item in memories:
        observation = item.get("observation") or item
        belief_id = (observation.get("metadata") or {}).get("beliefId")
        if not belief_id:
            source_id = (
                item.get("obsId") or item.get("id") or observation.get("id") or ""
            )
            belief_id = _belief_map.get(str(source_id))
        if not belief_id or belief_id in seen:
            continue
        seen.add(belief_id)
        results.append(
            {
                "id": belief_id,
                "memory": observation.get("content")
                or observation.get("narrative")
                or observation.get("memory", ""),
                "score": item.get("score", 1.0),
                "metadata": {"beliefId": belief_id},
            }
        )
    return {"results": results}


@app.delete("/reset")
def reset():
    _belief_map.clear()
    post("/agentmemory/governance/bulk-delete", {"all": True})
    return {"ok": True}

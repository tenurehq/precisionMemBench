import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agentic_memory.memory_system import AgenticMemorySystem
import os

LLM_BACKEND = os.getenv("AMEM_LLM_BACKEND", "openai")
LLM_MODEL   = os.getenv("AMEM_LLM_MODEL",   "gpt-4o-mini")
EMBED_MODEL = os.getenv("AMEM_EMBED_MODEL",  "all-MiniLM-L6-v2")

app = FastAPI()

_systems: dict[str, AgenticMemorySystem] = {}
_belief_map: dict[str, dict[str, str]] = {}


def _get_system(user_id: str) -> AgenticMemorySystem:
    if user_id not in _systems:
        _systems[user_id] = AgenticMemorySystem(
            model_name=EMBED_MODEL,
            llm_backend=LLM_BACKEND,
            llm_model=LLM_MODEL,
        )
        _belief_map[user_id] = {}
    return _systems[user_id]


class AddRequest(BaseModel):
    text: str
    user_id: str
    metadata: dict = {}


class SearchRequest(BaseModel):
    query: str
    user_id: str
    limit: int = 20


class UpdateRequest(BaseModel):
    beliefId: str
    text: str
    user_id: str
    metadata: dict = {}


@app.post("/add")
def add(req: AddRequest):
    system = _get_system(req.user_id)
    belief_id = req.metadata.get("beliefId")

    amem_id = system.add_note(req.text)

    if belief_id and amem_id:
        _belief_map[req.user_id][belief_id] = amem_id

    return {"ok": True}


@app.put("/update")
def update(req: UpdateRequest):
    system = _get_system(req.user_id)
    user_map = _belief_map.get(req.user_id, {})
    amem_id = user_map.get(req.beliefId)

    if amem_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"beliefId {req.beliefId} not found for user {req.user_id}",
        )

    system.update(amem_id, content=req.text)
    return {"ok": True}


@app.post("/search")
def search(req: SearchRequest):
    system = _get_system(req.user_id)
    user_map = _belief_map.get(req.user_id, {})

    inv_map = {v: k for k, v in user_map.items()}

    raw = system.search_agentic(req.query, k=req.limit)

    results = []
    seen: set[str] = set()
    for m in raw:
        amem_id = m.get("id")
        belief_id = inv_map.get(amem_id)
        if not belief_id or belief_id in seen:
            continue
        seen.add(belief_id)
        results.append({
            "id": belief_id,
            "memory": m.get("content", ""),
            "score": m.get("score", 1.0),
            "metadata": {"beliefId": belief_id},
        })

    return {"results": results}


@app.delete("/reset")
def reset():
    for user_id, system in list(_systems.items()):
        user_map = _belief_map.get(user_id, {})
        for amem_id in list(user_map.values()):
            try:
                system.delete(amem_id)
            except Exception:
                pass

    _systems.clear()
    _belief_map.clear()
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)
import os

from agentic_memory.memory_system import AgenticMemorySystem
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

LLM_BACKEND = os.getenv("AMEM_LLM_BACKEND", "openai")
LLM_MODEL = os.getenv("AMEM_LLM_MODEL", "gpt-4o-mini")
EMBED_MODEL = os.getenv("AMEM_EMBED_MODEL", "all-MiniLM-L6-v2")

app = FastAPI()

_system = AgenticMemorySystem(
    model_name=EMBED_MODEL,
    llm_backend=LLM_BACKEND,
    llm_model=LLM_MODEL,
)
_belief_to_amem: dict[str, str] = {}
_amem_to_belief: dict[str, str] = {}


class AddRequest(BaseModel):
    text: str
    user_id: str
    metadata: dict = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query: str
    user_id: str
    limit: int = 20


class UpdateRequest(BaseModel):
    beliefId: str
    text: str
    user_id: str
    metadata: dict = Field(default_factory=dict)


@app.post("/add")
def add(req: AddRequest):
    amem_id = _system.add_note(req.text)
    belief_id = req.metadata.get("beliefId")

    if belief_id and amem_id:
        _belief_to_amem[belief_id] = amem_id
        _amem_to_belief[amem_id] = belief_id

    return {"ok": True}


@app.put("/update")
def update(req: UpdateRequest):
    amem_id = _belief_to_amem.get(req.beliefId)

    if amem_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"beliefId {req.beliefId} not found",
        )

    _system.update(amem_id, content=req.text)
    return {"ok": True}


@app.post("/search")
def search(req: SearchRequest):
    raw = _system.search_agentic(req.query, k=req.limit)

    results = []
    seen: set[str] = set()

    for memory in raw:
        amem_id = memory.get("id")
        belief_id = _amem_to_belief.get(amem_id)

        if not belief_id or belief_id in seen:
            continue

        seen.add(belief_id)
        results.append(
            {
                "id": belief_id,
                "memory": memory.get("content", ""),
                "score": memory.get("score", 1.0),
                "metadata": {"beliefId": belief_id},
            }
        )

    return {"results": results}


@app.delete("/reset")
def reset():
    for amem_id in list(_amem_to_belief):
        try:
            _system.delete(amem_id)
        except Exception:
            pass

    _belief_to_amem.clear()
    _amem_to_belief.clear()
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8083)

import logging

from fastapi import FastAPI, HTTPException
from mnemosyne import Mnemosyne
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOP_K = 6
app = FastAPI()
_belief_map: dict[str, str] = {}
_mem_instances: dict[str, Mnemosyne] = {}


def _get_mem(user_id: str) -> Mnemosyne:
    if user_id not in _mem_instances:
        _mem_instances[user_id] = Mnemosyne(author_id=user_id)
    return _mem_instances[user_id]


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


class UpdateRequest(BaseModel):
    beliefId: str
    text: str
    user_id: str
    metadata: dict = {}


def _is_universal(scope: str) -> bool:
    return scope == "user:universal"


@app.post("/add")
def add(req: AddRequest):
    mem = _get_mem(req.user_id)
    memory_id = mem.remember(
        content=req.text,
        source="benchmark",
        importance=0.7,
        scope="global" if _is_universal(req.metadata.scope) else None,
    )
    print(memory_id)
    if memory_id and req.metadata.beliefId:
        _belief_map[memory_id] = req.metadata.beliefId
    return {"ok": True}


@app.put("/update")
def update(req: UpdateRequest):
    memory_id = next((k for k, v in _belief_map.items() if v == req.beliefId), None)
    if memory_id is None:
        raise HTTPException(
            status_code=404, detail=f"beliefId {req.beliefId} not in belief map"
        )
    mem = _get_mem(req.user_id)
    mem.update(memory_id=memory_id, content=req.text)
    return {"ok": True}


@app.get("/debug/beliefs")
def debug_beliefs():
    all_beliefs = []
    for user_id, mem in _mem_instances.items():
        memories = mem.recall(query="", top_k=1000)
        all_beliefs.append(
            {
                "user_id": user_id,
                "count": len(memories),
                "memories": memories,
            }
        )
    return {
        "belief_map_count": len(_belief_map),
        "belief_map": _belief_map,
        "instances": all_beliefs,
    }


@app.post("/search")
def search(req: SearchRequest):
    mem = _get_mem(req.user_id)
    memories = mem.recall(query=req.query, scope=req.scope)
    print(memories)
    results = []
    seen: set[str] = set()
    for m in memories:
        bid = _belief_map.get(m.get("id", ""))
        if not bid or bid in seen:
            continue
        seen.add(bid)
        results.append(
            {
                "id": bid,
                "memory": m.get("content", ""),
                "score": m.get("score", 1.0),
                "metadata": {"beliefId": bid},
            }
        )
    print("RESULTS")
    print(results)
    return {"results": results}


@app.delete("/reset")
def reset():
    for memory_id in list(_belief_map.keys()):
        for mem in _mem_instances.values():
            mem.forget(memory_id)
    _belief_map.clear()
    _mem_instances.clear()
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8082)

"""PrecisionMemBench adapter: transparent API only, no benchmark-specific logic."""
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from hingezero_memory import HingeZeroMemory, build_local_encoder
from HingeZero_Core import HZ_ALPHA, HZ_STEPS

app = FastAPI(title="HingeZero Memory")
store = HingeZeroMemory(
    build_local_encoder(),
    db_path=os.getenv("HZ_DATABASE", "/data/hingezero.sqlite3"),
    min_score=float(os.getenv("HZ_MIN_SCORE", "0.50")),
    steps=int(os.getenv("HZ_STEPS", "8")),
)

class AddRequest(BaseModel):
    text: str
    user_id: str
    metadata: dict = Field(default_factory=dict)
    aliases: list[str] | None = None

class SearchRequest(BaseModel):
    query: str
    user_id: str
    limit: int = 20
    scope: str | list[str] | None = None

@app.post("/add")
def add(req: AddRequest):
    belief_id = req.metadata.get("beliefId")
    if not isinstance(belief_id, str) or not belief_id.strip():
        raise HTTPException(422, "metadata.beliefId is required")
    try:
        store.add(req.text, req.user_id, belief_id, req.metadata, req.aliases)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"ok": True}

@app.post("/search")
def search(req: SearchRequest):
    try:
        return {"results": store.search(req.query, req.user_id, req.limit, req.scope)}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

@app.delete("/reset")
def reset():
    store.reset()
    return {"ok": True}

@app.get("/health")
def health():
    return {"ok": True, "engine": "original-HingeZero-Core",
            "witness": True, "retaining_loop": True,
            "steps": HZ_STEPS, "alpha": HZ_ALPHA}

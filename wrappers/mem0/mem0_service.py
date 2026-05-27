from fastapi import FastAPI
from pydantic import BaseModel
from mem0 import Memory
import uvicorn

import os

config = {
    "llm": {
        "provider": "openai",
        "config": {
            "model": os.getenv("LLM_MODEL", "us.anthropic.claude-sonnet-4-6"),
            "openai_base_url": os.getenv("LLM_BASE_URL", "http://localhost:8000/api/v1"),
            "api_key": os.getenv("LLM_API_KEY", "123456"),
            "top_p": None,
            "temperature": 0.1,
        },
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large"),
            "ollama_base_url": os.getenv("OLLAMA_URL", "http://localhost:11434"),
        },
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": os.getenv("QDRANT_COLLECTION", "tenure_eval"),
            "host": os.getenv("QDRANT_HOST", "qdrant"),
            "port": int(os.getenv("QDRANT_PORT", "6333")),
            "embedding_model_dims": int(os.getenv("EMBEDDING_DIMS", "1024")),
        },
    },
}

m = Memory.from_config(config)
app = FastAPI()


class AddRequest(BaseModel):
    text: str
    user_id: str
    metadata: dict = {}


class SearchRequest(BaseModel):
    query: str
    user_id: str
    limit: int = 20


@app.post("/add")
def add(req: AddRequest):
    m.add(req.text, user_id=req.user_id, metadata=req.metadata)
    return {"ok": True}


@app.post("/search")
def search(req: SearchRequest):
    response = m.search(req.query, filters={"user_id": req.user_id}, limit=req.limit)
    results = (
        response.get("results", response) if isinstance(response, dict) else response
    )

    normalized = []
    seen = set()
    for r in results:
        belief_id = r.get("metadata", {}).get("beliefId")
        if not belief_id or belief_id in seen:
            continue
        seen.add(belief_id)
        normalized.append(
            {
                "id": belief_id,
                "memory": r.get("memory", ""),
                "score": r.get("score", 1.0),
            }
        )

    return {"results": normalized}


@app.delete("/reset")
def reset():
    m.reset()
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)

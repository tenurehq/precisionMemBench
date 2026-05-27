import json

from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import uvicorn
import os

HINDSIGHT_URL = os.getenv("HINDSIGHT_URL", "http://hindsight:8888")
BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "default-bank")

app = FastAPI()
client = httpx.AsyncClient(base_url=HINDSIGHT_URL, timeout=120.0)


class AddRequest(BaseModel):
    text: str
    user_id: str
    metadata: dict = {}


class SearchRequest(BaseModel):
    query: str
    user_id: str
    limit: int = 20


@app.on_event("startup")
async def ensure_bank():
    for bank_id in ["test-user", "other-user", "brand-new-user"]:
        resp = await client.put(f"/v1/default/banks/{bank_id}", json={})
        print(f"ensure_bank {bank_id}: {resp.status_code} {resp.text}")
        resp.raise_for_status()


@app.post("/add")
async def add(req: AddRequest):
    response = await client.post(
        f"/v1/default/banks/{req.user_id}/memories",
        json={
            "items": [
                {
                    "content": req.text,
                    **({"context": str(req.metadata)} if req.metadata else {}),
                }
            ],
            "async": False,
        },
    )
    response.raise_for_status()
    return {"ok": True, "result": response.json()}


@app.post("/search")
async def search(req: SearchRequest):
    response = await client.post(
        f"/v1/default/banks/{req.user_id}/memories/recall",
        json={
            "query": req.query,
            "max_tokens": req.limit * 100,
        },
    )
    response.raise_for_status()
    data = response.json()
    memories = data.get("results", [])

    seen = set()
    normalized = []

    for memory in memories:
        ctx = memory.get("context")
        belief_id = None
        if ctx:
            try:
                parsed = json.loads(ctx.replace("'", '"'))
                belief_id = parsed.get("beliefId")
            except Exception:
                pass

        if not belief_id or belief_id in seen:
            continue

        seen.add(belief_id)
        normalized.append(
            {
                "id": belief_id,
                "memory": memory.get("content", ""),
                "score": memory.get("score", 1.0),
            }
        )

    return {"results": normalized}


@app.delete("/reset")
async def reset():
    for bank_id in ["test-user", "other-user", "brand-new-user"]:
        resp = await client.delete(f"/v1/default/banks/{bank_id}")
        if resp.status_code not in (200, 404):
            resp.raise_for_status()
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)

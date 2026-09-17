import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Any

import httpx2
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

HINDSIGHT_URL = os.getenv("HINDSIGHT_URL", "http://hindsight:8888")
BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "default-bank")

client = httpx2.AsyncClient(base_url=HINDSIGHT_URL, timeout=120.0)


class AddRequest(BaseModel):
    text: str
    user_id: str
    metadata: dict = {}


class UpdateRequest(BaseModel):
    beliefId: str
    text: str
    user_id: str
    metadata: dict = {}


class SearchRequest(BaseModel):
    query: str
    user_id: str
    limit: int = 20
    scope: str | list[str]


def normalize_scopes(scope: Any) -> list[str]:
    if isinstance(scope, str):
        return [scope] if scope else []

    if isinstance(scope, list):
        return [value for value in scope if isinstance(value, str) and value]

    return []


@asynccontextmanager
async def lifespan(app: FastAPI):
    bank_ids = ["test-user", "other-user", "brand-new-user"]

    for attempt in range(60):
        try:
            for bank_id in bank_ids:
                response = await client.put(
                    f"/v1/default/banks/{bank_id}",
                    json={},
                )
                response.raise_for_status()
                print(f"ensure_bank {bank_id}: {response.status_code} {response.text}")
            break
        except httpx2.HTTPError as error:
            if attempt == 59:
                await client.aclose()
                raise
            print(f"Hindsight unavailable, retry {attempt + 1}/60: {error}")
            await asyncio.sleep(2)

    try:
        yield
    finally:
        await client.aclose()


app = FastAPI(lifespan=lifespan)


@app.post("/add")
async def add(req: AddRequest):
    belief_id = req.metadata.get("beliefId")
    scope = req.metadata.get("scope")

    item: dict[str, Any] = {
        "content": req.text,
        "context": json.dumps(req.metadata),
    }

    if belief_id:
        item["document_id"] = belief_id

    if scope:
        item["tags"] = [scope]

    response = await client.post(
        f"/v1/default/banks/{req.user_id}/memories",
        json={
            "items": [item],
            "async": False,
        },
    )
    response.raise_for_status()
    return {"ok": True, "result": response.json()}


@app.put("/update")
async def update(req: UpdateRequest):
    metadata = {
        **req.metadata,
        "beliefId": req.beliefId,
    }

    item: dict[str, Any] = {
        "content": req.text,
        "context": json.dumps(metadata),
        "document_id": req.beliefId,
    }

    scope = metadata.get("scope")
    if scope:
        item["tags"] = [scope]

    response = await client.post(
        f"/v1/default/banks/{req.user_id}/memories",
        json={
            "items": [item],
            "async": False,
        },
    )
    response.raise_for_status()
    return {"ok": True, "result": response.json()}


@app.post("/search")
async def search(req: SearchRequest):
    scopes = normalize_scopes(req.scope)

    response = await client.post(
        f"/v1/default/banks/{req.user_id}/memories/recall",
        json={
            "query": req.query,
            "max_tokens": req.limit * 100,
            "tags": scopes,
            "tags_match": "any_strict",
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
                parsed = json.loads(ctx)
                belief_id = parsed.get("beliefId")
            except Exception:
                pass

        if not belief_id or belief_id in seen:
            continue

        seen.add(belief_id)
        normalized.append(
            {
                "id": belief_id,
                "memory": memory.get("text", ""),
                "score": memory.get("score", 1.0),
                "metadata": {"beliefId": belief_id},
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

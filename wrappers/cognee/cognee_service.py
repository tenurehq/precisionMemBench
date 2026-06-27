import io
import os

import httpx
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

COGNEE_URL = os.getenv("COGNEE_URL", "http://localhost:8000")
TIMEOUT = httpx.Timeout(240.0)

app = FastAPI()

id_map: dict[str, str] = {}


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
    belief_id = req.metadata.get("beliefId")
    dataset_name = f"user_{req.user_id}"

    httpx.post(
        f"{COGNEE_URL}/api/v1/remember",
        data={"datasetName": dataset_name},
        files={
            "data": ("data.txt", io.BytesIO(req.text.encode("utf-8")), "text/plain")
        },
        timeout=TIMEOUT,
    )

    if belief_id:
        id_map[f"{req.user_id}:{req.text}"] = belief_id
        print(f"{req.user_id}:{req.text}")

    return {"ok": True}


@app.post("/search")
def search(req: SearchRequest):
    dataset_name = f"user_{req.user_id}"

    response = httpx.post(
        f"{COGNEE_URL}/api/v1/search",
        json={
            "query": req.query,
            "search_type": "CHUNKS",
            "datasets": [dataset_name],
            "top_k": req.limit,
        },
        timeout=TIMEOUT,
    )
    data = response.json()

    normalized = []
    seen = set()

    print(data)

    results = data if isinstance(data, list) else data.get("results", [])
    for r in results:
        text = r.get("text", str(r)) if isinstance(r, dict) else str(r)
        matched_belief = None
        for key, bid in id_map.items():
            user_prefix = f"{req.user_id}:"
            if key.startswith(user_prefix):
                stored_text = key[len(user_prefix) :]
                if (
                    stored_text.lower() in text.lower()
                    or text.lower() in stored_text.lower()
                ):
                    matched_belief = bid
                    break
        if matched_belief and matched_belief not in seen:
            seen.add(matched_belief)
            normalized.append(
                {
                    "id": matched_belief,
                    "memory": text,
                    "score": r.get("score", 1.0) if isinstance(r, dict) else 1.0,
                }
            )

    return {"results": normalized}


@app.delete("/reset")
def reset():
    id_map.clear()

    httpx.delete(f"{COGNEE_URL}/api/v1/datasets", timeout=TIMEOUT)

    for name in ["user_test-user", "user_other-user", "user_brand-new-user"]:
        httpx.post(
            f"{COGNEE_URL}/api/v1/datasets",
            json={"name": name},
            timeout=TIMEOUT,
        )

    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8082)

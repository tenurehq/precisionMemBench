import json
import logging
import re
import subprocess

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOP_K = 6
app = FastAPI()
_belief_map: dict[str, str] = {}


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


def _run_gbrain(args: list[str]) -> str:
    """Shell out to gbrain CLI directly. No auth needed."""
    result = subprocess.run(
        ["gbrain"] + args,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"gbrain {args[0]} failed: {result.stderr}",
        )
    return result.stdout


def _slug_from_belief(belief_id: str, user_id: str) -> str:
    safe_id = belief_id.replace(" ", "-").replace("/", "-")
    return f"beliefs/{user_id}/{safe_id}"


@app.post("/add")
def add(req: AddRequest):
    content = (
        f"---\n"
        f"beliefId: {req.metadata.beliefId}\n"
        f"user_id: {req.user_id}\n"
        f"scope: {req.metadata.scope}\n"
        f"---\n\n"
        f"{req.text}"
    )
    proc = subprocess.run(
        ["gbrain", "capture", "--stdin", "--quiet"],
        input=content,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=f"capture failed: {proc.stderr}")

    actual_slug = proc.stdout.strip()

    actual_slug = ""
    for line in proc.stdout.split("\n"):
        line = line.strip()
        if line.startswith("slug:"):
            actual_slug = line.split(":", 1)[1].strip()
            break

    if not actual_slug:
        raise HTTPException(
            status_code=500, detail=f"Could not parse slug from: {proc.stdout}"
        )

    _belief_map[req.metadata.beliefId] = actual_slug
    return {"ok": True}


@app.put("/update")
def update(req: UpdateRequest):
    slug = _belief_map.get(req.beliefId)
    if slug is None:
        raise HTTPException(
            status_code=404, detail=f"beliefId {req.beliefId} not in belief map"
        )

    content = (
        f"---\nbeliefId: {req.beliefId}\nuser_id: {req.user_id}\n---\n\n{req.text}"
    )
    proc = subprocess.run(
        ["gbrain", "put-page", slug, "--stdin"],
        input=content,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=f"put-page failed: {proc.stderr}")
    return {"ok": True}


def _parse_search_output(output: str) -> list[dict]:
    results = []
    for line in output.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^\[([0-9.]+)\]\s+(\S+)\s+--\s+(.*)$", line)
        if m:
            results.append(
                {
                    "score": float(m.group(1)),
                    "slug": m.group(2),
                    "content": m.group(3),
                }
            )
    return results


@app.post("/search")
def search(req: SearchRequest):
    output = _run_gbrain(["search", req.query, "--json", "--limit", str(TOP_K)])
    pages = _parse_search_output(output)

    results = []
    seen = set()
    for page in pages:
        slug = page["slug"]
        bid = None

        for b, s in _belief_map.items():
            if s == slug:
                bid = b
                break

        if not bid or bid in seen:
            continue
        seen.add(bid)
        results.append(
            {
                "id": bid,
                "memory": page.get("content", ""),
                "score": page.get("score", 1.0),
                "metadata": {"beliefId": bid},
            }
        )

    return {"results": results}


@app.delete("/reset")
def reset():
    _belief_map.clear()
    for user_id in ["test-user", "other-user", "brand-new-user"]:
        try:
            output = _run_gbrain(
                ["list-pages", f"beliefs/{user_id}", "--json", "--limit", "200"]
            )
            pages = json.loads(output) if output.strip() else []
            for page in pages:
                slug = page.get("slug", page) if isinstance(page, dict) else page
                if slug:
                    subprocess.run(
                        ["gbrain", "delete-page", slug],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
        except Exception:
            pass
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8082)

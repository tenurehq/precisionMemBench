import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
SOURCE_ROOT = Path("/tmp/precisionmembench-gbrain-sources")
SOURCE_PREFIX = "pmb-"
_page_map: dict[tuple[str, str], dict[str, Any]] = {}
_source_ids: set[str] = set()


class Metadata(BaseModel):
    beliefId: str
    scope: str | list[str]


class AddRequest(BaseModel):
    text: str
    user_id: str
    metadata: Metadata


class SearchRequest(BaseModel):
    query: str
    user_id: str
    limit: int = 20
    scope: str | None = None


class UpdateRequest(BaseModel):
    beliefId: str
    text: str
    user_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


def _run_gbrain(
    args: list[str],
    input_text: str | None = None,
    source_id: str | None = None,
    timeout: int = 30,
) -> str:
    env = os.environ.copy()
    if source_id is not None:
        env["GBRAIN_SOURCE"] = source_id

    result = subprocess.run(
        ["gbrain", *args],
        check=False,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )

    if result.returncode != 0:
        logger.error(
            "gbrain command failed: %s, exit=%s, stdout=%s, stderr=%s",
            args,
            result.returncode,
            result.stdout,
            result.stderr,
        )
        raise HTTPException(
            status_code=500,
            detail=result.stderr.strip()
            or result.stdout.strip()
            or "gbrain command failed",
        )

    return result.stdout


def _safe_component(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "unknown"


def _source_id(user_id: str, scope: str) -> str:
    readable = _safe_component(f"{user_id}-{scope}")
    digest = hashlib.sha256(f"{user_id}\x00{scope}".encode("utf-8")).hexdigest()[:10]
    available = 32 - len(SOURCE_PREFIX) - len(digest) - 1
    prefix = readable[:available].rstrip("-") or "source"
    return f"{SOURCE_PREFIX}{prefix}-{digest}"


def _slug_from_belief(belief_id: str, user_id: str) -> str:
    safe_user = _safe_component(user_id)
    safe_belief = _safe_component(belief_id)
    return f"beliefs/{safe_user}/{safe_belief}"


def _normalize_slug(value: Any) -> str:
    slug = str(value or "").strip().strip('"').strip("'")
    slug = slug.split("#", 1)[0]
    slug = slug.removesuffix(".md")
    return slug.strip("/")


def _as_scopes(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        scope = value.strip()
        return [scope] if scope else []
    return list(dict.fromkeys(scope.strip() for scope in value if scope.strip()))


def _page_content(
    belief_id: str,
    user_id: str,
    scopes: list[str],
    text: str,
) -> str:
    return (
        "---\n"
        f"beliefId: {json.dumps(belief_id, ensure_ascii=False)}\n"
        f"user_id: {json.dumps(user_id, ensure_ascii=False)}\n"
        f"scope: {json.dumps(scopes, ensure_ascii=False)}\n"
        "---\n\n"
        f"{text}"
    )


def _load_source_ids() -> set[str]:
    output = _run_gbrain(["sources", "list", "--json"])
    if not output.strip():
        return set()

    try:
        data = json.loads(output)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500, detail="Invalid JSON from gbrain sources list"
        ) from exc

    rows = data.get("sources", []) if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return set()

    return {
        row["id"]
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }


def _ensure_source(source_id: str) -> None:
    if source_id in _source_ids:
        return

    existing = _load_source_ids()
    _source_ids.update(existing)
    if source_id in _source_ids:
        return

    source_path = SOURCE_ROOT / source_id
    source_path.mkdir(parents=True, exist_ok=True)
    _run_gbrain(
        [
            "sources",
            "add",
            source_id,
            "--path",
            str(source_path),
            "--no-federated",
            "--force",
        ]
    )
    _source_ids.add(source_id)


def _extract_slugs(data: Any) -> list[str]:
    if isinstance(data, list):
        slugs = []
        for item in data:
            slugs.extend(_extract_slugs(item))
        return slugs

    if not isinstance(data, dict):
        return []

    slug = (
        data.get("slug")
        or data.get("page_slug")
        or data.get("page")
        or data.get("path")
        or data.get("id")
    )
    if slug:
        return [_normalize_slug(slug)]

    slugs = []
    for field in ("results", "chunks", "pages", "matches", "items", "data", "response"):
        if field in data:
            slugs.extend(_extract_slugs(data[field]))
    return slugs


def _parse_search_output(output: str) -> list[str]:
    stripped = output.strip()
    if not stripped:
        return []

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="gbrain query returned invalid JSON",
        )

    slugs = _extract_slugs(data)
    if not slugs:
        raise HTTPException(
            status_code=500,
            detail="gbrain query returned no recognizable page slugs",
        )

    return slugs


def _record_for(source_id: str, slug: str) -> dict[str, Any] | None:
    normalized = _normalize_slug(slug)
    record = _page_map.get((source_id, normalized))
    if record is not None:
        return record

    for (stored_source, stored_slug), candidate in _page_map.items():
        if stored_source != source_id:
            continue
        belief_id = str(candidate["belief_id"])
        if normalized == belief_id or normalized.endswith(f"/{belief_id}"):
            return candidate
        if stored_slug.endswith(f"/{normalized}"):
            return candidate

    return None


def _capture_page(slug: str, source_id: str, content: str) -> str:
    output = _run_gbrain(
        [
            "capture",
            "--stdin",
            "--json",
            "--slug",
            slug,
            "--source",
            source_id,
        ],
        input_text=content,
        source_id=source_id,
    )
    result = json.loads(output)
    actual_slug = result.get("slug")
    if not actual_slug:
        raise HTTPException(
            status_code=500,
            detail="gbrain capture returned no slug",
        )
    return _normalize_slug(actual_slug)


@app.post("/add")
def add(req: AddRequest):
    scopes = _as_scopes(req.metadata.scope)
    if not scopes:
        raise HTTPException(status_code=400, detail="At least one scope is required")

    slug = _slug_from_belief(req.metadata.beliefId, req.user_id)
    content = _page_content(req.metadata.beliefId, req.user_id, scopes, req.text)
    captured = []

    for scope in scopes:
        source_id = _source_id(req.user_id, scope)
        _ensure_source(source_id)
        actual_slug = _capture_page(slug, source_id, content)

        _page_map[(source_id, actual_slug)] = {
            "belief_id": req.metadata.beliefId,
            "user_id": req.user_id,
            "scopes": scopes,
            "source_id": source_id,
            "slug": actual_slug,
        }
        captured.append({"source_id": source_id, "slug": actual_slug})

    return {"ok": True, "pages": captured}


@app.put("/update")
def update(req: UpdateRequest):
    records = [
        record
        for record in _page_map.values()
        if record["belief_id"] == req.beliefId and record["user_id"] == req.user_id
    ]
    if not records:
        raise HTTPException(
            status_code=404, detail=f"beliefId {req.beliefId} not found for user"
        )

    requested_scope = req.metadata.get("scope")
    scopes = (
        _as_scopes(requested_scope)
        if requested_scope is not None
        else list(records[0]["scopes"])
    )
    content = _page_content(req.beliefId, req.user_id, scopes, req.text)

    for record in records:
        actual_slug = _capture_page(
            record["slug"],
            record["source_id"],
            content,
        )
        record["slug"] = actual_slug
        record["scopes"] = scopes
        _page_map[(record["source_id"], actual_slug)] = record

    return {"ok": True, "updated": len(records)}


@app.post("/search")
def search(req: SearchRequest):
    limit = max(0, req.limit)
    if limit == 0 or not req.query.strip():
        return {"results": []}

    scope = req.scope.strip() if req.scope is not None else ""
    if not scope:
        raise HTTPException(status_code=400, detail="scope is required")

    if not _source_ids:
        _source_ids.update(_load_source_ids())

    source_id = _source_id(req.user_id, scope)
    if source_id not in _source_ids:
        return {"results": []}

    query_start = time.perf_counter()

    output = _run_gbrain(
        [
            "query",
            req.query,
            "-" * 2 + "json",
            "-" * 2 + "limit",
            str(limit),
        ],
        source_id=source_id,
    )

    query_ms = (time.perf_counter() - query_start) * 1000
    logger.info("gbrain query completed in %.2f ms", query_ms)

    parse_start = time.perf_counter()
    slugs = _parse_search_output(output)
    parse_ms = (time.perf_counter() - parse_start) * 1000
    logger.info("gbrain result parsing completed in %.2f ms", parse_ms)

    results = []

    for slug in _parse_search_output(output):
        record = _record_for(source_id, slug)
        if record is None:
            raise HTTPException(
                status_code=500,
                detail=f"Could not map gbrain slug to beliefId: {slug}",
            )

        results.append(
            {
                "id": str(record["belief_id"]),
                "memory": "",
            }
        )

    return {"results": results}


@app.delete("/reset")
def reset():
    source_ids = _load_source_ids()
    benchmark_sources = sorted(
        source_id for source_id in source_ids if source_id.startswith(SOURCE_PREFIX)
    )
    removed = []
    failures = []

    for source_id in benchmark_sources:
        try:
            _run_gbrain(
                ["sources", "remove", source_id, "--confirm-destructive"],
                timeout=60,
            )
            removed.append(source_id)
        except HTTPException as exc:
            failures.append({"source_id": source_id, "detail": exc.detail})

    if failures:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to remove benchmark sources",
                "failures": failures,
            },
        )

    _page_map.clear()
    _source_ids.clear()
    if SOURCE_ROOT.exists():
        shutil.rmtree(SOURCE_ROOT)

    return {"ok": True, "removed_sources": removed}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8082)

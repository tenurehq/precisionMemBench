"""
Self-contained MCP server + eval endpoint for OKF-based memory retrieval.

The model receives ONLY the standard MCP tool definitions. No retrieval-agent
system prompt. The user asks a question. The model decides whether to call
list_files / read_file -- or not. This is how an OKF bundle would actually
be used: dropped into a tool, consumed organically.

Usage:
    python okf_mcp_eval.py ./okf-bundle/

Environment variables:
    OPENAI_API_KEY   API key for the model
    OPENAI_BASE_URL  Base URL (defaults to https://api.openai.com/v1)
    MODEL_NAME       Model to use (defaults to gpt-4o)
    PORT             Port for the HTTP server (defaults to 8082)
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

BUNDLE_DIR = (
    Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path("./okf-bundle").resolve()
)

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
)

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
)
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o")

app = FastAPI()


def _read_frontmatter(filepath: Path) -> dict[str, str]:
    content = filepath.read_text()
    if not content.startswith("---"):
        return {}
    try:
        end = content.index("---", 3)
        raw = content[3:end]
        result: dict[str, str] = {}
        for line in raw.strip().split("\n"):
            if ":" in line:
                key, _, val = line.partition(":")
                result[key.strip()] = val.strip().strip('"').strip("'")
        return result
    except Exception:
        return {}


def _safe_filepath(filename: str) -> Path:
    """Resolve the filename against BUNDLE_DIR. Reject path traversal."""
    if "/" in filename or "\\" in filename:
        raise ValueError(f"Invalid filename (contains path separator): {filename}")

    candidate = (BUNDLE_DIR / filename).resolve()
    if not str(candidate).startswith(str(BUNDLE_DIR)):
        raise ValueError(f"Path traversal rejected: {filename}")
    if not candidate.is_file():
        raise FileNotFoundError(f"File not found: {filename}")

    return candidate


_belief_id_cache: dict[str, str] = {}


def _get_belief_id(filename: str) -> str:
    """Parse beliefId from the markdown file's frontmatter."""
    if filename in _belief_id_cache:
        return _belief_id_cache[filename]

    try:
        filepath = _safe_filepath(filename)
    except (ValueError, FileNotFoundError):
        return f"b-{Path(filename).stem}"

    fm = _read_frontmatter(filepath)
    belief_id = fm.get("beliefId", "")
    if not belief_id:
        # Fallback: derive from filename stem
        stem = Path(filename).stem
        belief_id = f"b-{stem}" if not stem.startswith("b-") else stem

    _belief_id_cache[filename] = belief_id
    return belief_id


TOOLS: list[ChatCompletionToolParam] = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List available OKF markdown files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "description": "Optional filter, e.g. 'domain:code' or 'domain:writing'",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read an OKF markdown file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The filename to read, e.g. 'stripe-webhook-idempotency.md'",
                    }
                },
                "required": ["filename"],
            },
        },
    },
]


def tool_list_files(scope: str | None = None) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for f in sorted(BUNDLE_DIR.glob("*.md")):
        fm = _read_frontmatter(f)
        file_scope = fm.get("scope", "")
        if scope and scope not in file_scope:
            continue
        results.append(
            {
                "filename": f.name,
                "title": fm.get("title", f.stem),
                "type": fm.get("type", ""),
                "description": fm.get("description", ""),
                "tags": fm.get("tags", ""),
            }
        )
    return results


def tool_read_file(filename: str) -> str:
    try:
        filepath = _safe_filepath(filename)
    except (ValueError, FileNotFoundError) as e:
        return f"Error: {e}"
    return filepath.read_text()


def execute_tool(name: str, args: dict[str, Any]) -> str:
    if name == "list_files":
        return json.dumps(tool_list_files(args.get("scope")))
    elif name == "read_file":
        return tool_read_file(args["filename"])
    else:
        return json.dumps({"error": f"Unknown tool: {name}"})


class SearchRequest(BaseModel):
    query: str
    user_id: str = "test-user"


@app.post("/search")
def eval_query(req: SearchRequest):
    """
    Send a plain user query. No system prompt about retrieval. The model has
    access to list_files and read_file as MCP tools. It decides whether to
    use them -- exactly how an OKF bundle would work in practice.
    """
    t0 = time.time()

    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": req.query},
    ]

    files_read: list[str] = []
    max_turns = 2

    for _ in range(max_turns):
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        choice = resp.choices[0]
        msg = choice.message

        if msg.tool_calls:
            tool_calls_block: list[dict[str, Any]] = []
            for tc in msg.tool_calls:
                tool_calls_block.append(
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                )
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": tool_calls_block,
                }  # type: ignore[arg-type]
            )

            for tc in msg.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments)
                result = execute_tool(name, args)
                if name == "read_file":
                    fn = args.get("filename", "")
                    if fn not in files_read:
                        files_read.append(fn)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }  # type: ignore[arg-type]
                )
        else:
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                }  # type: ignore[arg-type]
            )
            break

    beliefs_retrieved = []
    for fn in files_read:
        try:
            filepath = BUNDLE_DIR / fn
            if filepath.exists():
                fm = _read_frontmatter(filepath)
                bid = fm.get("beliefId", "")
                if bid and bid not in beliefs_retrieved:
                    beliefs_retrieved.append(bid)
        except Exception:
            pass

    results = []
    for bid in beliefs_retrieved:
        results.append(
            {
                "id": bid,
                "metadata": {"beliefId": bid},
            }
        )

    elapsed = (time.time() - t0) * 1000

    return {
        "results": results,
        "elapsed_ms": round(elapsed, 2),
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8082))
    print(f"Starting OKF MCP eval server on port {port}")
    print(f"OKF bundle: {BUNDLE_DIR}")
    print(f"Model: {MODEL_NAME}")
    uvicorn.run(app, host="0.0.0.0", port=port)

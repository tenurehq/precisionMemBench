## Provider

hippo

## Repository

https://github.com/kitfunso/hippo-memory (MIT). The eval runs the published npm release, `hippo-memory@3.15.1`.

## Embedding model

None. hippo stores each belief as written and ranks recall with its own local search over a SQLite store (`hippo init --no-embeddings`).

## LLM (if applicable)

None. hippo writes and recalls without a language model.

## Artifact reproducibility

Built from public source: `npm install -g hippo-memory@3.15.1` on `node:22-bookworm-slim@sha256:e9f565d32859f0cbfb52125eafe8be39390f24dac302dc3cdf566e8ba3ab21ee`. The wrapper image uses the same Python base and package pins as the agentmemory wrapper. Tested at benchmark commit `61a712a`.

## Network behavior

Build: npm (hippo-memory) and PyPI (fastapi, httpx, uvicorn). Run: none observed. `hippo serve` listens on 127.0.0.1 inside its container, the wrapper shares that network namespace, and hippo calls no model or hosted API.

## Notes

- Run: `docker compose up -d --build` in this folder, then the README commands with `MEMORY_PROVIDER=hippo RESEED=true` (wrapper on `http://localhost:8085`).
- Each container start serves a new, empty hippo store and mints one admin API key for the wrapper (`/data/key.json`), so `/reset` can delete every stored row.
- `/add` is `POST /v1/memories` with scope `<user_id>/<metadata.scope>`. `/search` is `GET /v1/memories?q=&limit=&scope=<user_id>/<scope>`, hippo's scope filter. `/reset` is `DELETE /v1/memories/:id` for each stored row.
- hippo's recall rows carry no caller metadata, so the wrapper keeps beliefIds in an in-process map by hippo memory id and clears it on `/reset`, as the yourmemory wrapper does. The first hit per beliefId is returned.
- The harness sends parallel searches from one caller, so hippo's 20-per-second request limits are off (`HIPPO_CALLER_RPS=0`, `HIPPO_V1_RPS=0`).
- No thresholds, ranking settings or belief-specific handling are added; recall runs on hippo 3.15.1's defaults.

# Submitting to PrecisionMemBench

To appear on the leaderboard, open a PR adding a wrapper for your provider to
`wrappers/`. We run the eval against your wrapper -- you do not submit scores,
we produce them.

---

## What a wrapper is

A wrapper is a thin FastAPI service that normalizes your provider's API to the
three-endpoint contract the eval harness expects (`/add`, `/search`, `/reset`).
The `wrappers/mem0/` directory is the reference implementation. Use it as your
starting point.

The three files are:

- `mem0_service.py` -- the FastAPI service
- `Dockerfile` -- with all dependency versions pinned
- `docker-compose.yml` -- with any infrastructure dependencies (vector store,
  cache, etc.) pinned to digests

The `wrappers/` directory contains all existing integrations. Browse them for
patterns before writing your own -- most common problems have already been
solved there.

---

## API contract

Your wrapper must expose three endpoints on port `8080`.

### `POST /add`

Ingest a single belief into your memory store.

```json
// Request
{
  "text": "Writes TypeScript with strict mode and no implicit any.",
  "user_id": "test-user",
  "metadata": {
    "beliefId": "b-ts-pref"
  }
}

// Response
{ "ok": true }
```

You must persist `metadata.beliefId` and return it in search results. The eval
harness uses it to map your results back to the belief corpus.

### `POST /search`

Search for beliefs by query text, scoped to a `user_id`.

```json
// Request
{
  "query": "what language does this user prefer for backend code?",
  "user_id": "test-user",
  "limit": 20
}

// Response
{
  "results": [
    {
      "id": "b-ts-pref",
      "memory": "Writes TypeScript with strict mode and no implicit any.",
      "score": 0.91
    }
  ]
}
```

The `id` field in each result must be the `beliefId` from the original `/add`
metadata. Results that omit or mangle this field will score zero on all active
retrieval cases.

### `DELETE /reset`

Clear all stored beliefs for all users. Called once before seeding begins.

```json
// Response
{ "ok": true }
```

---

## Mapping beliefId when your provider doesn't support metadata round-trip

The eval harness maps your search results back to the belief corpus using the
`beliefId` value from each `/add` request. Your `/search` response must return
it as the `id` field on every result.

If your provider supports storing and returning arbitrary metadata, persist
`beliefId` there and read it back on search -- this is what the mem0 wrapper
does.

If your provider does not support metadata round-trip, maintain an in-process
dict in the wrapper that maps your provider's internal IDs to `beliefId` values
at `/add` time, then resolve them on `/search`. The `wrappers/yourmemory/`
wrapper uses this pattern and is a good reference for it.

Your `/reset` endpoint must also clear this dict along with the provider's
stored memories, or stale mappings will corrupt subsequent eval runs.

---

## Requirements

### 1. Public GitHub repository

Your provider's source code must be publicly accessible at the time of
submission and must remain public. Link to it in your `SUBMISSION.md`.

Private repos, obfuscated code, and compiled-only submissions are not accepted.

### 2. Pinned dependencies

Pin all dependency versions in your `Dockerfile`. If your wrapper requires
infrastructure (e.g. Qdrant, Redis), pin those images to SHA256 digests in
`docker-compose.yml`, as the mem0 reference does:

```yaml
image: qdrant/qdrant@sha256:45f8e3ddc2570a4d029877e1b5ec1045c19b3852b4e22a55c7f43b05aea0ca89
```

Mutable tags (`:latest`, `:main`, etc.) are not accepted.

### 3. Environment variables

Declare all required environment variables in your `docker-compose.yml`. The
eval harness will not supply any credentials or configuration beyond what is
documented in your PR.

The following variables from the mem0 reference are illustrative -- your
provider will have its own:

| Variable             | Purpose                                          |
| -------------------- | ------------------------------------------------ |
| `LLM_MODEL`          | The LLM your provider uses for memory extraction |
| `LLM_BASE_URL`       | Base URL for LLM inference                       |
| `LLM_API_KEY`        | API key for LLM inference                        |
| `OLLAMA_EMBED_MODEL` | Embedding model name (if using Ollama)           |
| `OLLAMA_URL`         | Ollama base URL (if using Ollama)                |

The embedding model you use will be included in your leaderboard display name,
e.g. `mem0 (mxbai-embed-large)`. If you use a proprietary embedder, document
it clearly in your PR.

---

## Opening a submission PR

Create a PR against this repository with the following:

1. A new directory `wrappers/<your-provider-name>/` containing:
   - Your wrapper service (e.g. `<provider>_service.py`)
   - `Dockerfile` with pinned dependency versions
   - `docker-compose.yml` with any infrastructure dependencies
2. A `wrappers/<your-provider-name>/SUBMISSION.md` with the fields below

```markdown
## Provider

<!-- Name as it should appear on the leaderboard -->

## Repository

<!-- Public GitHub URL for your provider's source code -->

## Embedding model

<!-- Model name and dimensions, e.g. mxbai-embed-large (1024d) -->
<!-- Or "proprietary" with a description -->

## LLM (if applicable)

<!-- If your provider uses an LLM for memory extraction, name it here -->
<!-- This will be noted alongside your results -->

## Notes

<!-- Anything relevant to reproducing your results -->
```

---

## What happens after you open a PR

1. We review your wrapper and `SUBMISSION.md`
2. We bring up your stack with `docker compose up` and run the full eval suite:
   - `retrieval.external.eval.test.ts` (77 retrieval cases)
   - `session-retrieval.external.eval.test.ts` (12 session cases)
3. We attach the results to your PR as a comment
4. If the eval passes cleanly, we merge and run `export_to_hf.py` to update
   the leaderboard

Results are published as-is. We do not adjust scores or re-run on different
hardware. If your wrapper fails to start or the API contract is not met, we
will comment on the PR with the failure and you can revise.

## What we do not accept

- Self-reported scores
- Wrappers with mutable image tags (`:latest`, `:main`, etc.)
- Closed-source provider implementations
- Wrappers that modify the eval harness or seed data
- Wrappers that detect the eval environment and behave differently

The public repo requirement exists so that any auditor can verify your
implementation is not special-casing the benchmark. If your code reads the
belief IDs at startup and pre-caches responses, that will be visible and the
submission will be removed.

## Questions

Open an issue with the `submission` label.

# Submitting to PrecisionMemBench

To appear on the leaderboard your submission must satisfy all of the
requirements below. We run the eval against your container -- you do not
submit scores, we produce them.

---

## Requirements

### 1. Public GitHub repository

Your full memory provider implementation must be publicly accessible at the
time of submission and must remain public. The repository must contain at
minimum:

- Your service implementation
- A `Dockerfile` with all dependency versions pinned
- A `docker-compose.yml` if your service requires infrastructure dependencies
  (vector store, cache, etc.)

Private repos, obfuscated code, and compiled-only submissions are not accepted.

### 2. Docker image with a pinned digest

Push your image to Docker Hub or GHCR and submit it with a SHA256 digest, not
a mutable tag:

```
# Good — digest is immutable
ghcr.io/yourorg/yourprovider@sha256:abc123...

# Not accepted — latest can change silently
ghcr.io/yourorg/yourprovider:latest
```

To get the digest after pushing:

```bash
docker buildx imagetools inspect ghcr.io/yourorg/yourprovider:yourtag \
  --format '{{json .Manifest.Digest}}'
```

The digest in your PR must match the digest we pull. If they do not match the
submission is rejected without running the eval.

### 3. Implement the provider API

Your container must expose three endpoints on port `8080`. This is the same
contract the reference implementations in `providers/` follow.

#### `POST /add`

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

The `metadata.beliefId` field is the stable identifier the eval harness uses
to map your search results back to the belief corpus. You must persist it and
return it in search results.

#### `POST /search`

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
retrieval cases -- the harness cannot map them back to the corpus.

#### `DELETE /reset`

Clear all stored beliefs for all users. Called once before seeding begins.

```json
// Response
{ "ok": true }
```

### 4. Reference implementation

The `providers/mem0/` directory contains a complete working reference:

- `mem0_service.py` -- the FastAPI service implementing all three endpoints
- `Dockerfile` -- pinned dependency versions
- `docker-compose.yml` -- Qdrant pinned to a digest as an infrastructure dependency

Use it as your starting point. The three files together are the full contract.

### 5. Environment variables

Declare all required environment variables in your `docker-compose.yml`. The
eval harness will not supply any credentials or configuration beyond what is
documented in your PR.

The following variables from the reference implementation are illustrative --
your provider will have its own:

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

1. A new directory under `providers/<your-provider-name>/` containing your
   service files
2. A `providers/<your-provider-name>/SUBMISSION.md` with the fields below

```markdown
## Provider

<!-- Name as it should appear on the leaderboard -->

## Image

<!-- Full image reference with SHA256 digest -->
<!-- e.g. ghcr.io/yourorg/yourprovider@sha256:abc123... -->

## Repository

<!-- Public GitHub URL -->

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

1. We verify the image digest matches the repo at the referenced commit
2. We pull your image and run the full eval suite:
   - `retrieval.external.eval.test.ts` (77 retrieval cases)
   - `session-retrieval.external.eval.test.ts` (12 session cases)
3. We attach the results to your PR as a comment
4. If the eval passes cleanly, we merge and run `export_to_hf.py` to update
   the leaderboard

Results are published as-is. We do not adjust scores or re-run on different
hardware. If your container fails to start or the API contract is not met, we
will comment on the PR with the failure and you can revise.

## What we do not accept

- Self-reported scores without a Docker image
- Images that detect the eval environment and behave differently
- Mutable image tags (`:latest`, `:main`, etc.)
- Closed-source implementations
- Containers that modify the eval harness or seed data

The public repo requirement exists precisely so that any auditor can verify
your implementation is not special-casing the benchmark. If your code reads
the belief IDs at startup and pre-caches responses, that will be visible and
the submission will be removed.

## Questions

Open an issue with the `submission` label.

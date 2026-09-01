# PrecisionMemBench

PrecisionMemBench is a multi-dimensional retrieval benchmark for LLM memory systems. It measures four orthogonal properties that single-turn answer-quality benchmarks cannot detect:

- **Retrieval precision** - does the right belief surface, and only that belief, against a fixed seed corpus of 35 beliefs spanning two domain scopes, a supersession chain, and a secondary-user fixture
- **Noise isolation** - do beliefs introduced during off-topic drift turns contaminate retrieval on subsequent unrelated turns across a 10-turn session
- **Session-turn latency** - does retrieval latency degrade under session load relative to single-turn baselines
- **Belief mutability** - do beliefs updated mid-session surface immediately within the same session via the alias enrichment flywheel

Each case specifies what memory must be returned and shouldn't be returned. Any memory that is included that shouldn't be returned results in a failure for that case.

**89 scored cases**, comprising 77 single-turn cases and 12 turn-level session assertions, covering alias resolution · scope disambiguation · supersession chain exclusion · fuzzy matching · cross-user isolation · budget eviction · ranking stability · session-level noise isolation under multi-turn topic drift

Paper: [arXiv](https://arxiv.org/abs/2605.11325) — Dataset: [HuggingFace](https://huggingface.co/datasets/tenurehq/precisionmembench) — Leaderboard: [HuggingFace Spaces](https://huggingface.co/spaces/tenurehq/precisionmembench)

**_Memory and belief are used interchangably._**

## Results

### Single-turn results

| Provider                | Active passes | Total passes | Mean precision | Mean recall | Retrieval p50 (ms) | Ingestion total (s) |
| ----------------------- | ------------- | ------------ | -------------- | ----------- | ------------------ | ------------------- |
| `tenure`                | 43/43         | 77/77        | 1.00           | 1.00        | 9.77               | 1.00                |
| `open-knowledge-format` | 18/43         | 36/77        | 0.47           | 0.91        | 3534.53            | 0.00                |
| `supermemory`           | 4/43          | 21/77        | 0.22           | 0.71        | 69.41              | 5.20                |
| `agentmemory`           | 0/43          | 7/77         | 0.17           | 0.97        | 82.28              | 1.10                |
| `yourmemory`            | 0/43          | 21/77        | 0.17           | 0.88        | 313.39             | 16.40               |
| `atomicmemory`          | 0/43          | 9/77         | 0.15           | 0.95        | 71.01              | 658.90              |
| `gbrain`                | 5/43          | 34/77        | 0.14           | 0.17        | 543.84             | 28.60               |
| `zep`                   | 0/43          | 9/77         | 0.09           | 0.95        | 124.36             | 897.00              |
| `vector`                | 0/43          | 11/77        | 0.09           | 1.00        | 71.87              | ---                 |
| `hindsight`             | 0/43          | 9/77         | 0.06           | 1.00        | 589.86             | 173.30              |
| `mem0`                  | 0/43          | 9/77         | 0.06           | 0.99        | 64.94              | 111.30              |
| `a-mem`                 | 0/43          | 9/77         | 0.06           | 0.99        | 13.80              | 178.80              |
| `cognee`                | 0/43          | 11/77        | 0.05           | 0.92        | 2891.04            | 369.20              |

Mean precision and recall are computed over the 43 cases that require active query-dependent retrieval. The single-turn pass count includes active, structural, and trivially empty cases.

A high recall score doesn't mean the retrieval is precise. Most comparison systems frequently return the correct belief alongside many unrelated beliefs, preserving recall while reducing precision. Other systems exhibit a different failure mode by returning few or no results and omitting the required belief. A low precision score indicates that, when relevant memories are retrieved, they are often accompanied by substantial memories unrelated to the query.

### Pass type breakdown

The counts bloew represent the 77 single-turn cases.

| Provider                | Active retrieval | Structural | Trivially empty |
| ----------------------- | ---------------- | ---------- | --------------- |
| `tenure`                | 43               | 25         | 9               |
| `open-knowledge-format` | 18               | 13         | 5               |
| `gbrain`                | 5                | 20         | 9               |
| `supermemory`           | 4                | 14         | 3               |
| `a-mem`                 | 0                | 6          | 3               |
| `agentmemory`           | 0                | 5          | 2               |
| `atomicmemory`          | 0                | 6          | 3               |
| `cognee`                | 0                | 7          | 4               |
| `hindsight`             | 0                | 6          | 3               |
| `mem0`                  | 0                | 6          | 3               |
| `vector`                | 0                | 8          | 3               |
| `yourmemory`            | 0                | 15         | 6               |
| `zep`                   | 0                | 6          | 3               |

- **Active retrieval pass**: The case requires query-dependent belief IDs to be returned, and all asserted constraints are satisfied.
- **Structural pass**: The case tests a constraint such as scope isolation, supersession exclusion, or type routing without requiring successful query-dependent retrieval.
- **Trivially empty pass**: The case expects an empty `relevantBeliefs` tier because of its query or budget configuration.

### Embedding model invariance

| Model                    | Precision | Recall | Passes | Mean (ms) | p95 (ms) |
| ------------------------ | --------- | ------ | ------ | --------- | -------- |
| nomic-embed-text (768)   | 0.09      | 1.0    | 11/77  | 43.36     | 85.21    |
| mxbai-embed-large (1024) | 0.09      | 1.0    | 11/77  | 96.48     | 257.24   |
| qwen3-8b (4096)          | 0.09      | 1.0    | 11/77  | 1130.95   | 2604.84  |

Each configuration records 11 single-turn passes and 0 active retrieval passes.

### Session results

The session evaluation contains 12 scored turn-level assertions across two sessions. It records returned belief IDs, drift contamination, retrieval precision, and retrieval latency as session state changes.

The drift score is the fraction of retrieved beliefs originating from off-topic turns. A score of 0 means that no returned belief originated from an off-topic turn.

| Provider                | Turns passed | Pass rate | Mean drift | Mean precision | Session p50 (ms) |
| ----------------------- | ------------ | --------- | ---------- | -------------- | ---------------- |
| `tenure`                | 12/12        | 1.00      | 0.0000     | 1.0000         | 47.79            |
| `open-knowledge-format` | 2/12         | 0.17      | 0.2153     | 0.5694         | 3349.45          |
| `yourmemory`            | 1/12         | 0.08      | 0.7365     | 0.1965         | 430.49           |
| `supermemory`           | 1/12         | 0.08      | 0.7493     | 0.1825         | 172.32           |
| `cognee`                | 1/12         | 0.08      | 0.8459     | 0.0772         | 4222.62          |
| `gbrain`                | 1/12         | 0.08      | 0.0000     | ---            | 535.61           |
| `agentmemory`           | 0/12         | 0.00      | 0.8087     | 0.1913         | 98.49            |
| `atomicmemory`          | 0/12         | 0.00      | 0.8449     | 0.1551         | 355.08           |
| `zep`                   | 0/12         | 0.00      | 0.8888     | 0.1112         | 418.13           |
| `vector`                | 0/12         | 0.00      | 0.9142     | 0.0858         | 256.75           |
| `a-mem`                 | 0/12         | 0.00      | 0.9259     | 0.0741         | 25.66            |
| `hindsight`             | 0/12         | 0.00      | 0.9285     | 0.0715         | 1880.60          |
| `mem0`                  | 0/12         | 0.00      | 0.9398     | 0.0602         | 377.93           |

‡ For `gbrain`, the drift score is 0 because no beliefs were returned. The required belief was also absent, so the corresponding cases did not pass.

## Open Knowledge Format Run

The Open Knowledge Format run is not a test of markdown as a storage format. It evaluates the runtime access pattern implied by the OKF spec when a bundle is placed into an AI tool today: files are available, the model may inspect them, and PMB scores the belief IDs corresponding to the files the model retrieves.

## Case categories

The benchmark contains 77 single-turn cases and 12 scored turn-level assertions across two session scenarios, for 89 scored cases in total. Session evaluation extends the corpus dynamically, with beliefs created and alias sets updated during the session.

The categories define practical correctness requirements rather than prescribing a retrieval architecture. Providers may satisfy them through filtering, indexing, ranking, graph traversal, model-based selection, or another mechanism. The benchmark evaluates only whether the resulting belief set contains the required state and excludes state that would be misleading, obsolete, irrelevant, or unauthorized.

Benchmark categories are expressed as practical correctness requirements. Scoring examines required and prohibited belief IDs without requiring providers to adopt the proposed belief schema, retrieval pipeline, or output organization.

| Category                         | Cases  |
| -------------------------------- | ------ |
| Alias resolution                 | 23     |
| Scope disambiguation             | 12     |
| Session-level noise isolation    | 12     |
| Fuzzy matching and prefix guards | 8      |
| Design boundary cases            | 6      |
| Type routing and open questions  | 6      |
| Budget eviction and capacity     | 5      |
| Relation expansion               | 4      |
| Persona prelude content          | 4      |
| Supersession chain exclusion     | 3      |
| Ranking stability                | 3      |
| Counter-signal retrieval         | 2      |
| Cross-user isolation             | 1      |
| Cold start behavior              | 1      |
| **Total**                        | **89** |

**Alias resolution**  
Whether users can refer to a stored concept through shorthand, abbreviations, or natural variations without receiving unrelated memories that must be disambiguated downstream.

**Scope disambiguation**  
Whether the same name can be used in different projects or domains without information from one context appearing in another.

**Supersession chain exclusion**  
Whether changed decisions and preferences stop influencing current behavior while the historical record remains available for audit. Queries using outdated terminology must not restore obsolete guidance.

**Fuzzy matching and prefix guards**  
Whether ordinary misspellings and transpositions still reach the intended memory without allowing similarly spelled but unrelated terms to produce false matches.

**Counter-signal retrieval**  
Whether asking about a rejected or replaced option surfaces the current decision that should govern the response, rather than obsolete guidance or an empty result.

**Relation expansion**  
Whether a query about a dependency or relationship returns enough associated state to make the relationship useful, without introducing participants that are irrelevant or outside the active context.

**Session-level noise isolation**  
Whether a conversation can move through unrelated topics and later return to an earlier topic without memories from the intervening discussion contaminating the returned context.

**Budget eviction and capacity**  
Whether limited context capacity is allocated to the state that must be present, including when no slots are available, only one slot remains, or several memories compete for a full budget.

**Design boundary cases**  
Whether empty, weakly related, ambiguous, or intentionally unsupported queries produce predictable results instead of filling the context with low-confidence or misleading memories.

**Type routing and open questions**  
Whether downstream consumers can distinguish unsettled questions from established state, and whether resolved questions cease to appear as current uncertainty.

**Ranking stability**  
Whether specific and unambiguous queries produce a stable, useful ordering rather than allowing weaker matches or incidental scoring differences to displace the intended belief.

**Cross-user isolation**  
Whether one user's stored information remains inaccessible to another user regardless of textual or semantic similarity.

**Cold-start behavior**  
Whether a user with no stored state receives a clean empty result rather than an error, fabricated context, or information inherited from another user.

**Persona prelude content**  
Whether durable user preferences and communication guidance remain consistently available across topics without depending on incidental similarity to the current query.

## Metrics

Cases are scored against the belief IDs they require and prohibit.

A case passes when every required belief ID is returned and no prohibited belief ID is returned. If a case requires an empty result, it passes only when no belief IDs are returned.

The benchmark reports:

- **Retrieval precision and recall** for the `relevantBeliefs` tier.
- **Pinned coverage** for the `pinnedFacts` tier.
- **Question precision and recall** for the `openQuestions` tier.
- **Drift score** for session cases, measured as the fraction of retrieved non-pinned beliefs originating from drift-turn topics. A score of 0 indicates perfect isolation.

Metrics that do not apply to a case are recorded as null and excluded from aggregate calculations.

## Baseline reports

Pre-run reports for all reference systems are committed at `test-results/baseline/`:

```
test-results/baseline/
  retrieval-report.json
  retrieval-report-vector.json
  retrieval-report-mem0.json
  retrieval-report-zep.json
  retrieval-report-hindsight.json
  ...
```

Each report contains per-case results including `passed`, `failures`, `retrievalPrecision`, `retrievalRecall`, and `retrievalLatencyMs`, plus aggregate `p50`/`p95` latency and mean precision/recall at the top level.

When you run against your own provider, compare your output in `test-results/` directly against these files.

## Running the benchmark

### Prerequisites

- Node.js 20+
- Docker (for the vector baseline and provider stacks)
- An Ollama instance for the vector baseline only

### 1. Install dependencies

```bash
npm i
```

If you want to run the raw embedding model runs:

```bash
npm i mongodb
```

### 2. Run against a comparison provider

Start the provider's stack, then:

```bash
MEMORY_PROVIDER=mem0 npx ava src/retrieval.external.eval.test.ts --timeout 10m
MEMORY_PROVIDER=mem0 npx ava src/session-retrieval.external.eval.test.ts --timeout 10m
```

Reports land in `test-results/`. Valid values: `mem0`, `zep`, `hindsight`

### 3. Run the vector baseline

The vector eval manages its own MongoDB Atlas Local container. Docker must be running but you do not set anything up manually.

```bash
# One-time: generate embeddings and commit the result
OLLAMA_URL=http://localhost:11434 npx tsx embed-seed.ts

# Run the eval
npx ava src/retrieval.vector.eval.test.ts
npx ava src/session-retrieval.vector.eval.test.ts
```

The Atlas Local container starts and stops automatically per run. Ports `27019` (single-turn) and `27021` (session) are used.

### 4. Export results to HuggingFace format

```bash
python export_to_hf.py
# Output: hf_export/leaderboard.json + hf_export/README.md
```

## Adding your provider

### 1. Write a wrapper

Expose a FastAPI service with three endpoints. See `wrappers/mem0_service.py` for the full contract.

**`POST /add`**

```json
{
  "text": "redis_cache Redis",
  "user_id": "test-user",
  "metadata": { "beliefId": "b-redis-code" }
}
```

**`POST /search`**

```json
{ "query": "Redis eviction policy", "user_id": "test-user", "limit": 20 }
```

Returns: `{ "results": [ { "id": "...", "memory": "...", "metadata": { "beliefId": "..." } } ] }`

**`DELETE /reset`**
Clears all memories for all users. Called once before seeding.

The `beliefId` in metadata is how the harness maps provider results back to the benchmark's belief schema. If your provider cannot round-trip arbitrary metadata, implement a custom `resolveBeliefId` in the adapter.

### 2. Register the provider

Add one entry to `providers.config.json`:

```json
"myprovider": {
  "envVar": "MYPROVIDER_URL",
  "defaultUrl": "http://localhost:8082",
  "seedDelayMs": 1000,
  "beliefToText": "canonical_name_aliases"
}
```

### 3. Run

```bash
MEMORY_PROVIDER=myprovider npx ava src/retrieval.external.eval.test.ts --timeout 10m
MEMORY_PROVIDER=myprovider npx ava src/session-retrieval.external.eval.test.ts --timeout 10m
```

The eval files themselves never need to change.

## Submitting results to the leaderboard

See [SUBMITTING.md](./SUBMITTING.md) for the full submission process.

The short version: add a wrapper for your provider to `wrappers/` and open a PR. We run the eval against your wrapper and publish the results, you do not submit scores. Results from merged PRs are reflected on the [live leaderboard](https://huggingface.co/spaces/tenurehq/precisionmembench).

### Tenure

Tenure's eval lives in the Tenure repo and runs directly against its `BeliefsReader` and `ContextBuilder` implementations. It is fully self-contained. The Atlas Local container starts and stops automatically. Reports land in `test-results/`. Results are re-produced on every pull request via CI.

```bash
git clone https://github.com/tenurehq/tenure.git
cd tenure
npm i
npm run test:eval
```

## Provider wrappers

Each comparison provider is wrapped with a thin FastAPI service that normalises the `/add` / `/search` / `/reset` contract. Wrappers are in `wrappers/`.

## Citation

```bibtex
@article{flynt2026precisionmembench,
  title   = {Structured Belief State and the First Precision-Aware Benchmark
             for LLM Memory Retrieval},
  author  = {Flynt, Jeffrey},
  year    = {2026}
}
```

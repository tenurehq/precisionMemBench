## Provider
HingeZero — Original Witness / RetainingLoop (BGE-small-en-v1.5)

## Repository
**Public source for the submitted implementation:**
https://github.com/HingeZero/precisionMemBench/tree/submit-hingezero-witness/wrappers/hingezero

**Original public HingeZero core:**
https://github.com/HingeZero/HingeZero-1B-Memory/blob/main/HingeZero_Core.py

All runtime source needed for this wrapper, including the full HingeZero core, is committed under `wrappers/hingezero/` in this pull request.

## Embedding model
`BAAI/bge-small-en-v1.5`, 384 dimensions; `fastembed==0.9.1` / ONNX inference. The model is fetched during container build; inference itself is offline.

## LLM (if applicable)
None. This is a memory retrieval system, not an LLM-based answer generator.

## Artifact reproducibility
Source-build submission: all provider and wrapper Python source is public in this PR. All direct Python dependencies and the Docker base image are version/digest-pinned in the Dockerfile.

- Original unmodified HingeZero core Git blob: `ec0ec9c56c233b97038d88618ad9f2bcff26bcab`.
- Exact source implementation tested in standalone developer repository: https://github.com/HingeZero/ingeZero-PrecisionMemBench/actions/runs/40659252748
- Tested source commit: `67d8b53c0e92e53ac77935fd8f43c8e43a1d7c82`.
- Self-run result on upstream's unmodified fixtures: 77/77 single-turn retrieval cases, 2/2 session suites (12 session-turn assertions), 16/16 Python regression tests, GitHub Actions workflow conclusion success.
- This is a developer-run result, **not** an official leaderboard score. Independent organisers' rerun is requested.
- The embedding model's exact downloadable artifact revision is not independently locked in the current Dockerfile; the official evaluation should record the resolved artifact revision. No prebuilt binary image is being submitted as an opaque provider.

## Network behavior
Download of the embedding model during Docker build. Python package installation also needs package registry connectivity while building. Once built, the FastAPI service, FastEmbed encoder, HingeZero Witness and RetainingLoop, and SQLite memory store execute locally. No LLM endpoint, credentials, hosted inference, or runtime telemetry is required by the application.

## Notes
The complete original `HingeZero_Core.py` is reproduced unchanged in the submission. HingeZero's `HingeZeroWitness` verifies that recalled states match stored indexed states; this is not, on its own, a guarantee of semantic correctness. The wrapper preserves source text, identities, aliases, validity scopes, and independently filters obsolete records. Atomic writes prevent searches from reading a record while its new association is being embedded. No benchmark seed data, gold labels, or case IDs are hard-coded or modified.

Please run the official reproducibility evaluation and publish the organiser-computed metrics, including retrieval precision/recall and latency.

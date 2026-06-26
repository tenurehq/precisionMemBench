## Reproducibility

Supermemory local is distributed as a compiled binary. PrecisionMemBench packages that binary into a Docker image and pins the resulting image by digest.

Benchmark image:

```bash
docker pull tenurehq/precisionmembench-supermemory@sha256:<digest>
```

## Evaluated artifact

| Field                        | Value                                                                     |
| ---------------------------- | ------------------------------------------------------------------------- |
| Provider                     | `supermemory`                                                             |
| Distribution                 | Local/self-hosted compiled binary                                         |
| Supermemory version          | `v0.0.3`                                                                  |
| Binary filename              | `supermemory-server`                                                      |
| Binary digest                | `sha256:4036486514bd3511099e8f8642e1c56ecc58550c5e194442e88a5438992c0957` |
| Binary digest source         | Release manifest                                                          |
| Docker image                 | `tenurehq/precisionmembench-supermemory`                                  |
| Docker image digest          | `sha256:<image-digest>`                                                   |
| Built on                     | `2026-06-25`                                                              |
| Retrieval threshold override | None                                                                      |

## Running the Supermemory eval

The Supermemory local binary is packaged into the published Docker image used by PrecisionMemBench. The wrapper source is included in this directory for transparency, so reviewers can inspect the `/add`, `/search`, and `/reset` adapter logic. The benchmark run itself should use the pinned Docker image, not a locally modified wrapper.

To reproduce the published run:

```bash
cd wrappers/supermemory
docker compose up
```

In a second terminal, from the repository root:

```bash
MEMORY_PROVIDER=supermemory RESEED=true npx ava src/retrieval.external.eval.test.ts --timeout 10m
MEMORY_PROVIDER=supermemory npx ava src/session-retrieval.external.eval.test.ts --timeout 10m
```

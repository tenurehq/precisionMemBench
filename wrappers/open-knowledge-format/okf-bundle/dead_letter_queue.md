---
beliefId: b-dead-letter-queue
type: entity
title: dead_letter_queue
description: Failed messages route to a MongoDB-backed dead letter queue with manual replay via admin CLI.
tags: [dead letter, DLQ, failed messages]
scope: domain:code
epistemic_status: active
timestamp: 2026-09-01T00:00:00Z
---

# dead_letter_queue
Failed messages route to a MongoDB-backed dead letter queue with manual replay via admin CLI.
## Why This Matters
Shapes error recovery and messaging answers to assume a DLQ exists rather than suggesting one from scratch.

# Engineer 004 — Real-Time Analytics Pipeline

**Brief version:** [Observed] 2026-07. **Fixture SHA-256:** [Observed] `1aeb24b415009e89fcf8acb5a178410faf216dc17b16920d9849ecc8bbb24235` (verify with `$ shasum -a 256 challenges/engineer-004/fixtures/event_sample.jsonl`).

## Written answer

I would keep the current SDK contract and insert a compatible ingestion adapter, then make a durable stream—not the dashboard database—the boundary between accepting events and processing them. The MVP is Kinesis Data Streams, a Lambda consumer, DynamoDB materialized views for recent counters/segments, and Firehose to an S3 archive/export path. See the [architecture and flow diagram](architecture.md). I choose managed components and narrow event-time features because the brief assigns two senior engineers and a three-month MVP; I defer Kafka/MSK, Flink, OpenSearch, and a new SDK until measurements justify the extra operating surface.

For sizing, [Assumed] 50M events/day, a 10x peak, a 30-day month, and 1 KiB average event size produce [Estimated] 579 events/s average, 5,790 events/s and 5.79 MB/s at peak, and 1.5 TB decimal raw data/month before overhead. Six shards is the arithmetic minimum; [Estimated] 12 provisioned shards give theoretical headroom, subject to hot-key distribution and pre-scaling. Kinesis publishes 1 MB/s or 1,000 records/s per shard and charges shard-hours plus 25 KB PUT units ([AWS pricing](https://aws.amazon.com/kinesis/data-streams/pricing/)). The listed Kinesis + Firehose + first-month S3 subset is [Estimated] about $403/month—not a full-stack quote; Lambda, DynamoDB, networking, logging, security, exports, and redundancy remain to be priced from measured workload. Detailed formulas and sensitivity inputs are in [cost-model.md](cost-model.md).

The edge derives tenant from credentials, normalizes legacy schema aliases, strips direct identifiers from event properties, validates size/time/type, and adds server `received_at`. The canonical identity key and idempotency key are both tenant-scoped. `identify` may link anonymous to authenticated IDs only within a tenant; conflict is quarantined. A small pre-aggregated serving view answers dashboards and bounded behavioral segments without scanning raw events. Each dashboard response exposes freshness and degrades visibly when the consumer falls behind.

Delivery is at-least-once with `(tenant_id,event_id)` idempotency. The edge acknowledges after durable stream acceptance; failed records retry with bounded backoff, invalid/conflicting records go to restricted quarantine, and consumers checkpoint only after their effects commit. This avoids duplicate effects but is not end-to-end exactly-once. We cannot promise zero loss before server acknowledgement without verifying existing browser SDK batching/retries and customer network behavior. Measure accepted-vs-processed counts by tenant/window and reconcile to detect gaps; retain replay capability and explicit rollback.

The fixture analysis changes concrete behavior: `evt-0002` is a retry and is deduplicated; `evt-0005`, `evt-0006`, and `evt-0016` have event clocks ahead of receipt and are held for time review; `evt-0007` contains contact fields and is sanitized; `evt-0009` uses legacy aliases and lacks receipt time; `evt-0011` lacks tenant and is quarantined; `evt-0012`–`evt-0015` look scanner-like and are excluded from personalization pending bot classification; `evt-0017` takes the privacy-control path; malformed line 21 exposes `evt-0020` and is quarantined. Do not trust those records at face value because their timestamps, tenant attribution, direct identifiers, or traffic intent are unsafe/ambiguous. The bot signal is heuristic, not proof. The artifact reports [Observed] 25 lines, 24 valid objects, one malformed object, 23 unique IDs, and a fixture-only receipt/event lag p95 of 0.206s across 17 eligible rows. That is not dashboard latency. [Observed] 11 local tests pass; neither result proves live reliability or the <5-second target. Reproduce using the commands in [README.md](../README.md) and inspect the [decision output](../output/decisions.json).

Deletion is priority control-plane work: authenticate the request, tombstone the tenant-scoped subject, block new events, delete/recompute serving state and exports, find and rewrite affected lake objects, and verify absence from query paths. Backups and downstream warehouse copies have separate retention/notification procedures; the contractual deletion SLA and permitted audit record need customer/legal agreement. The system is designed to support SOC 2/GDPR/CCPA controls; it is not certified or independently audited today.

Migration proceeds by inventory and baseline, server-side shadow mirroring, internal/opt-in tenant canaries, read cutover behind tenant feature flags, then gradual expansion. Compare event counts, schema, identity links, segment output, freshness, and privacy drills per tenant. Roll back reads/writes on unexplained count divergence, freshness/error-budget breach, cross-tenant access, deletion verification failure, or sustained backlog; drain and reconcile before retiring the old path. The existing client contract stays in place throughout.

## Operating artifact

This repo includes a deterministic JSONL analyzer, sanitized decision outputs, tests, source-pinned brief and fixture, architecture, and a reproducible cost model. It does not deploy an AWS pipeline. No cloud load test or production migration was available, so capacity and cost remain hypotheses pending representative payload traces and a provisioned test environment.

## Evidence log

See [evidence-log.md](evidence-log.md) for claim-by-claim evidence tiers, commands, artifacts, and explicit unproven claims. The strongest current evidence is Tier 2–3 (runnable artifact and source/test records); there is no Tier 4 before/after production measurement or Tier 5 independent verification. The report and source tests are [available here](../output/fixture-report.json) and [here](../tests/test_analyze_fixture.py); rerun with `python3 -m unittest discover -s tests -v`.

## Number source labels

Numbers in this answer are labeled **[Assumed]**, **[Estimated]**, or **[Observed]** in context. AWS limits/prices are **[Benchmarked]** public source values, cited inline and itemized in the cost model. Fixture and test values are observed only from the named local artifacts; they must not be presented as production outcomes. Recheck this label policy using `$ python3 scripts/validate_submission.py docs/submission.md` before sharing.

## AI usage disclosure

I used OpenAI Codex to inspect the public challenge materials, implement and refine the fixture analyzer and tests, and help draft the architecture and calculations. I personally inspected the pinned fixture, verified its checksum, reran the tests and public validator, recalculated the capacity/cost inputs, and made the final architecture choices. No private benchmark answer was available or used. The known weak points are unverified SDK retry behavior, unmeasured event-size/tenant distributions, no AWS load test, and incomplete real deletion/compliance validation.

## Failure handling and what stays human

See [architecture.md](architecture.md#reliability-contract) and [failure-handling.md](failure-handling.md). Clock anomalies, schema drift, missing tenant identity, event-key conflicts, suspected bot traffic, and invalid payloads are quarantined or excluded instead of silently changing customer-facing behavior. A privacy request is prioritized and auditable, but ambiguous identity matches, legal retention, and completion approval stay human-reviewed. Humans also approve high-impact segment/personalization policy, tenant cutovers, rollback, and any assertion that an external SLA or compliance control has been met.

## Artifact access

Run locally with Python: see [README.md](../README.md). Main files: `src/analyze_fixture.py`, `tests/test_analyze_fixture.py`, `output/decisions.json`, `output/fixture-report.json`, `docs/architecture.md`, `docs/cost-model.md`, and `docs/evidence-log.md`. [Observed] All are local artifacts until the candidate publishes a repository; no public link or deployed demo exists yet.

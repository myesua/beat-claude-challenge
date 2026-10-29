# Engineer 004 alignment and failure log

This is the working memory for this challenge. Re-read it, the pinned brief, the pinned role rubric, and the fixture checksum before changing the implementation or submission. Update the status and failure log whenever a test, fixture review, design assumption, or validation result changes.

## Pinned challenge materials

- Challenge: Engineer 004 — System Design: Real-Time Analytics Pipeline.
- Brief version: `2026-07`.
- Upstream repository commit inspected: `4b719e4501c8ff98fd3e641c46d3bffe34b9aaa5`.
- Fixture: `challenges/engineer-004/fixtures/event_sample.jsonl`.
- Fixture SHA-256: `1aeb24b415009e89fcf8acb5a178410faf216dc17b16920d9849ecc8bbb24235`.
- The file `claude_baseline.md` in the upstream challenge directory is a **withheld-benchmark notice**, not a sample answer. It explicitly says not to use it as content guidance. No answer key or reviewer benchmark was published. Do not claim to have seen or used a baseline answer.
- Read the full public brief, Engineer 004 scoring rubric, fixture, root README, public SCORING guide, repo ARCHITECTURE, submission instructions, and submission validator. Core requirements below are distilled from those materials.

## Requirements that must stay visible in the final packet

1. **System design:** a complete SDK-to-dashboard data-flow diagram; component choices and rejected alternatives; event schema; user identity stitching.
2. **Scale arithmetic:** size for `50M events/day` and `10x` peaks; label every input as observed, benchmarked, estimated, or assumed; show traffic and storage math and a cost estimate against the `$50K/month` ceiling.
3. **Customer and platform constraints:** preserve the existing SDK/integrations; design for `500+` tenants; meet `<5 seconds` dashboard visibility as a target; handle GDPR/CCPA deletion; keep the plan plausible for two dedicated senior engineers, a three-month MVP, six-month fuller system.
4. **Reliability:** state precise delivery semantics, buffering/backpressure, overload/degradation behavior, retries, idempotency/deduplication, and how data loss/duplication is detected. Do not promise literal end-to-end zero loss without proving the existing SDK retry/ack behavior and client-network limits.
5. **Migration:** phased shadow/parallel run, per-tenant validation, cutover gates, rollback triggers and the no-breaking-change plan.
6. **Fixture:** classify actual anomaly classes and cite actual `event_id`s; identify at least three records not safe to act on at face value; state what the small sample cannot establish; include the checksum.
7. **Tradeoffs and scope:** explain chosen options, what is sacrificed, failure modes, MVP exclusions, and what extra time/budget would change.
8. **Packet:** written answer (maximum four pages; diagrams excluded), inspectable operating artifact, evidence log with Tier 0–5 mapping, source labels on all numeric claims, AI usage disclosure, failure handling, and human-only decisions. Keep the role brief version stamp.

## Fixture findings currently detected by the analyzer

These are observations from the pinned synthetic fixture, not claims about any live system. The decision file is `output/decisions.json`; the aggregate report is `output/fixture-report.json`.

- `evt-0002` appears twice for the same tenant with matching semantic content and different `received_at`: treat as an idempotent retry, not a second event.
- `evt-0005`, `evt-0006`, and `evt-0016` have event timestamps materially ahead of receipt timestamps. Do not feed these clock-anomalous records to live dashboards/personalization; quarantine for clock/source review and possible controlled backfill.
- `evt-0007` includes email and phone properties. The decision artifact must never repeat their values; sanitize before durable analytics storage and retain only safe evidence such as property names and event ID.
- `evt-0009` uses legacy aliases (`pageview`, `timestamp`, `page_path`, `ref`) and lacks `received_at`. Normalize the recognized schema without changing the client contract; mark ingestion latency as unmeasurable for this record.
- `evt-0011` has no tenant identifier. Quarantine rather than infer a tenant.
- `evt-0012`–`evt-0015` arrive as a rapid page-view burst from a scanner-like referrer. Preserve safely for audit, but exclude from human-behavior metrics/personalization pending bot classification; a single referrer heuristic is not definitive proof of a bot.
- `evt-0017` is a GDPR delete-all request. Route it through a priority privacy-control workflow; suppress subsequent use, delete/propagate tombstones through raw, serving, cache, and export stores, and preserve only the legally permitted audit record.
- Physical line 21 is malformed JSON and still exposes `evt-0020` in the damaged text. Quarantine and retain enough restricted diagnostic material for repair/replay, not a false successful acknowledgement.
- The fixture is tiny and synthetic; it does not measure production event loss, SDK retry behavior, traffic distribution, latency SLOs, AWS throughput, or privacy completion time.

## Current local measurement (not a production benchmark)

- [Observed] `25` physical lines; `24` parse as JSON objects; `1` malformed line; `23` distinct event IDs among parseable objects.
- [Observed] Analyzer classifications: `12` ACCEPT; `4` ACCEPT_EXCLUDED_FROM_PERSONALIZATION; `1` DEDUPLICATE; `1` NORMALIZE_AND_ACCEPT; `1` PRIORITY_PRIVACY_CONTROL; `2` QUARANTINE; `3` QUARANTINE_TIME_REVIEW; `1` SANITIZE_AND_ACCEPT.
- [Observed] For `17` fixture records eligible under the analyzer's local live-ingest lag filter, `received_at - ts` is `0.119s` minimum, `0.163s` median, and `0.206s` p95. This is a fixture clock-difference statistic only—not browser-independent pipeline latency and not evidence the architecture meets `<5s`.
- [Observed] Local fixture-only analyzer runtime varies by run (recent runs were approximately 0.002 seconds for 24 JSON objects). This tiny measurement is timer/environment noise; omit the rate from the public narrative and never treat it as production capacity evidence.
- [Assumed] Analyzer policy thresholds are a `30s` future-clock tolerance and `300s` late-arrival threshold. They are reviewable prototype rules, not a regulatory or customer SLA.

## Failure log and known gaps (keep this current)

### Confirmed

- The challenge's `claude_baseline.md` contains only a withheld-benchmark notice; treating it as an architecture baseline would be a mistake.
- `evt-0005`, `evt-0006`, `evt-0016` are all future-time/clock-skew anomalies (negative `received_at - ts`), not ordinary delayed-arrival events. The analyzer has a separate late-event branch, covered by a synthetic unit test, but the pinned fixture has no valid late-arrival example.
- [Observed] Current local test suite: `11` unit tests pass. These test analyzer behavior, not AWS deployment, load, data durability, or compliance.
- The first submission pre-screen run passed required sections and integrity checks but emitted four advisory warnings: two unlabeled-number paragraphs (metadata and artifact access) and two sections without a checkable artifact reference. These are recorded as document failures, not hidden; the submission was revised to label the metadata, add local evidence paths/commands, and rerun the validator.
- A subsequent `--strict` run still failed one advisory check because the opening observed fixture checksum lacked its verification command in that section. The checksum command was added inline; this specific failure is expected to clear on the final rerun.
- The first cost draft used decimal GB for Firehose's 5 KiB billing units, while AWS's pricing example converts with 1,048,576 KiB/GiB. The Firehose subtotal and grand subtotal were corrected before finalization; see `docs/cost-model.md` for explicit units and source.
- [Observed] The latest submission pre-screen passes required headings, review-integrity scan, evidence-tier scan, and brief-version check. See the current validator output in the session; rerun `python3 scripts/validate_submission.py docs/submission.md` before public sharing.
- The `<5s` target cannot be verified from this fixture. No production AWS account, workload, baseline traces, representative event-size distribution, tenant skew, or load test is available in this workspace.

### Must be resolved before calling the submission complete

- Determine envelope/schema behavior and whether the current JS SDK retries or batches; the prompt forbids a required breaking SDK update. No actual SDK source or customer integration was supplied for verification.
- Add explicit full-packet mapping from each seeded anomaly to its operational handling, and ensure three “not at face value” examples are explained in the written answer.
- Add event schema, tenant-safe identity-stitching rules, cost model with named AWS pricing source and all assumptions, and migration/rollback gates.
- Add measured/reproducible load test for the prototype artifact if practical. Do not imply that synthetic local tests prove AWS throughput or zero loss.
- Review raw PII quarantine policy: avoid durable retention of cleartext PII, minimize access/TTL, and ensure logs/errors do not leak payload values.
- Explain privacy deletion across data lake, stream replays, aggregates, caches, warehouses, and backups. State backup deletion limits and legal/SLA assumptions instead of promising instant physical erasure.
- Review analyzer report semantics and tests after every change; check that no raw sensitive values enter output or logs.
- Run the official submission validator against the final answer, fix required-section failures and advisory warnings where they are legitimate, then re-check the four-page written limit.
- Check current upstream commit/brief version and recompute the fixture hash immediately before submission; fixtures rotate.

## Design posture

- Prefer a small, operable MVP for two engineers over a stack of fashionable components.
- Treat “zero data loss” as an objective only at a clearly defined durability boundary. Be explicit that browser/network loss before server acknowledgement cannot be fixed server-side without compatible client retry behavior.
- Use at-least-once delivery plus tenant-scoped idempotency and reconciliation; avoid claiming end-to-end exactly-once semantics.
- Do not expose inferred identity across tenants. Identity keys and dedupe keys must be tenant-scoped.
- Keep human review for privacy deletion ambiguity, identity conflicts, schema drift, and any action that changes customer-facing personalization based on low-confidence signals.
- Never claim a production incident was prevented, an SLA was achieved, a system was load-tested, or a customer outcome was measured unless a checkable source exists.

# Failure handling and validation plan

| Failure / ambiguity | Detection | Immediate action | Recovery / human gate |
|---|---|---|---|
| Partial Kinesis write or throttling | Per-record PutRecords result; edge 5xx/retry and write metrics | Retry only failed records with bounded exponential backoff + jitter; do not acknowledge failed records | Alert on retry exhaustion; restricted DLQ, replay after capacity/schema correction |
| Client disconnect before durable acknowledgement | Edge request/stream ack metrics; compare request attempts where possible | Return retryable response only if compatible SDK behavior is verified; rate-limit abuse | Inspect existing SDK retry/backoff before asserting loss protection; cannot recover an event never resent |
| Duplicate retry | `(tenant_id,event_id)` idempotency state; duplicate counter | Suppress repeated state mutation | Preserve audit count; quarantine if same key carries different semantic payload |
| Hot tenant/partition key | Per-shard throughput/throttle and tenant lag | Apply tenant quota; avoid naive tenant-only partition key; shed nonessential enrichment | Reshard/re-key only with ordering/identity review; pre-scale for known campaigns |
| Consumer crash or poison record | Lambda error/iterator age, retry age, DLQ count | Pause/retry affected shard; isolate poison records to DLQ without blocking all tenants where possible | Replay after patch; reconcile accepted/processed totals before clearing incident |
| Dashboard data stale | End-to-end freshness and stream iterator age | Mark UI/API stale; never label old aggregates “live” | Restore consumer and backfill from stream/archive; customer communication if thresholds breached |
| Schema drift / malformed JSON | Version/type validation; quarantine reason counts | Do not guess fields or publish malformed payload | Keep restricted diagnostic evidence; add supported mapping after compatibility review; replay |
| Missing or conflicting tenant/identity | Envelope validation; mapping conflict metrics | Quarantine; no inferred tenant, no cross-tenant merge | Human verifies auth and source identity before repair/replay |
| Suspected bot/scanner traffic | Heuristic referrer/rate signals | Preserve for audit but exclude from human personalization pending policy | Human-reviewed classifier thresholds; do not call heuristic a verified bot label |
| PII in properties/logs | Allowlist scan and synthetic test; log scan | Remove before durable analytics; redact diagnostics and restrict quarantine | Security review; deletion/search of affected stores and incident process if persisted |
| Privacy deletion request | Priority queue age and tombstone state machine | Tombstone subject; suppress new use; prioritize serving/export deletion | Verify every store/export path, rewrite affected lake objects, record legally permitted proof; human signs off ambiguous requests |
| AWS regional/service outage | Health checks, Kinesis/Lambda/DDB errors | Buffer within retention; degrade dashboard freshness; protect privacy controls and stop accepting data without durability | Replay after recovery; multi-region is a later, cost-bearing design decision, not an assumed MVP feature |

## Readiness gates before production claims

- Inspect current SDK versions and prove retry/ack/timeout compatibility with a fault-injection endpoint.
- Replay representative sanitized production payloads; test p50/p95/p99 sizes, skewed tenants, and planned 10x peak duration.
- Load test the complete edge → stream → materialized view → dashboard path and measure p95/p99 freshness, errors, backlog age, and cost.
- Inject consumer restarts, partial writes, throttling, poison records, S3/Firehose delivery faults, and deletion requests; prove recovery and reconciliation.
- Validate tenant authorization, key isolation, redaction, encryption/KMS policy, audit access, backup retention, and export credentials.
- Confirm compliance language and deletion SLA with security/legal/customer owners. Passing these gates is required before claiming achieved latency, zero loss, certification, or deletion completion.

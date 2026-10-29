# Evidence log

| Claim | Evidence | Tier | Limit / interpretation |
|---|---|---:|---|
| Fixture parser identifies the seeded retry, time anomalies, PII property paths, legacy aliases, missing tenant, scanner-like burst, privacy request, and malformed JSON. | Reproduce with `python3 src/analyze_fixture.py ...`; inspect `output/decisions.json`, `output/fixture-report.json`, tests in `tests/test_analyze_fixture.py`. | 2–3 | Deterministic local operating artifact plus source/test records against one synthetic fixture; not production ingestion. |
| The fixture contains 25 physical lines, 24 valid JSON objects, one malformed record, and 23 distinct event IDs. | `output/fixture-report.json`; SHA-256 `1aeb24b415009e89fcf8acb5a178410faf216dc17b16920d9849ecc8bbb24235`. | 3 | Observed from the pinned file, not an external dataset. |
| The eligible fixture event/receipt timestamp differences are min 0.119s, median 0.163s, p95 0.206s for 17 records. | `output/fixture-report.json` and analyzer definition. | 3 | Fixture-only timestamp arithmetic; not SDK-to-dashboard latency and cannot validate the <5-second goal. |
| The prototype analyzer's current unit suite passes. | `python3 -m unittest discover -s tests -v`; 11 tests in `tests/`. | 3 | Unit coverage does not establish AWS behavior, sustained load, security certification, or end-to-end loss rate. |
| AWS Kinesis per-shard limits and price inputs. | Linked official Kinesis pricing in `docs/cost-model.md`. | 3 | Public benchmark/source, not deployment measurement; region and date affect price. |
| Candidate architecture can support the target workload. | Capacity arithmetic and topology in `docs/architecture.md` and `docs/cost-model.md`. | 0–1 | Design hypothesis only until representative load test, failure injection, and cost observation on AWS. |
| Under-five-second visibility, zero loss, deletion completion, compliance certification, and customer outcomes. | No production environment, baseline traces, customer data, or independent audit was supplied. | 0 | Explicitly unproven; no claim is made. |

## Number sources

- **Observed**: values calculated from the pinned synthetic fixture or local test execution; artifacts and commands are linked above.
- **Estimated**: derived capacity/cost arithmetic; formula and inputs appear beside each estimate.
- **Benchmarked**: externally published AWS service limits/pricing linked in the cost model; these are public reference values, not our benchmark run.
- **Assumed**: workload or design placeholder taken from the brief or explicitly selected for calculation, including 1 KiB average payload, 10x multiplier, 30-day month, and 24h retention.

## AI use and human review

AI coding assistance was used to inspect the public challenge files, draft and implement the analyzer/tests, and help structure architecture and cost reasoning. The candidate must verify the current challenge repository version/hash, inspect the source fixture and generated decisions, recalculate the capacity math, validate regional AWS prices, and be ready to explain each tradeoff live. No private baseline answer was available or used. No fabricated production telemetry, customer outcome, or benchmark is included.

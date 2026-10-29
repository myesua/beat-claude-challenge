# Beat Claude — Engineer 004

Candidate work product for Single Grain's `Engineer 004: System Design — Real-Time Analytics Pipeline` challenge.

This repository is being built against the public `2026-07` brief and the fixture present in the upstream repository commit recorded in [`docs/source-provenance.md`](docs/source-provenance.md). The fixture is copied verbatim so the analysis can be rerun. It is synthetic challenge data, not customer data.

## What is here

- `challenges/engineer-004/brief.md` — public challenge brief.
- `challenges/engineer-004/fixtures/event_sample.jsonl` — exact public fixture used.
- `src/analyze_fixture.py` — deterministic, standard-library-only fixture analyzer.
- `tests/` — tests for malformed input, tenant isolation, idempotency, schema compatibility, PII handling, bot-like traffic, time anomalies, and privacy control events.
- `output/` — reproducible decision file and measured fixture report.
- `docs/` — architecture, findings, decisions, validation, and submission write-up.

## Reproduce

From the repository root, using Python 3.10 or newer:

```bash
python3 -m unittest discover -s tests -v
python3 src/analyze_fixture.py challenges/engineer-004/fixtures/event_sample.jsonl --json-out output/decisions.json --report-out output/fixture-report.json
python3 scripts/validate_submission.py docs/submission.md
```

The analyzer writes no raw property values to its decision output. It records event IDs, source line numbers, classification codes, and handling decisions. The source fixture itself contains synthetic contact details as part of the challenge, so outputs intentionally retain only the affected property names.

## Scope and honesty

The runnable artifact analyzes the challenge fixture; it is not a deployed streaming service and does not prove production throughput, zero-loss guarantees, customer adoption, or AWS service-level performance. Architecture capacity numbers are explicitly labeled by source type. Production performance and cost require load tests and an AWS account/environment supplied by the hiring team.

AI assistance is disclosed in the submission. The candidate must review the final decisions and be prepared to explain them live before sharing this repository.

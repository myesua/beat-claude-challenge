#!/usr/bin/env python3
"""Analyze the public Engineer 004 JSONL fixture without external packages.

The analyzer is deliberately deterministic and conservative. It does not
call an LLM, infer a person's identity, or emit event property values.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_INGEST_LAG_SECONDS = 300
MAX_FUTURE_CLOCK_SKEW_SECONDS = 30
BOT_REFERRER_RE = re.compile(r"(?:bot|crawler|spider|scanner)", re.I)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d().\s-]{7,}\d)(?!\w)")
EVENT_ID_RE = re.compile(r'"event_id"\s*:\s*"([^"]+)"')


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _find_sensitive_properties(value: Any, path: str = "") -> list[str]:
    """Return sensitive property paths only; never return matched values."""
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            key_is_sensitive = re.search(r"email|phone|mobile|telephone", str(key), re.I)
            if key_is_sensitive and child not in (None, ""):
                found.append(child_path)
            elif isinstance(child, (dict, list)):
                found.extend(_find_sensitive_properties(child, child_path))
            elif isinstance(child, str) and (EMAIL_RE.search(child) or PHONE_RE.search(child)):
                found.append(child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_sensitive_properties(child, f"{path}[{index}]"))
    return found


def normalize_event(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    event = dict(raw)
    anomalies: list[str] = []
    if "ts" not in event and "timestamp" in event:
        event["ts"] = event.pop("timestamp")
        anomalies.append("legacy_timestamp_field")
    if event.get("type") == "pageview":
        event["type"] = "page_view"
        anomalies.append("legacy_event_type_alias")
    props = event.get("properties")
    if isinstance(props, dict):
        props = dict(props)
        if "path" not in props and "page_path" in props:
            props["path"] = props.pop("page_path")
            anomalies.append("legacy_page_path_field")
        if "referrer" not in props and "ref" in props:
            props["referrer"] = props.pop("ref")
            anomalies.append("legacy_referrer_field")
        event["properties"] = props
    return event, anomalies


def _semantic_payload(event: dict[str, Any]) -> str:
    """Stable semantic fingerprint; receipt metadata must not defeat retries."""
    semantic = {k: v for k, v in event.items() if k not in {"received_at", "server_received_at"}}
    return json.dumps(semantic, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def analyze_text(text: str, source_path: str = "<memory>") -> dict[str, Any]:
    started = time.perf_counter()
    lines = text.splitlines()
    decisions: list[dict[str, Any]] = []
    seen: dict[tuple[str, str], str] = {}
    ingest_lags: list[float] = []
    lag_excluded_ids: list[str] = []
    observed_ids: set[str] = set()
    anomaly_totals: Counter[str] = Counter()

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            decisions.append({
                "source_line": line_number,
                "event_id": None,
                "decision": "IGNORE_EMPTY_LINE",
                "anomalies": ["empty_line"],
                "reason": "Empty line contains no event record.",
            })
            anomaly_totals["empty_line"] += 1
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            match = EVENT_ID_RE.search(line)
            event_id = match.group(1) if match else None
            anomaly_totals["malformed_json"] += 1
            decisions.append({
                "source_line": line_number,
                "event_id": event_id,
                "decision": "QUARANTINE",
                "anomalies": ["malformed_json"],
                "reason": "JSON parsing failed; retain only the restricted raw record for diagnosis, then replay after repair.",
            })
            continue

        if not isinstance(raw, dict):
            anomaly_totals["non_object_json"] += 1
            decisions.append({
                "source_line": line_number,
                "event_id": None,
                "decision": "QUARANTINE",
                "anomalies": ["non_object_json"],
                "reason": "Each JSONL record must be an object.",
            })
            continue

        event, anomalies = normalize_event(raw)
        event_id = event.get("event_id") if isinstance(event.get("event_id"), str) else None
        tenant_id = event.get("tenant_id") if isinstance(event.get("tenant_id"), str) and event.get("tenant_id") else None
        event_type = event.get("type") if isinstance(event.get("type"), str) and event.get("type") else None
        event_time = parse_time(event.get("ts"))
        received_time = parse_time(event.get("received_at"))
        props = event.get("properties")
        payload_problems: list[str] = []
        if not event_id:
            payload_problems.append("missing_event_id")
        if not tenant_id:
            payload_problems.append("missing_tenant_id")
        if not event_type:
            payload_problems.append("missing_event_type")
        if event_time is None:
            payload_problems.append("missing_or_invalid_event_time")
        if not isinstance(props, dict):
            payload_problems.append("missing_or_invalid_properties_object")

        if "received_at" not in event:
            anomalies.append("received_at_missing_latency_unmeasurable")
        elif received_time is None:
            payload_problems.append("invalid_received_at")

        pii_paths = _find_sensitive_properties(props)
        if pii_paths:
            anomalies.append("sensitive_property_detected")

        lag: float | None = None
        if event_time is not None and received_time is not None:
            lag = (received_time - event_time).total_seconds()
            if lag < -MAX_FUTURE_CLOCK_SKEW_SECONDS:
                anomalies.append("event_time_ahead_of_receipt_clock_skew")
            elif lag > MAX_INGEST_LAG_SECONDS:
                anomalies.append("late_arrival_over_five_minutes")

        referrer = props.get("referrer") if isinstance(props, dict) else None
        if isinstance(referrer, str) and BOT_REFERRER_RE.search(referrer):
            anomalies.append("bot_like_referrer")

        canonical_json = _semantic_payload(event)
        duplicate_key: tuple[str, str] | None = (tenant_id, event_id) if tenant_id and event_id else None
        duplicate_of: int | None = None
        duplicate_conflict = False
        if duplicate_key and duplicate_key in seen:
            if seen[duplicate_key] == canonical_json:
                anomalies.append("duplicate_event_retry")
                prior = next((d for d in decisions if d.get("tenant_id") == tenant_id and d.get("event_id") == event_id and d.get("decision") != "DEDUPLICATE"), None)
                duplicate_of = prior.get("source_line") if prior else None
            else:
                anomalies.append("duplicate_key_payload_conflict")
                duplicate_conflict = True
        elif duplicate_key:
            seen[duplicate_key] = canonical_json

        if event_id:
            observed_ids.add(event_id)
        anomaly_totals.update(anomalies)
        anomaly_totals.update(payload_problems)

        if payload_problems:
            decision = "QUARANTINE"
            reason = "Required envelope fields are missing or invalid; do not publish to customer-facing consumers."
        elif duplicate_conflict:
            decision = "QUARANTINE"
            reason = "The same tenant-scoped event key has different semantic content; preserve for conflict investigation."
        elif "duplicate_event_retry" in anomalies:
            decision = "DEDUPLICATE"
            reason = "Idempotent retry matches the prior semantic event; receipt timestamp does not create a second event."
        elif event_type == "privacy_request":
            decision = "PRIORITY_PRIVACY_CONTROL"
            reason = "Route to the privacy deletion workflow and suppress downstream use pending verified completion."
        elif "event_time_ahead_of_receipt_clock_skew" in anomalies:
            decision = "QUARANTINE_TIME_REVIEW"
            reason = "Event time is more than the configured 30-second tolerance ahead of receipt time; exclude from live metrics until repaired or approved for backfill."
        elif "late_arrival_over_five_minutes" in anomalies:
            decision = "ACCEPT_HISTORICAL_ONLY"
            reason = "Preserve for historical correction after validation; exclude from real-time personalization and ingestion-latency SLO."
        elif pii_paths:
            decision = "SANITIZE_AND_ACCEPT"
            reason = "Remove sensitive property values before durable analytics storage; retain property-path evidence only."
        elif "bot_like_referrer" in anomalies:
            decision = "ACCEPT_EXCLUDED_FROM_PERSONALIZATION"
            reason = "Preserve for audit/bot analysis but exclude from human-behavior metrics and personalization pending bot policy."
        elif any(item.startswith("legacy_") for item in anomalies):
            decision = "NORMALIZE_AND_ACCEPT"
            reason = "Map recognized legacy fields to the canonical envelope and record the schema version/normalization path."
        else:
            decision = "ACCEPT"
            reason = "Envelope passes fixture checks; downstream processing remains subject to idempotency and tenant-scoped access controls."

        if lag is not None:
            if decision in {"ACCEPT", "SANITIZE_AND_ACCEPT", "ACCEPT_EXCLUDED_FROM_PERSONALIZATION", "NORMALIZE_AND_ACCEPT"} and "duplicate_event_retry" not in anomalies:
                ingest_lags.append(lag)
            elif event_id:
                lag_excluded_ids.append(event_id)

        output = {
            "source_line": line_number,
            "event_id": event_id,
            "tenant_id": tenant_id,
            "event_type": event_type,
            "decision": decision,
            "anomalies": sorted(set(anomalies + payload_problems)),
            "reason": reason,
        }
        if duplicate_of is not None:
            output["duplicate_of_line"] = duplicate_of
        if pii_paths:
            output["sensitive_property_paths"] = sorted(set(pii_paths))
        if lag is not None:
            output["observed_fixture_lag_seconds"] = round(lag, 3)
        decisions.append(output)

    valid_json_count = sum(1 for item in decisions if "malformed_json" not in item["anomalies"] and "non_object_json" not in item["anomalies"] and "empty_line" not in item["anomalies"])
    decision_counts = Counter(item["decision"] for item in decisions)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    elapsed = time.perf_counter() - started
    lag_stats: dict[str, float | int] = {"n": len(ingest_lags)}
    if ingest_lags:
        ordered = sorted(ingest_lags)
        p95_index = max(0, math.ceil(0.95 * len(ordered)) - 1)
        lag_stats.update({
            "min_seconds": round(ordered[0], 3),
            "median_seconds": round(statistics.median(ordered), 3),
            "p95_seconds": round(ordered[p95_index], 3),
            "max_seconds": round(ordered[-1], 3),
        })

    return {
        "source": source_path,
        "fixture_sha256": digest,
        "counts": {
            "physical_lines": len(lines),
            "json_records": valid_json_count,
            "malformed_or_non_object_records": decision_counts["QUARANTINE"] - sum(1 for d in decisions if d["decision"] == "QUARANTINE" and "malformed_json" not in d["anomalies"] and "non_object_json" not in d["anomalies"]),
            "unique_event_ids_observed": len(observed_ids),
            "decisions": dict(sorted(decision_counts.items())),
            "anomalies": dict(sorted(anomaly_totals.items())),
        },
        "latency_measurement": {
            "definition": "received_at minus ts for events accepted into live processing; excludes invalid-clock events, late arrivals, retries, and missing receipt times",
            "thresholds_seconds": {
                "future_clock_skew_tolerance": MAX_FUTURE_CLOCK_SKEW_SECONDS,
                "late_arrival_cutoff": MAX_INGEST_LAG_SECONDS,
            },
            "eligible_event_lag_seconds": lag_stats,
            "excluded_event_ids": lag_excluded_ids,
        },
        "runtime_measurement": {
            "analysis_elapsed_seconds": round(elapsed, 6),
            "parsed_json_records_per_second": round(valid_json_count / elapsed, 1) if elapsed > 0 else None,
            "scope": "single local fixture-analysis run only; not a production or AWS throughput benchmark",
        },
        "decisions": decisions,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path, help="JSONL fixture path")
    parser.add_argument("--json-out", type=Path, help="write complete decision packet JSON")
    parser.add_argument("--report-out", type=Path, help="write report JSON (same data as decision packet)")
    args = parser.parse_args(argv)
    try:
        text = args.fixture.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot read fixture: {exc}", file=sys.stderr)
        return 2
    result = analyze_text(text, str(args.fixture))
    serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    for target in (args.json_out, args.report_out):
        if target:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(serialized, encoding="utf-8")
    if not args.json_out and not args.report_out:
        print(serialized, end="")
    else:
        print(json.dumps({"counts": result["counts"], "fixture_sha256": result["fixture_sha256"], "latency_measurement": result["latency_measurement"], "runtime_measurement": result["runtime_measurement"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

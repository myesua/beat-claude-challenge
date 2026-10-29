import json
import unittest

from src.analyze_fixture import analyze_text


def event(event_id="e-1", tenant_id="t-1", **overrides):
    record = {
        "event_id": event_id,
        "tenant_id": tenant_id,
        "anonymous_id": "anon-1",
        "user_id": None,
        "type": "page_view",
        "ts": "2026-01-01T00:00:00Z",
        "received_at": "2026-01-01T00:00:01Z",
        "properties": {"path": "/"},
    }
    record.update(overrides)
    return json.dumps(record)


class AnalyzerTests(unittest.TestCase):
    def analyze(self, *records):
        return analyze_text("\n".join(records))

    def by_id(self, result, event_id):
        return next(item for item in result["decisions"] if item["event_id"] == event_id)

    def test_malformed_json_is_quarantined_without_losing_recoverable_id(self):
        result = self.analyze('{"event_id":"e-bad",')
        item = self.by_id(result, "e-bad")
        self.assertEqual(item["decision"], "QUARANTINE")
        self.assertIn("malformed_json", item["anomalies"])

    def test_missing_tenant_is_quarantined(self):
        result = self.analyze(event(tenant_id=None))
        self.assertEqual(self.by_id(result, "e-1")["decision"], "QUARANTINE")

    def test_same_event_key_in_different_tenants_is_not_deduplicated(self):
        result = self.analyze(event("same", "t-1"), event("same", "t-2"))
        self.assertEqual([d["decision"] for d in result["decisions"]], ["ACCEPT", "ACCEPT"])

    def test_identical_retry_ignores_received_at(self):
        first = json.loads(event("retry"))
        retry = dict(first, received_at="2026-01-01T00:00:07Z")
        result = self.analyze(json.dumps(first), json.dumps(retry))
        self.assertEqual(result["decisions"][1]["decision"], "DEDUPLICATE")
        self.assertEqual(result["decisions"][1]["duplicate_of_line"], 1)

    def test_conflicting_duplicate_is_quarantined(self):
        first = json.loads(event("conflict"))
        second = dict(first, properties={"path": "/changed"})
        result = self.analyze(json.dumps(first), json.dumps(second))
        self.assertEqual(result["decisions"][1]["decision"], "QUARANTINE")
        self.assertIn("duplicate_key_payload_conflict", result["decisions"][1]["anomalies"])

    def test_legacy_schema_is_normalized(self):
        result = self.analyze(json.dumps({
            "event_id": "legacy", "tenant_id": "t-1", "type": "pageview",
            "timestamp": "2026-01-01T00:00:00Z", "properties": {"page_path": "/x", "ref": "https://example.test"},
        }))
        item = self.by_id(result, "legacy")
        self.assertEqual(item["decision"], "NORMALIZE_AND_ACCEPT")
        self.assertIn("received_at_missing_latency_unmeasurable", item["anomalies"])

    def test_sensitive_values_never_appear_in_decision_output(self):
        record = json.loads(event("pii", properties={"contact_email": "person@example.test", "phone": "+1-555-0100"}))
        result = self.analyze(json.dumps(record))
        output = json.dumps(result)
        self.assertEqual(self.by_id(result, "pii")["decision"], "SANITIZE_AND_ACCEPT")
        self.assertNotIn("person@example.test", output)
        self.assertNotIn("555-0100", output)
        self.assertIn("contact_email", output)

    def test_bot_like_referrer_is_not_used_for_personalization(self):
        result = self.analyze(event("bot", properties={"path": "/", "referrer": "https://scanner.example.test"}))
        item = self.by_id(result, "bot")
        self.assertEqual(item["decision"], "ACCEPT_EXCLUDED_FROM_PERSONALIZATION")

    def test_future_event_time_is_quarantined(self):
        result = self.analyze(event("clock", ts="2026-01-01T00:01:00Z"))
        item = self.by_id(result, "clock")
        self.assertEqual(item["decision"], "QUARANTINE_TIME_REVIEW")

    def test_late_event_is_historical_only(self):
        result = self.analyze(event("late", received_at="2026-01-01T00:10:00Z"))
        self.assertEqual(self.by_id(result, "late")["decision"], "ACCEPT_HISTORICAL_ONLY")

    def test_privacy_request_takes_priority_route(self):
        result = self.analyze(event("delete", type="privacy_request", properties={"request": "delete_all_data"}))
        self.assertEqual(self.by_id(result, "delete")["decision"], "PRIORITY_PRIVACY_CONTROL")


if __name__ == "__main__":
    unittest.main()

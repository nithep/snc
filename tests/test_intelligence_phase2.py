#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for SNC Intelligence Phase 2 read-only analytics."""

import unittest
from datetime import datetime

from api.services.intelligence.clinical import ClinicalAnalyticsAgent
from api.services.intelligence.handover import ShiftHandoverAgent


class IntelligencePhase2Test(unittest.TestCase):
    NOW = datetime(2026, 9, 2, 12, 0, 0)

    def event(self, room, minutes_ago, *, event_type="CALL_BEDSIDE", status="resolved",
              ack=10, resolution=60, breached=False):
        return {
            "room_id": str(room),
            "event_type": event_type,
            "status": status,
            "timestamp": (self.NOW.replace() - __import__("datetime").timedelta(minutes=minutes_ago)).isoformat(),
            "acknowledged_at": None,
            "resolved_at": None,
            "ack_time_seconds": ack,
            "resolution_time_seconds": resolution,
            "sla_breached": breached,
        }

    def test_clinical_agent_detects_frequent_callers(self):
        events = [self.event("401", minutes) for minutes in (10, 20, 30)]
        events.append(self.event("402", 15, event_type="INFO_UPDATE"))
        result = ClinicalAnalyticsAgent(frequent_min_calls=3).analyze(events, now=self.NOW)
        self.assertEqual(result["frequent_callers"][0]["room_id"], "0401")
        self.assertEqual(result["frequent_callers"][0]["call_count"], 3)
        self.assertTrue(result["safety"]["requires_human_review"])

    def test_clinical_agent_calculates_sla_drift(self):
        recent = [self.event("401", 10, ack=40, resolution=100)]
        baseline = [self.event("402", 24 * 60 * 2, ack=10, resolution=50)]
        result = ClinicalAnalyticsAgent(baseline_days=7).analyze(
            recent + baseline, now=self.NOW, window_hours=1
        )
        self.assertEqual(result["sla_drift"]["drift_seconds"]["ack"], 30.0)
        self.assertEqual(result["sla_drift"]["status"], "degraded")

    def test_handover_is_draft_and_keeps_open_cases(self):
        events = [
            self.event("401", 60, status="resolved"),
            self.event("401", 120, status="active", ack=None, resolution=None),
            self.event("402", 180, event_type="CALL_BATHROOM_EMERGENCY"),
        ]
        result = ShiftHandoverAgent().generate(events, shift="morning", at=self.NOW)
        self.assertEqual(result["status"], "draft")
        self.assertTrue(result["safety"]["draft_only"])
        self.assertFalse(result["safety"]["filed"])
        self.assertEqual(result["summary"]["open_cases"], 1)
        self.assertEqual(result["summary"]["emergency_cases"], 1)
        self.assertEqual(result["rooms_to_watch"][0]["room_id"], "0401")

    def test_handover_rejects_unknown_shift(self):
        with self.assertRaises(ValueError):
            ShiftHandoverAgent().generate([], shift="unknown", at=self.NOW)


if __name__ == "__main__":
    unittest.main(verbosity=2)

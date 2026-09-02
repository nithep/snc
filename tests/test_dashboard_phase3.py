#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static contract checks for the Phase 3 dashboard integration."""

import unittest
from pathlib import Path


class DashboardPhase3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parent.parent
        cls.html = (root / "app" / "index.html").read_text(encoding="utf-8")

    def test_smart_insight_panel_is_present(self):
        for marker in (
            'id="insightContent"',
            'id="insightState"',
            "/api/intelligence/clinical?window_hours=24",
            "function loadClinicalInsights()",
        ):
            self.assertIn(marker, self.html)

    def test_handover_modal_is_present(self):
        for marker in (
            'id="handoverModal"',
            'id="handoverShift"',
            'id="handoverDraft"',
            'id="copyHandoverBtn"',
            "/api/intelligence/handover?shift=",
            "navigator.clipboard.writeText",
        ):
            self.assertIn(marker, self.html)

    def test_emergency_controls_remain_distinct(self):
        self.assertIn(".btn-ack", self.html)
        self.assertIn(".btn-clear", self.html)
        self.assertIn(".room-card.st-emergency", self.html)
        self.assertIn(".insight-panel", self.html)


if __name__ == "__main__":
    unittest.main(verbosity=2)

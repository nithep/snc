#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for the SNC Intelligence Phase 1 Ops Agent."""

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path

from api.services.intelligence.ops_agent import (
    OpsAgentConfig,
    OpsSelfHealingAgent,
    OpsThresholds,
)


class OpsAgentTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "nurse_call_events.db"
        self.request_path = Path(self.tmp.name) / "reconnect.json"
        self.now = 1000.0
        self.config = OpsAgentConfig(
            pbx_host="pbx",
            pbx_port=23,
            proxy_host="proxy",
            proxy_port=2323,
            backend_url="http://backend",
            db_path=str(self.db_path),
            reconnect_request_file=str(self.request_path),
            auto_reconnect=True,
            thresholds=OpsThresholds(
                reconnect_cooldown_seconds=60,
                max_reconnect_requests=2,
                disk_warning_percent=101.0,
            ),
        )
        self.tcp_results = {("pbx", 23): True, ("proxy", 2323): True}

    def tearDown(self):
        self.tmp.cleanup()

    def agent(self):
        return OpsSelfHealingAgent(
            self.config,
            clock=lambda: self.now,
            tcp_checker=lambda host, port, timeout: self.tcp_results[(host, port)],
            http_checker=lambda url, timeout: {"status": "healthy", "service": "snc-backend"},
        )

    def test_health_report_is_operator_safe(self):
        self.db_path.write_bytes(b"sqlite")
        report = self.agent().collect_health()
        self.assertEqual(report["status"], "healthy")
        self.assertEqual(report["checks"]["backend"]["status"], "healthy")
        self.assertFalse(report["safe_execution"]["restart_services"])
        self.assertFalse(report["safe_execution"]["modify_alerts"])
        self.assertFalse(report["safe_execution"]["export_patient_data"])
        report_json = json.dumps(report).lower()
        for prohibited in ("rawsmdrlog", "roomid", "fhir_payload", "payload"):
            self.assertNotIn(prohibited, report_json)

    def test_missing_pbx_requests_bounded_reconnect(self):
        self.db_path.write_bytes(b"sqlite")
        self.tcp_results[("pbx", 23)] = False
        agent = self.agent()
        result = agent.remediate(agent.collect_health())
        self.assertEqual(result["action"]["status"], "requested")
        request = json.loads(self.request_path.read_text(encoding="utf-8"))
        self.assertEqual(request["source"], "ops-self-healing-agent")

    def test_reconnect_is_cooldown_and_count_limited(self):
        agent = self.agent()
        self.assertEqual(agent.request_pbx_reconnect("first")["status"], "requested")
        self.assertEqual(agent.request_pbx_reconnect("too soon")["status"], "cooldown")
        self.now += 61
        self.assertEqual(agent.request_pbx_reconnect("second")["status"], "requested")
        self.now += 61
        self.assertEqual(agent.request_pbx_reconnect("third")["status"], "blocked")

    def test_reconnect_disabled_by_default(self):
        config = OpsAgentConfig(
            db_path=str(self.db_path),
            reconnect_request_file=str(self.request_path),
            auto_reconnect=False,
        )
        agent = OpsSelfHealingAgent(config, clock=lambda: self.now)
        self.assertEqual(agent.request_pbx_reconnect("not allowed")["status"], "disabled")
        self.assertFalse(self.request_path.exists())

    def test_run_once_is_async_and_does_not_need_pbx(self):
        self.tcp_results[("pbx", 23)] = False
        report = asyncio.run(self.agent().run_once())
        self.assertEqual(report["checks"]["pbx"]["status"], "down")
        self.assertEqual(report["remediation"]["action"]["status"], "requested")


if __name__ == "__main__":
    unittest.main(verbosity=2)

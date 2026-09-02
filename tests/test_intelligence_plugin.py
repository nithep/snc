#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contract tests for the SNC Intelligence optional plugin boundary."""

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class IntelligencePluginContractTest(unittest.TestCase):
    def run_import_probe(self, enabled: bool, script: str):
        env = os.environ.copy()
        env["SNC_INTELLIGENCE_ENABLED"] = "true" if enabled else "false"
        env["SNC_SQLITE_PATH"] = str(ROOT / "tests" / ".plugin-contract-events.db")
        env["PYTHONPATH"] = str(ROOT / "api")
        return subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            try:
                (ROOT / "tests" / (".plugin-contract-events.db" + suffix)).unlink()
            except FileNotFoundError:
                pass

    def test_disabled_core_does_not_import_plugin(self):
        script = r'''
import importlib
import sys

real_import = importlib.import_module
def guarded_import(name, package=None):
    if name.startswith("services.intelligence"):
        raise AssertionError("optional Intelligence plugin was imported while disabled")
    return real_import(name, package)
importlib.import_module = guarded_import

import server
assert not any(route.path.startswith("/api/intelligence") for route in server.app.routes)
assert server.SNC_INTELLIGENCE_ENABLED is False
'''
        result = self.run_import_probe(False, script)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_enabled_mode_dynamically_registers_plugin_routes(self):
        script = r'''
import server
paths = {route.path for route in server.app.routes}
assert "/api/intelligence/clinical" in paths
assert "/api/intelligence/handover" in paths
assert server.SNC_INTELLIGENCE_ENABLED is True
'''
        result = self.run_import_probe(True, script)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)

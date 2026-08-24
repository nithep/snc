# -*- coding: utf-8 -*-
"""Unit tests สำหรับ SMDR parser ใน snc_pbx_listener.py"""
import os
import tempfile
import time

# ควบคุม room map ด้วย fixture — ไม่พึ่ง pbx/room_map.json จริง (ผู้ใช้แก้ได้ตลอดเวลา)
# ตั้ง env ก่อน import listener เพราะ ROOM_MAP_PATH ถูกคำนวณตอน import
_TEST_MAP = os.path.join(tempfile.gettempdir(), "snc_test_room_map.json")
with open(_TEST_MAP, "w", encoding="utf-8") as _f:
    _f.write('{"501": "9901"}')
os.environ["SNC_ROOM_MAP"] = _TEST_MAP

import unittest
from snc_pbx_listener import PhonikSNCListener, PhonikTelnetSession


class TestSMDRParser(unittest.TestCase):
    def setUp(self):
        self.listener = PhonikSNCListener()

    def test_standard_smdx_format(self):
        line = "==SMDX2005=03/08/26 18:59 401 e.400 EC 0:00'09 0 #1"
        event = self.listener.parse_smdr_line(line)
        self.assertIsNotNone(event)
        self.assertEqual(event["extension"]["roomId"], "0401")
        self.assertEqual(event["payload"][0]["contentString"], "CALL_BEDSIDE")

    def test_dash_prefix_smdx_format(self):
        line = "--SMDX2027=10/08/26 21:04 401 e.401 EC 0:00'05 0 #1"
        event = self.listener.parse_smdr_line(line)
        self.assertIsNotNone(event)
        self.assertEqual(event["extension"]["roomId"], "0401")
        self.assertEqual(event["payload"][0]["contentString"], "CALL_BEDSIDE")

    def test_no_prefix_smdr_format(self):
        """Test SMDR records without ==SMDX prefix (actual PBX format)"""
        test_cases = [
            ("10/08/26 14:54 401 e.400 EC 0:00'05 0 #1", "0401", "CALL_BEDSIDE"),
            ("10/08/26 17:21 401 e.400 EC 0:00'10 0 #1", "0401", "CALL_BEDSIDE"),
            ("10/08/26 21:04 401 e.400 EC 0:00'08 0 #1", "0401", "CALL_BEDSIDE"),
            ("10/08/26 22:15 401 e.400 EC 0:00'04 0 #1", "0401", "CALL_BEDSIDE"),
        ]
        
        for line, expected_room, expected_event in test_cases:
            with self.subTest(line=line):
                self.listener.recent_call_memory.clear()  # ล้างหน่วยความจำเพื่อให้ทดสอบแยกขาดกันอย่างสะอาด
                event = self.listener.parse_smdr_line(line)
                self.assertIsNotNone(event, f"Failed to parse: {line}")
                self.assertEqual(event["extension"]["roomId"], expected_room)
                self.assertEqual(event["payload"][0]["contentString"], expected_event)

    def test_nurse_talking_event(self):
        line = "==SMDX2010=03/08/26 19:00 401 onM -9"
        event = self.listener.parse_smdr_line(line)
        self.assertIsNotNone(event)
        self.assertEqual(event["payload"][0]["contentString"], "NURSE_TALKING")

    def test_call_cleared_event(self):
        line = "==SMDX2012=03/08/26 19:01 401 offM =0"
        event = self.listener.parse_smdr_line(line)
        self.assertIsNotNone(event)
        self.assertEqual(event["payload"][0]["contentString"], "CALL_CLEARED")

    def test_fallback_e_dot_pattern(self):
        line = "some garbage e.402 trailing"
        event = self.listener.parse_smdr_line(line)
        self.assertIsNotNone(event)
        self.assertEqual(event["extension"]["roomId"], "0402")

    def test_room_map_translation(self):
        """Port→Room mapping: 501 → 9901 ตาม fixture map"""
        line = "==SMDX2005=03/08/26 18:59 501 e.500 EC 0:00'09 0 #1"
        event = self.listener.parse_smdr_line(line)
        self.assertIsNotNone(event)
        self.assertEqual(event["extension"]["roomId"], "9901")

    def test_room_map_hot_reload(self):
        """แก้ room_map.json แล้วมีผลทันที ไม่ต้องรีสตาร์ท listener"""
        with open(_TEST_MAP, "w", encoding="utf-8") as f:
            f.write('{"501": "9902"}')
        os.utime(_TEST_MAP, (time.time() + 2, time.time() + 2))  # บังคับ mtime ใหม่
        line = "==SMDX2005=03/08/26 18:59 501 e.500 EC 0:00'09 0 #1"
        event = self.listener.parse_smdr_line(line)
        self.assertEqual(event["extension"]["roomId"], "9902")
        with open(_TEST_MAP, "w", encoding="utf-8") as f:
            f.write('{"501": "9901"}')  # เคลียร์กลับสำหรับ test อื่น

    def test_banner_line_returns_none(self):
        self.assertIsNone(self.listener.parse_smdr_line("Phonik PABX Telnet system"))
        self.assertIsNone(self.listener.parse_smdr_line(".."))

    def test_temporal_bathroom_emergency(self):
        import time
        self.listener.recent_call_memory["401"] = time.time() - 30  # เปลี่ยนจาก "400" เป็น "401" ให้ตรงกับสายใน 401 ต้นทาง
        line2 = "==SMDX2006=03/08/26 18:59 401 e.400 EC"
        event2 = self.listener.parse_smdr_line(line2)
        self.assertEqual(event2["payload"][0]["contentString"], "CALL_BATHROOM_EMERGENCY")


class TestRDSSParser(unittest.TestCase):
    """Tests สำหรับ RDSS Real-time channel (สถานะห้องจาก ..EVNT=ALL dump)"""

    def setUp(self):
        import asyncio
        self.listener = PhonikSNCListener()
        self.sent = []

        async def fake_send(event):
            self.sent.append(event)

        self.listener.send_event_to_backend = fake_send

    def _flush(self):
        import asyncio
        asyncio.run(self.listener._flush_rdss_transitions())

    def test_rdss_room_active_fires_bedside(self):
        self.listener.rdss_states["0401"] = 0
        self.listener._queue_rdss_state("==RDSS401=1")
        self._flush()
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0]["payload"][0]["contentString"], "CALL_BEDSIDE")
        self.assertEqual(self.sent[0]["extension"]["roomId"], "0401")

    def test_rdss_room_cleared_fires_cleared(self):
        self.listener.rdss_states["0401"] = 1
        self.listener._queue_rdss_state("==RDSS401=0")
        self._flush()
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0]["payload"][0]["contentString"], "CALL_CLEARED")

    def test_rdss_station_400_with_peer_maps_to_room(self):
        self.listener.rdss_states["0401"] = 0
        self.listener._queue_rdss_state("==RDSS400=4>401")
        self._flush()
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0]["extension"]["roomId"], "0401")
        self.assertEqual(self.sent[0]["payload"][0]["contentString"], "CALL_BEDSIDE")

    def test_rdss_no_duplicate_on_same_state(self):
        self.listener.rdss_states["0401"] = 1
        self.listener._queue_rdss_state("==RDSS401=1")
        self._flush()
        self.assertEqual(len(self.sent), 0)  # สถานะไม่เปลี่ยน -> ไม่ยิงซ้ำ

    def test_rdss_last_wins_within_dump(self):
        """ภายในรอบ dump เดียว ใช้ค่าสุดท้ายของห้อง (กัน false alarm จากประวัติ replay)"""
        self.listener.rdss_states["0401"] = 0
        self.listener._queue_rdss_state("==RDSS401=1")
        self.listener._queue_rdss_state("==RDSS401=2")
        self.listener._queue_rdss_state("==RDSS401=0")  # จบด้วยว่าง -> ไม่ควรยิง event
        self._flush()
        self.assertEqual(len(self.sent), 0)
        self.assertEqual(self.listener.rdss_states["0401"], 0)

    def test_rdss_ignores_non_nurse_groups(self):
        self.listener._queue_rdss_state("==RDSS101=1")   # ห้องโรงแรม (1xx) -> ข้าม
        self.listener._queue_rdss_state("==PWER101=off")  # ไม่ใช่ RDSS -> ข้าม
        self.listener._queue_rdss_state("==RDSS=0")       # ไม่มีเลขสถานี -> ข้าม
        self._flush()
        self.assertEqual(len(self.sent), 0)
        self.assertEqual(self.listener._rdss_pending, {})


class TestBannerDetection(unittest.TestCase):
    def test_is_banner(self):
        self.assertTrue(PhonikTelnetSession.is_banner_line("Phonik PABX Telnet system"))
        self.assertTrue(PhonikTelnetSession.is_banner_line(".."))
        self.assertFalse(PhonikTelnetSession.is_banner_line("==SMDX2005=03/08/26 18:59 401 e.400"))


class TestWatchdog(unittest.TestCase):
    """Tests สำหรับ Self-Healing Watchdog (session เงียบเกินเกณฑ์ -> Force reconnect)"""

    class FakeWriter:
        """จำลอง asyncio StreamWriter อย่างง่าย"""
        def __init__(self):
            self._closed = False
        def is_closing(self):
            return self._closed
        def close(self):
            self._closed = True
        async def wait_closed(self):
            return None

    def setUp(self):
        import snc_pbx_listener as mod
        self.mod = mod
        # เก็บค่าเดิมไว้คืนใน tearDown (กัน global leakage ไปยังเทสต์อื่น)
        self._orig_timeout = mod.WATCHDOG_SILENCE_TIMEOUT
        self._orig_interval = mod.WATCHDOG_CHECK_INTERVAL
        self.listener = mod.PhonikSNCListener()
        self.listener.is_running = True  # จำลองว่าระบบกำลังรัน

    def tearDown(self):
        # คืนค่า module globals ตามเดิม
        self.mod.WATCHDOG_SILENCE_TIMEOUT = self._orig_timeout
        self.mod.WATCHDOG_CHECK_INTERVAL = self._orig_interval

    def test_watchdog_force_reconnect_when_silent(self):
        """session เงียบเกินเกณฑ์ -> ต้องปิด connection ให้ reconnect"""
        import asyncio, time
        self.mod.WATCHDOG_SILENCE_TIMEOUT = 0.05
        self.mod.WATCHDOG_CHECK_INTERVAL = 0.02
        writer = self.FakeWriter()
        self.listener._last_data_time = time.time() - 10  # เงียบมา 10 วิ (เกินเกณฑ์)
        asyncio.run(self.listener._watchdog_loop(writer))
        self.assertTrue(writer.is_closing(), "Watchdog ต้องปิด connection เมื่อ session เงียบเกินเกณฑ์")
        self.assertTrue(self.listener._watchdog_triggered, "ต้องตั้ง flag _watchdog_triggered ก่อนปิด connection")

    def test_watchdog_keeps_connection_when_active(self):
        """ยังมีข้อมูลไหลเข้าต่อเนื่อง -> ต้องไม่ปิด connection"""
        import asyncio, time
        self.mod.WATCHDOG_SILENCE_TIMEOUT = 0.05
        self.mod.WATCHDOG_CHECK_INTERVAL = 0.02
        writer = self.FakeWriter()
        self.listener._last_data_time = time.time()  # เพิ่งมีข้อมูล

        async def run():
            task = asyncio.create_task(self.listener._watchdog_loop(writer))
            # จำลองข้อมูลไหลต่อเนื่อง (อัปเดต timestamp ทุก 10ms)
            for _ in range(15):
                await asyncio.sleep(0.01)
                self.listener._last_data_time = time.time()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        asyncio.run(run())
        self.assertFalse(writer.is_closing(), "Watchdog ต้องไม่ปิด connection เมื่อยังมีข้อมูลไหล")

    def test_watchdog_stops_when_not_running(self):
        """ถ้าระบบหยุด (is_running=False) -> loop ต้องจบทันทีโดยไม่แตะ connection"""
        import asyncio, time
        self.listener.is_running = False
        self.mod.WATCHDOG_SILENCE_TIMEOUT = 0.05
        self.mod.WATCHDOG_CHECK_INTERVAL = 0.02
        writer = self.FakeWriter()
        self.listener._last_data_time = time.time() - 10  # เงียบนาน แต่ระบบหยุดแล้ว
        asyncio.run(self.listener._watchdog_loop(writer))
        self.assertFalse(writer.is_closing(), "Watchdog ต้องไม่ปิด connection เมื่อระบบหยุดทำงานแล้ว")


class TestProxyEmulation(unittest.TestCase):
    """Tests สำหรับ TCP Proxy Emulation (Room Manager / PC Operator เชื่อม 2323)
    — ลอกแบบ response จริงของตู้ DX-COMPACT จาก probe หน้างาน (2026-08-12)"""

    def setUp(self):
        self.listener = PhonikSNCListener()

    def test_rdss_all_matches_real_pbx_format(self):
        """..RDSS=all ต้องตอบตามรูปแบบจริง: 401-409 → 6×==RDSS=0 → ==RDSS400=0 → ==ACKW"""
        resp = self.listener._build_proxy_response("..RDSS=all")
        self.assertIsNotNone(resp)
        lines = resp.strip().split("\r\n")
        expected = [f"==RDSS{i}=0" for i in range(401, 410)] + ["==RDSS=0"] * 6 + ["==RDSS400=0", "==ACKW"]
        self.assertEqual(lines, expected, "รูปแบบ RDSS=all ต้องตรงกับตู้จริง")

    def test_rdss_all_uses_live_state(self):
        """RDSS=all ต้องใช้สถานะสดจาก rdss_states (ให้ Room Manager เห็นห้องที่เรียกอยู่)"""
        self.listener.rdss_states["0401"] = 1
        self.listener.rdss_states["0405"] = 4
        resp = self.listener._build_proxy_response("..RDSS=all")
        self.assertIn("==RDSS401=1", resp)
        self.assertIn("==RDSS405=4", resp)
        self.assertIn("==RDSS402=0", resp)

    def test_handshake_commands(self):
        self.assertEqual(self.listener._build_proxy_response("..tcmd=1"), "==tcmd=1\r\n")
        self.assertEqual(self.listener._build_proxy_response("..tcmd=20"), "==tcmd=1\r\n")
        self.assertEqual(self.listener._build_proxy_response("..VERS="), "==VERS=DX-COMPACT V5.4r1 (V5.1r0)\r\n")
        self.assertEqual(self.listener._build_proxy_response("..PASS=1234"), "==ACKW\r\n")
        self.assertEqual(self.listener._build_proxy_response("..EVNT=ALL"), "==EVNT=END\r\n")

    def test_info_commands_match_real_format(self):
        """name/date/time/ssid ต้องเป็น lowercase ตามตู้จริง"""
        resp_date = self.listener._build_proxy_response("..date=")
        self.assertTrue(resp_date.startswith("==date="), f"ต้องเป็น ==date= ได้ {resp_date}")
        self.assertTrue(resp_date.endswith("\r\n"))
        resp_time = self.listener._build_proxy_response("..time=")
        self.assertTrue(resp_time.startswith("==time="))
        self.assertEqual(self.listener._build_proxy_response("..name="), "==name=   \r\n")
        self.assertEqual(self.listener._build_proxy_response("..ssid="), "==ssid=136375\r\n")

    def test_memory_dump_commands(self):
        """data6/data0 ต้องตอบ format บล็อกหน่วยความจำ (ไม่ใช่ ACKW เปล่า)"""
        resp6 = self.listener._build_proxy_response("..data6=")
        self.assertTrue(resp6.startswith("==data6=\r\n==:40000070:"))
        resp0 = self.listener._build_proxy_response("..data0=")
        self.assertTrue(resp0.startswith("==data0=\r\n==:81028000:"))

    def test_prompt_commands(self):
        """prompt .. / . / ..= → ตอบ .."""
        self.assertEqual(self.listener._build_proxy_response(".."), "..\r\n")
        self.assertEqual(self.listener._build_proxy_response("."), "..\r\n")
        self.assertEqual(self.listener._build_proxy_response("..="), "..\r\n")

    def test_prefix_matching_no_false_positive(self):
        """prefix matching ต้องไม่ให้ ..update= ไปโดน DATE หรือ ..rename= ไปโดน NAME="""
        self.assertEqual(self.listener._build_proxy_response("..update="), "==ACKW\r\n")
        self.assertEqual(self.listener._build_proxy_response("..rename="), "==ACKW\r\n")

    def test_unknown_command_gets_ackw(self):
        """คำสั่ง CCH2 ที่ไม่รู้จัก → ตอบ ACKW ปลอดภัย กันโปรแกรมค้าง"""
        self.assertEqual(self.listener._build_proxy_response("..somecmd="), "==ACKW\r\n")
        self.assertIsNone(self.listener._build_proxy_response("hello world"))


if __name__ == "__main__":
    unittest.main()

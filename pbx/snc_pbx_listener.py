# -*- coding: utf-8 -*-
"""
Smart Nurse Call — Phonik PBX SMDR Telnet Listener

เชื่อมต่อตู้ Phonik PBX ผ่าน Telnet (port 23), ทำ Authentication handshake,
Subscribe SMDR event stream แล้วส่งต่อไปยัง SNC Backend API
"""
import asyncio
import os
import re
import pathlib
import logging
import time
import aiohttp
from datetime import datetime

# โหลด .env (ไม่มี python-dotenv) — PBX_PASS / SNC_API_KEY มาจากไฟล์ ไม่ฝังในโค้ด
_env_file = pathlib.Path(__file__).resolve().parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Phonik PBX Telnet Configuration (override ได้ผ่าน environment variables)
PBX_IP = os.getenv("PBX_IP", "192.168.1.91")
PBX_PORT = int(os.getenv("PBX_PORT", "23"))
PBX_PASS = os.getenv("PBX_PASS", "1234")

# Backend API Configuration
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")
BACKEND_API_KEY = os.getenv("SNC_API_KEY", "")
# SNC_API_KEY ต้องตรงกับค่าใน backend/.env (server.py ตรวจ X-API-Key ที่ /api/events/trigger)

# รองรับทั้ง ==SMDX และ --SMDX (PC Operator บางเวอร์ชันแสดง -- แต่ wire format มักเป็น ==)
# Example with prefix: ==SMDX2005=03/08/26 18:59 401 e.400 EC 0:00'09 0 #1
# Example without prefix: 10/08/26 14:54 401 e.400 EC 0:00'05 0 #1
SMDR_PATTERN = re.compile(
    r"(?:[=\\-]{2}SMDX\s*\d*\s*=?\s*)?\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}\s+(\d+)\s+(\S+)"
)

# ─── ช่องทาง Real-time (RDSS — Room Display Status) ───
# ตู้ Phonik ไม่ Push ข้อมูลสด แต่ Buffer สถานะห้องไว้ และ Dump ออกมาเมื่อถูกขอ (..EVNT=ALL)
# รูปแบบ: ==RDSS<สถานี>=<สถานะ>  หรือ  ==RDSS<สถานี>=<สถานะ>><ปลายทาง>  (เช่น ==RDSS400=4>401)
#   - กลุ่ม 4xx = Nurse Call (401+ = ห้องผู้ป่วย, 400 = สถานีกลางที่ชี้ไปยังห้องผู้ป่วย)
#   - สถานะ 0 = ว่าง / ไม่มีการเรียก  |  !=0 = กำลังเรียก/คุยอยู่
RDSS_PATTERN = re.compile(r"==RDSS(\d{3,4})=(\d+)(?:>(\d{3,4}))?")
# ความถี่ Poll สถานะห้อง (วินาที) — ยิ่งถี่ยิ่งใกล้ real-time (ค่าเริ่มต้น 3 วิ)
RDSS_POLL_INTERVAL = float(os.getenv("RDSS_POLL_INTERVAL", "3"))

# ─── Self-Healing Watchdog ───
# ถ้าไม่ได้รับข้อมูลใดๆ จากตู้ PBX เกิน WATCHDOG_SILENCE_TIMEOUT วินาที
# (เช่น session ตาย/ค้างจาก power cycle, ตู้ค้าง, หรือ heartbeat task หลุดเงียบ)
# → ปิด connection เอง เพื่อให้ main loop ตรวจจับและ reconnect ใหม่โดยอัตโนมัติ
WATCHDOG_SILENCE_TIMEOUT = float(os.getenv("WATCHDOG_SILENCE_TIMEOUT", "60"))
WATCHDOG_CHECK_INTERVAL = float(os.getenv("WATCHDOG_CHECK_INTERVAL", "10"))

BANNER_MARKERS = ("Phonik PABX Telnet system", "Phonik PABX", "Telnet system")


class PhonikTelnetSession:
    """จัดการ handshake และ subscription กับตู้ Phonik PBX"""

    def __init__(self, password: str = PBX_PASS):
        self.password = password

    async def send_command(self, writer, reader, command: str, timeout: float = 5.0) -> str:
        """ส่งคำสั่ง CCH2 แล้วอ่าน response บรรทัดแรก"""
        if not command.endswith("\r\n"):
            command = command + "\r\n"
        writer.write(command.encode("ascii"))
        await writer.drain()
        try:
            line_bytes = await asyncio.wait_for(reader.readline(), timeout=timeout)
            return line_bytes.decode("utf-8", errors="ignore").strip()
        except asyncio.TimeoutError:
            logging.warning(f"Timeout waiting for PBX response to: {command.strip()}")
            return ""

    async def authenticate(self, writer, reader) -> bool:
        """
        ลำดับ handshake ตามมาตรฐาน Phonik (Reverse-engineered จาก PC Operator):
        1. ..tcmd=1  — เข้าโหมด terminal command
        2. ..VERS=   — ping protocol (optional)
        3. ..PASS=   — ยืนยันรหัสผ่าน
        4. ..EVNT=ALL — subscribe real-time SMDR event stream
        """
        steps = [
            ("..tcmd=1", "Terminal command mode"),
            ("..VERS=", "Protocol version ping"),
            (f"..PASS={self.password}", "Authentication"),
            ("..EVNT=ALL", "SMDR event subscription"),
        ]

        for cmd, label in steps:
            resp = await self.send_command(writer, reader, cmd)
            logging.info(f"PBX handshake [{label}]: cmd={cmd.strip()} resp={resp[:120]}")
            if cmd.startswith("..PASS=") and resp and "NACK" in resp.upper():
                logging.error("PBX authentication failed (NACK) — ตรวจสอบ PBX_PASS")
                return False

        logging.info("PBX authentication & SMDR subscription handshake completed")
        return True

    @staticmethod
    def is_banner_line(line: str) -> bool:
        stripped = line.strip()
        if not stripped or stripped == "..":
            return True
        return any(marker in stripped for marker in BANNER_MARKERS)


class PhonikSNCListener:
    def __init__(self, host=PBX_IP, port=PBX_PORT, backend_url=BACKEND_API_URL, pbx_pass=PBX_PASS):
        self.host = host
        self.port = port
        self.backend_url = backend_url
        self.pbx_session = PhonikTelnetSession(password=pbx_pass)
        self.is_running = False
        self.recent_call_memory = {}
        self.http_session = None
        self._read_buffer = b""
        self.proxy_port = int(os.getenv("PROXY_PORT", "2323"))
        self.connected_clients = set()
        self.proxy_server = None
        # สถานะ RDSS สำหรับตรวจจับ transition (0->active / active->0)
        self.rdss_states = {}          # ห้อง -> สถานะล่าสุดที่รู้จัก
        self._rdss_pending = {}        # สถานะค้างภายในรอบ dump เดียว (last-wins)
        self._rdss_pending_since = 0.0
        # Watchdog: timestamp ล่าสุดที่ได้รับข้อมูลจากตู้ (ใช้ตรวจ session เงียบ)
        self._last_data_time = 0.0
        # Flag: watchdog เป็นคนตัด connection (เพื่อ log/backoff ที่แม่นยำ)
        self._watchdog_triggered = False

    def parse_smdr_line(self, line: str):
        """Parse raw SMDR line into structured FHIR-like JSON event."""
        line = line.strip()
        if not line or PhonikTelnetSession.is_banner_line(line):
            return None

        match = SMDR_PATTERN.search(line)
        if not match:
            # Fallback: try to extract room ID from "e.XXX" pattern even if regex fails
            if "e." in line:
                logging.debug(f"SMDR regex failed but 'e.' found, using fallback: {line[:100]}")
                room_match = re.search(r"e\.(\d+)", line)
                if room_match:
                    room_id = room_match.group(1)
                    logging.info(f"Fallback parsing successful: Room {room_id} from line: {line[:80]}")
                    return self._create_event_payload(room_id, "CALL_BEDSIDE", line)
            else:
                logging.debug(f"SMDR line ignored (no match): {line[:100]}")
            return None

        station_ext = match.group(1)
        event_code = match.group(2)

        if event_code.startswith("e."):
            room_id = station_ext
            now_ts = datetime.now().timestamp()
            last_call_time = self.recent_call_memory.get(room_id, 0)
            time_diff = now_ts - last_call_time
            self.recent_call_memory[room_id] = now_ts

            if 0 < time_diff <= 90:
                event_type = "CALL_BATHROOM_EMERGENCY"
                logging.warning(
                    f"Temporal Pattern Detected: Room {room_id} repeating call ({time_diff:.1f}s) "
                    f"-> Re-classified to BATHROOM EMERGENCY!"
                )
            else:
                event_type = "CALL_BEDSIDE"

        elif "onM" in event_code or "onto" in event_code:
            room_id = station_ext
            event_type = "NURSE_TALKING"
        elif "offM" in event_code or "offx" in event_code:
            room_id = station_ext
            event_type = "CALL_CLEARED"
            if room_id in self.recent_call_memory:
                del self.recent_call_memory[room_id]
        else:
            room_id = station_ext
            event_type = "INFO_UPDATE"

        return self._create_event_payload(room_id, event_type, line)

    def _create_event_payload(self, room_id: str, event_type: str, raw_line: str):
        formatted_room = room_id.zfill(4)
        now_iso = datetime.now().isoformat()
        is_active_call = event_type in ["CALL_BEDSIDE", "CALL_BATHROOM_EMERGENCY", "CALL_TRIGGERED"]
        is_bathroom = event_type == "CALL_BATHROOM_EMERGENCY"

        return {
            "resourceType": "CommunicationRequest",
            "id": f"snc-event-{formatted_room}-{int(datetime.now().timestamp())}",
            "status": "active" if is_active_call else "completed",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/communication-category",
                            "code": "alert",
                            "display": "Bathroom Emergency Pull" if is_bathroom else "Bedside Nurse Call",
                        }
                    ]
                }
            ],
            "priority": "stat" if is_bathroom else ("urgent" if is_active_call else "routine"),
            "occurrenceDateTimeField": now_iso,
            "payload": [{"contentString": event_type}],
            "extension": {
                "roomId": formatted_room,
                "originDevice": "BATHROOM_PULL_SWITCH" if is_bathroom else "BEDSIDE_STA",
                "rawSmdrLog": raw_line,
                "timestamp": now_iso,
            },
        }

    # ─── RDSS Real-time Channel Helpers ───
    def _queue_rdss_state(self, line: str):
        """บันทึกสถานะ RDSS ล่าสุดของห้อง (last-wins ภายในรอบ EVNT=ALL dump)"""
        m = RDSS_PATTERN.search(line)
        if not m:
            return
        station = m.group(1)
        state = int(m.group(2))
        peer = m.group(3)

        # แมปไปห้องผู้ป่วย: 401+ คือห้อง / 400 (สถานีกลาง) ชี้ไปยัง peer
        if station == "400" and peer:
            room = peer
        elif station.isdigit() and int(station) >= 401:
            room = station
        else:
            return  # กลุ่ม extension อื่น (เช่น 1xx โรงแรม) ไม่ใช่ nurse call

        room_id = room.zfill(4)
        if not self._rdss_pending:
            self._rdss_pending_since = time.time()
        self._rdss_pending[room_id] = state

    async def _flush_rdss_transitions(self):
        """เมื่อจบ dump (EVNT=END) เปรียบเทียบกับสถานะเดิม → ยิง event เฉพาะ transition"""
        for room_id, new_state in list(self._rdss_pending.items()):
            prev_state = self.rdss_states.get(room_id, 0)
            if new_state == prev_state:
                continue
            self.rdss_states[room_id] = new_state

            event = None
            if new_state != 0 and prev_state == 0:
                event = self._create_event_payload(room_id, "CALL_BEDSIDE", f"==RDSS{room_id}={new_state}")
            elif new_state == 0 and prev_state != 0:
                event = self._create_event_payload(room_id, "CALL_CLEARED", f"==RDSS{room_id}=0")

            if event:
                logging.info(
                    f"RDSS State Change: Room {room_id} {prev_state} -> {new_state} "
                    f"=> {event['payload'][0]['contentString']}"
                )
                await self.send_event_to_backend(event)
        self._rdss_pending.clear()

    def _consume_binary_packets(self):
        """ข้าม Phonik binary keep-alive frames ที่ขึ้นต้นด้วย 0x5A"""
        while len(self._read_buffer) >= 2 and self._read_buffer[0] == 0x5A:
            packet_len = 1 + self._read_buffer[1]
            if len(self._read_buffer) < packet_len:
                break
            self._read_buffer = self._read_buffer[packet_len:]

    def _extract_lines(self):
        """แยกบรรทัด ASCII จาก buffer (รองรับ \r\n และ \n)"""
        self._consume_binary_packets()
        lines = []

        while True:
            self._consume_binary_packets()
            idx = self._read_buffer.find(b"\n")
            if idx == -1:
                break
            raw_line = self._read_buffer[:idx]
            self._read_buffer = self._read_buffer[idx + 1:]
            line = raw_line.decode("utf-8", errors="ignore").rstrip("\r")
            if line:
                lines.append(line)

        return lines

    async def init_http_session(self):
        if self.http_session is None or self.http_session.closed:
            self.http_session = aiohttp.ClientSession()
            logging.info("HTTP session initialized for Backend API communication")

    async def send_event_to_backend(self, event_data: dict):
        try:
            await self.init_http_session()
            url = f"{self.backend_url}/api/events/trigger"
            payload = {
                "room_id": event_data["extension"]["roomId"],
                "event_type": event_data["payload"][0]["contentString"],
            }

            logging.info(f"Attempting to send event to backend: {payload}")  # Debug log
            
            async with self.http_session.post(url, json=payload, headers={"X-API-Key": BACKEND_API_KEY}) as response:
                if response.status == 200:
                    result = await response.json()
                    logging.info(
                        f"✅ Event sent successfully: Room {payload['room_id']} - {payload['event_type']} "
                        f"(ID: {result.get('event', {}).get('id', 'unknown')})"
                    )
                else:
                    body = await response.text()
                    logging.error(f"❌ Failed to send event. Status: {response.status} Body: {body[:200]}")

        except Exception as e:
            logging.error(f"❌ Error sending event to Backend: {e}")
            import traceback
            logging.error(traceback.format_exc())

    async def _process_line(self, raw_line: str):
        if PhonikTelnetSession.is_banner_line(raw_line):
            logging.debug(f"PBX banner/prompt ignored: {raw_line.strip()[:80]}")
            return

        line = raw_line.strip()

        # จบรอบ EVNT=ALL dump → flush สถานะ RDSS ที่ค้างอยู่ (ยิง event จาก transition)
        if line == "==EVNT=END":
            await self._flush_rdss_transitions()
            return

        # ช่องทาง Real-time: RDSS (Room Display Status) — buffer แล้ว flush เมื่อจบรอบ
        if RDSS_PATTERN.search(line):
            self._queue_rdss_state(line)
            return

        # Log all incoming lines for debugging
        logging.debug(f"Processing line: {raw_line[:150]}")
        
        if "SMDX" in raw_line or "e." in raw_line:
            logging.info(f"PBX SMDR received: {raw_line.strip()[:500]}")

        event_data = self.parse_smdr_line(raw_line)
        if event_data:
            logging.info(
                f"SNC Event Detected: Room {event_data['extension']['roomId']} "
                f"-> {event_data['payload'][0]['contentString']}"
            )
            await self.send_event_to_backend(event_data)
        else:
            # Log when parsing fails (for debugging)
            if "e." in raw_line and not PhonikTelnetSession.is_banner_line(raw_line):
                logging.warning(f"Line contains 'e.' but failed to parse: {raw_line[:150]}")

    def _build_proxy_response(self, raw_cmd: str):
        """
        สร้าง response จำลอง (Emulation) ให้โปรแกรม Phonik บน PC (Room Manager / System Monitor)
        ที่เชื่อมผ่าน TCP Proxy พอร์ต 2323 — ลอกแบบ response จริงของตู้ DX-COMPACT V5.4r1 (V5.1r0)
        ที่จับจาก probe หน้างาน (2026-08-12) เพื่อให้โปรแกรม PC ยอมรับการเชื่อมต่อและแสดงผลได้

        คืนค่า response string (ปิดท้าย \r\n) หรือ None ถ้าไม่รู้จักคำสั่ง
        """
        # ใช้ prefix matching (ไม่ใช่ substring) กัน false-positive เช่น ..update= ไปโดน DATE
        cmd_upper = raw_cmd.upper()
        if cmd_upper.startswith("..TCMD"):
            return "==tcmd=1\r\n"
        if cmd_upper.startswith("..VERS") or cmd_upper.startswith("VERS"):
            return "==VERS=DX-COMPACT V5.4r1 (V5.1r0)\r\n"
        if cmd_upper.startswith("..PASS"):
            return "==ACKW\r\n"
        if cmd_upper.startswith("..EVNT"):
            return "==EVNT=END\r\n"
        if cmd_upper.startswith("..RDSS"):
            # ลอกแบบ response จริงของตู้ (probe 21:09): ==RDSS401..409 → 6× ==RDSS=0 (สถานีว่าง)
            # → ==RDSS400=0 → ==ACKW  — ใช้สถานะสดจาก self.rdss_states (RDSS poll ทุก 3 วิ)
            resp_lines = []
            for station in list(range(401, 410)):
                state = self.rdss_states.get(str(station).zfill(4), 0)
                resp_lines.append(f"==RDSS{station}={state}")
            for _ in range(6):
                resp_lines.append("==RDSS=0")
            resp_lines.append("==RDSS400=0")
            resp_lines.append("==ACKW")
            return "\r\n".join(resp_lines) + "\r\n"
        if raw_cmd.startswith("..name="):
            return "==name=   \r\n"
        if raw_cmd.startswith("..date="):
            now = datetime.now()
            return f"==date={now.strftime('%y/%m/%d')}-{now.isoweekday()}\r\n"
        if raw_cmd.startswith("..time="):
            now = datetime.now()
            return f"==time={now.strftime('%H:%M:%S')}\r\n"
        if raw_cmd.startswith("..ssid="):
            # หมายเลขเครื่องจริงของตู้ DX-COMPACT ตัวนี้ (จับจาก probe หน้างาน)
            return "==ssid=136375\r\n"
        if raw_cmd.startswith("..data6="):
            # บล็อกหน่วยความจำตัวอย่าง (captured จากตู้จริง) — ถ้าโปรแกรม PC อ่าน address เพิ่มเติม
            # ให้ capture เพิ่มเติมแล้วขยายบล็อกนี้ (ดู docs/wiki/PBX_RDSS_REALTIME_CHANNEL.md)
            return ("==data6=\r\n"
                    "==:40000070:61,61,16,00;00,00,00,00;00,00,00,00;00,00,00,00\r\n"
                    "==:40000080:00,00,00,00;00,00,00,00;00,00,00,00;00,00,00,00\r\n")
        if raw_cmd.startswith("..data0="):
            return ("==data0=\r\n"
                    "==:81028000:00,00,03,D8;3D,00,03,D0;84,BA,04,80;7D,58,10,54\r\n"
                    "==:81028010:7D,58,10,54;82,D3,41,52;73,DC,A7,12;F7,7B,26,61\r\n")
        if raw_cmd in ("..", ".", "..="):
            return "..\r\n"
        if raw_cmd.startswith(".."):
            # คำสั่ง CCH2 อื่นที่ยังไม่รู้จัก → ตอบ ACKW ปลอดภัย (กันโปรแกรมค้าง)
            return "==ACKW\r\n"
        return None

    async def handle_proxy_client(self, reader, writer):
        """จัดการการเชื่อมต่อจาก Client ภายนอก (เช่น Phonik Room Manager/System Monitor) ที่ต่อพอร์ต 2323"""
        client_address = writer.get_extra_info('peername')
        logging.info(f"🔌 Proxy client connected from: {client_address}")
        self.connected_clients.add(writer)
        
        def strip_telnet_iac(data: bytes) -> str:
            cleaned = bytearray()
            i = 0
            while i < len(data):
                if data[i] == 0xFF:
                    if i + 1 < len(data) and data[i + 1] in (251, 252, 253, 254):
                        i += 3
                    else:
                        i += 2
                else:
                    cleaned.append(data[i])
                    i += 1
            return cleaned.decode("utf-8", errors="ignore").strip()

        try:
            # ส่ง banner จำลองตรงตามมาตรฐานตู้สาขา Phonik PABX Telnet system
            writer.write(b"Phonik PABX Telnet system\r\n..\r\n")
            await writer.drain()
            
            client_buffer = b""
            while self.is_running:
                data = await reader.read(1024)
                if not data:
                    break
                
                client_buffer += data
                while b"\n" in client_buffer:
                    line_idx = client_buffer.find(b"\n")
                    raw_cmd_bytes = client_buffer[:line_idx]
                    client_buffer = client_buffer[line_idx + 1:]
                    
                    raw_cmd = strip_telnet_iac(raw_cmd_bytes)
                    if not raw_cmd:
                        continue
                    
                    logging.info(f"📩 Proxy client command received from {client_address}: '{raw_cmd}'")
                    
                    # จำลอง Handshake Emulation + ตอบคำสั่งข้อมูล Room Manager
                    # (ลอกแบบ response จริงของตู้ DX-COMPACT — ดู _build_proxy_response)
                    response = self._build_proxy_response(raw_cmd)
                    
                    if response:
                        logging.info(f"📤 Emulating PBX response to client {client_address}: '{response.strip()}'")
                        writer.write(response.encode("utf-8"))
                        await writer.drain()
                        
        except ConnectionError:
            pass
        except Exception as e:
            logging.debug(f"Proxy client handling exception: {e}")
        finally:
            self.connected_clients.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            logging.info(f"🔌 Proxy client disconnected: {client_address}")

    async def broadcast_to_proxy_clients(self, raw_line: str):
        """กระจายสำเนาข้อมูลดิบ SMDR ออกไปหาทุก Client ที่มาเชื่อมพอร์ต 2323"""
        if not self.connected_clients:
            return
        
        # ปรับปรุงให้แน่ใจว่าปิดท้ายด้วย \r\n
        payload = raw_line.rstrip("\r\n") + "\r\n"
        encoded_payload = payload.encode("utf-8", errors="ignore")
        
        disconnected = []
        for writer in list(self.connected_clients):
            try:
                writer.write(encoded_payload)
                await writer.drain()
            except Exception as e:
                logging.warning(f"Error sending SMDR log to proxy client: {e}")
                disconnected.append(writer)
                
        for writer in disconnected:
            self.connected_clients.discard(writer)

    async def _read_initial_banner(self, reader, timeout: float = 2.0):
        """อ่าน welcome banner ที่ PBX ส่งทันทีหลัง connect"""
        try:
            chunk = await asyncio.wait_for(reader.read(256), timeout=timeout)
            if chunk:
                self._read_buffer += chunk
                for line in self._extract_lines():
                    logging.debug(f"PBX banner: {line.strip()[:120]}")
        except asyncio.TimeoutError:
            pass

    async def _heartbeat_loop(self, writer):
        """ส่งคำสั่ง ping (..VERS=) ไปที่ตู้ PBX ทุก 30 วินาที เพื่อรักษาสายไม่ให้ถูกตัด (Idle Connection Timeout)"""
        logging.info("Heartbeat loop started (30s interval)")
        try:
            while self.is_running and writer and not writer.is_closing():
                await asyncio.sleep(30)
                if self.is_running and writer and not writer.is_closing():
                    logging.debug("Sending heartbeat ping (..VERS=) to PBX")
                    writer.write(b"..VERS=\r\n")
                    await writer.drain()
        except asyncio.CancelledError:
            logging.info("Heartbeat loop cancelled")
        except Exception as e:
            logging.warning(f"Error in heartbeat loop: {e}")
            # ถ้า heartbeat เขียน/ส่งข้อมูลไม่ได้ = สายขาด → ปิด connection
            # ให้ main loop ตรวจจับและ reconnect ใหม่ทันที
            try:
                if writer and not writer.is_closing():
                    writer.close()
            except Exception:
                pass

    async def _rdss_poll_loop(self, writer):
        """
        Poll ..EVNT=ALL ทุก RDSS_POLL_INTERVAL วินาที เพื่อรับสถานะห้อง (RDSS) แบบ near-real-time
        เนื่องจากตู้ Phonik ไม่ Push ข้อมูลสด — มัน Buffer สถานะและ Dump เมื่อถูกขอเท่านั้น
        """
        logging.info(f"RDSS status poll loop started (interval={RDSS_POLL_INTERVAL}s)")
        try:
            while self.is_running and writer and not writer.is_closing():
                await asyncio.sleep(RDSS_POLL_INTERVAL)
                if self.is_running and writer and not writer.is_closing():
                    writer.write(b"..EVNT=ALL\r\n")
                    await writer.drain()
                    # Safety: ถ้า dump ไม่ปิดท้ายด้วย EVNT=END ให้ flush ด้วยเวลา (กันค้าง)
                    if self._rdss_pending and time.time() - self._rdss_pending_since > 5:
                        await self._flush_rdss_transitions()
        except asyncio.CancelledError:
            logging.info("RDSS poll loop cancelled")
        except Exception as e:
            logging.warning(f"Error in RDSS poll loop: {e}")
            # ถ้า poll เขียนไม่ได้ = สายขาด → ปิด connection ให้ reconnect ใหม่
            try:
                if writer and not writer.is_closing():
                    writer.close()
            except Exception:
                pass

    async def _watchdog_loop(self, writer):
        """
        Self-Healing Watchdog: ตรวจว่ายังได้รับข้อมูลจากตู้ PBX อยู่หรือไม่

        ถ้า session เงียบเกิน WATCHDOG_SILENCE_TIMEOUT วินาที (ตู้ค้าง / session ตายครึ่งเดียว
        / heartbeat task หลุดเงียบ) → ปิด connection เอง เพื่อให้ main loop ตรวจจับ
        และ reconnect ใหม่ทันที — กันเหตุการณ์ค้างยาวนานแบบ 18:39-18:55 ที่พบหน้างาน
        """
        logging.info(
            f"Watchdog loop started (silence timeout={WATCHDOG_SILENCE_TIMEOUT:.0f}s, "
            f"check every {WATCHDOG_CHECK_INTERVAL:.0f}s)"
        )
        try:
            while self.is_running and writer and not writer.is_closing():
                await asyncio.sleep(WATCHDOG_CHECK_INTERVAL)
                if not self.is_running or not writer or writer.is_closing():
                    break
                silent_for = time.time() - self._last_data_time
                if silent_for > WATCHDOG_SILENCE_TIMEOUT:
                    logging.warning(
                        f"⚠️ Watchdog: ไม่ได้รับข้อมูลจาก PBX เป็นเวลา {silent_for:.0f}s "
                        f"(เกินเกณฑ์ {WATCHDOG_SILENCE_TIMEOUT:.0f}s) — Force reconnect!"
                    )
                    self._watchdog_triggered = True
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except Exception:
                        pass
                    break
        except asyncio.CancelledError:
            logging.info("Watchdog loop cancelled")
        except Exception as e:
            logging.warning(f"Error in watchdog loop: {e}")

    async def start_listening(self):
        self.is_running = True
        await self.init_http_session()

        # เริ่มต้นรัน Built-in TCP Proxy Server เพื่อแชร์ข้อมูลให้ Room Manager บนพอร์ต 2323
        try:
            self.proxy_server = await asyncio.start_server(
                self.handle_proxy_client, '0.0.0.0', self.proxy_port
            )
            logging.info(f"🚀 Built-in TCP SMDR Proxy Server กำลังรันที่พอร์ต 0.0.0.0:{self.proxy_port}")
        except Exception as e:
            logging.error(f"❌ ไม่สามารถเริ่มรัน TCP Proxy Server ที่พอร์ต {self.proxy_port} ได้: {e}")
            self.proxy_server = None

        while self.is_running:
            writer = None
            heartbeat_task = None
            rdss_poll_task = None
            watchdog_task = None
            try:
                logging.info(f"Connecting to Phonik PBX Telnet at {self.host}:{self.port}...")
                reader, writer = await asyncio.open_connection(self.host, self.port)
                logging.info("Connected successfully to Phonik PBX!")

                self._read_buffer = b""
                self._last_data_time = time.time()
                self._watchdog_triggered = False
                await self._read_initial_banner(reader)

                auth_ok = await self.pbx_session.authenticate(writer, reader)
                if not auth_ok:
                    logging.error(
                        "PBX authentication failed — retry in 10s. "
                        "ตรวจสอบ PBX_PASS และว่าไม่มี client อื่นครอง session (เช่น PC Operator)"
                    )
                    await asyncio.sleep(10)
                    continue

                logging.info(
                    "Listening for SMDR stream... "
                    "(หากต้องการตรวจสอบย้อนหลัง: เปิดโปรแกรม Room Manager ชี้มาที่พอร์ต 2323 ของ Pi)"
                )

                # เริ่มทำงาน Heartbeat Loop + RDSS Poll Loop + Watchdog ใน Background
                heartbeat_task = asyncio.create_task(self._heartbeat_loop(writer))
                rdss_poll_task = asyncio.create_task(self._rdss_poll_loop(writer))
                watchdog_task = asyncio.create_task(self._watchdog_loop(writer))

                while self.is_running:
                    chunk = await reader.read(4096)
                    if not chunk:
                        if self._watchdog_triggered:
                            # Watchdog เป็นคนตัด (session เงียบ) → reconnect เร็วทันที
                            logging.warning("Watchdog force-reconnect initiated — reconnecting immediately")
                            await asyncio.sleep(2)
                        else:
                            logging.warning("Connection closed by PBX server. Backing off for 15 seconds before retrying...")
                            await asyncio.sleep(15)
                        break

                    # มีข้อมูลไหลเข้า = session ยังมีชีวิต → อัปเดต timestamp ให้ watchdog
                    self._last_data_time = time.time()
                    self._read_buffer += chunk
                    for line in self._extract_lines():
                        # บรอดแคสต์ข้อมูลดิบให้ Room Manager / TCP Clients ที่พอร์ต 2323
                        await self.broadcast_to_proxy_clients(line)
                        await self._process_line(line)

            except Exception as e:
                logging.error(f"Error in PBX Telnet listener: {e}. Retrying in 5 seconds...")
                await asyncio.sleep(5)
            finally:
                # ยกเลิกและเคลียร์ Background Tasks ให้เรียบร้อย
                for task in (heartbeat_task, rdss_poll_task, watchdog_task):
                    if task and not task.done():
                        task.cancel()
                        try:
                            await task
                        except Exception:
                            pass
                if writer and not writer.is_closing():
                    try:
                        writer.close()
                        await writer.wait_closed()
                    except Exception:
                        pass

    async def stop_listening(self):
        self.is_running = False
        
        # ปิด Proxy Server
        if self.proxy_server:
            logging.info("Stopping Built-in TCP Proxy Server...")
            self.proxy_server.close()
            try:
                await self.proxy_server.wait_closed()
            except Exception:
                pass
            self.proxy_server = None

        # เคลียร์และปิดท่อ Client ทั้งหมด
        for writer in list(self.connected_clients):
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
        self.connected_clients.clear()

        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
            logging.info("HTTP session closed")


if __name__ == "__main__":
    listener = PhonikSNCListener()
    try:
        asyncio.run(listener.start_listening())
    except KeyboardInterrupt:
        logging.info("Listener stopped by user")
        asyncio.run(listener.stop_listening())
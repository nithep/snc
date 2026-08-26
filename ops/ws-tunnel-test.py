#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================================
# ops/ws-tunnel-test.py — ตรวจสอบ WebSocket ผ่าน Cloudflare Tunnel (เต็มวงจร)
# ----------------------------------------------------------------------------
# ตรวจว่า Dashboard รับเหตุการณ์ใหม่แบบ real-time ผ่าน tunnel ได้จริงหรือไม่:
#   1) เชื่อม WS ผ่าน wss://<host>/ws/nurse-station (ข้าม Cloudflare Tunnel)
#   2) ยิง POST /api/demo/trigger (source=demo — ไม่ปนข้อมูลจริง/KPI)
#   3) รอรับ WS broadcast แล้วตรวจ status/roomId/source ตรงกัน
#
# ⚠️ สาเหตุที่ต้องมี User-Agent แบบเบราว์เซอร์:
#    Cloudflare WAF จะตอบ 403 ให้ POST ที่ไม่มี User-Agent ของเบราว์เซอร์จริง
#    (เช่น urllib default) — เบราว์เซอร์ปกติไม่เจอปัญหานี้
#
# วิธีใช้:
#   python ops/ws-tunnel-test.py                          # ใช้ https://snc.nithep.com
#   HOST="snc.nithep.com" python ops/ws-tunnel-test.py
#   python ops/ws-tunnel-test.py --room 0400 --event CALL_BATHROOM_EMERGENCY
#
# exit code: 0 = ผ่าน (WS ผ่าน tunnel + broadcast กลับครบ), 1 = ล้มเหลว
# ============================================================================
import argparse
import asyncio
import json
import os
import ssl
import sys
import urllib.request

# Windows console (cp874) พิมพ์อักษร box-drawing ไม่ได้ — บังคับ UTF-8 (กฎ Strict UTF-8)
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# ค่าเริ่มต้น — เปลี่ยนผ่าน env var (เช่นเดียวกับสคริปต์ ops/ อื่นๆ)
DEFAULT_HOST = os.getenv("WS_TEST_HOST", "snc.nithep.com")
DEFAULT_ROOM = os.getenv("WS_TEST_ROOM", "0400")
DEFAULT_EVENT = os.getenv("WS_TEST_EVENT", "CALL_BEDSIDE")

# Cloudflare WAF ปล่อย POST ผ่านเฉพาะเมื่อมี User-Agent ของเบราว์เซอร์จริง
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def fail(msg: str) -> None:
    print(f"❌ {msg}")
    sys.exit(1)


async def main() -> None:
    parser = argparse.ArgumentParser(description="ตรวจสอบ WebSocket ผ่าน Cloudflare Tunnel (SNC)")
    parser.add_argument("--host", default=DEFAULT_HOST, help="hostname ผ่าน tunnel (default: %(default)s)")
    parser.add_argument("--room", default=DEFAULT_ROOM, help="room_id สำหรับ demo trigger (default: %(default)s)")
    parser.add_argument("--event", default=DEFAULT_EVENT,
                        choices=["CALL_BEDSIDE", "CALL_BATHROOM_EMERGENCY"],
                        help="event_type สำหรับ demo trigger (default: %(default)s)")
    parser.add_argument("--check-only", action="store_true",
                        help="ตรวจแค่ว่า WS ผ่าน tunnel เปิดได้ (ไม่ยิง event) — เหมาะกับ cron")
    args = parser.parse_args()

    try:
        import websockets  # type: ignore
    except ImportError:
        fail("ไม่พบไลบรารี websockets — ติดตั้งด้วย: pip install websockets")

    ws_url = f"wss://{args.host}/ws/nurse-station"
    trigger_url = f"https://{args.host}/api/demo/trigger"
    print("═══════ SNC WebSocket Tunnel Test ═══════")
    print(f"WS      : {ws_url}")
    print(f"Trigger : {trigger_url} (room={args.room}, event={args.event})")

    ctx = ssl.create_default_context()
    try:
        async with websockets.connect(ws_url, ssl=ctx, open_timeout=15) as ws:
            print("✅ เชื่อม WS ผ่าน tunnel สำเร็จ")

            if args.check_only:
                print("✅ โหมด --check-only: WS เปิดได้ผ่าน tunnel (ไม่ยิง event)")
                print("═══════════ PASS — WS tunnel reachable ═══════════")
                return

            print("— รอ broadcast...")
            # ยิง demo trigger ผ่าน tunnel (ต้องมี browser UA กัน Cloudflare WAF 403)
            body = json.dumps({"room_id": args.room, "event_type": args.event}).encode()
            req = urllib.request.Request(
                trigger_url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": BROWSER_UA,
                },
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=15)
            print(f"✅ POST /api/demo/trigger → HTTP {resp.status}")

            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
            ext = msg.get("extension", {})
            status = msg.get("status")
            room_id = ext.get("roomId")
            source = ext.get("source")

            print(f"📡 WS broadcast รับ: status={status} roomId={room_id} source={source}")

            # ตรวจความถูกต้องของ payload — ต้องตรงกับที่ dashboard คาดหวัง
            if room_id != args.room.zfill(4):
                fail(f"roomId ไม่ตรง: ได้ {room_id} คาด {args.room.zfill(4)}")
            if source != "demo":
                fail(f"source ควรเป็น demo (กันปนข้อมูลจริง) — ได้ {source}")
            if status != "active":
                fail(f"status ควรเป็น active — ได้ {status}")
            print("✅ พบ payload ตรงตามที่ Dashboard ใช้ (extension.roomId/source + status)")
            print("═══════════ PASS — WS ผ่าน tunnel ทำงาน real-time ═══════════")
    except asyncio.TimeoutError:
        fail(f"ไม่ได้รับ WS broadcast ภายใน 10 วิ (tunnel ช้า/WS ตาย? ดู pill connLive บน dashboard)")
    except Exception as e:
        fail(f"การเชื่อมต่อ WS ผ่าน tunnel ล้มเหลว: {e}")


if __name__ == "__main__":
    asyncio.run(main())

import os
import sys
import socket
import sqlite3
import json
import urllib.request
import urllib.error
from datetime import datetime

# Ensure UTF-8 output on Windows / Linux console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Colors for terminal styling
GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
NC = "\033[0m"

# Path setups relative to project root
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
DB_PATH = os.path.join(BACKEND_DIR, "nurse_call_events.db")

print(f"{CYAN}============================================================{NC}")
print(f"{CYAN}🏥 ระบบ Smart Nurse Call (SNC) — Pre-Flight Health Check{NC}")
print(f"{CYAN}⏰ เวลาตรวจสอบ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NC}")
print(f"{CYAN}============================================================{NC}\n")

# 1. Load Environmental Variables (.env)
print(f"{YELLOW}[1/6] ตรวจสอบไฟล์การตั้งค่าระบบ (.env)...{NC}")
env_path = os.path.join(BACKEND_DIR, ".env")
if not os.path.exists(env_path):
    env_path = os.path.join(PROJECT_ROOT, ".env")

if os.path.exists(env_path):
    print(f"   {GREEN}✅ พบไฟล์การตั้งค่าที่: {env_path}{NC}")
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().replace('"', '').replace("'", "")
else:
    print(f"   {YELLOW}⚠️  ไม่พบไฟล์ .env ระบบจะใช้ค่าเริ่มต้นจาก Environment Variables แทน{NC}")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GOOGLE_CHAT_WEBHOOK_URL = os.getenv("GOOGLE_CHAT_WEBHOOK_URL", "")
PBX_IP = os.getenv("PBX_IP", "192.168.1.91")
PBX_PORT = int(os.getenv("PBX_PORT", "23"))

# 2. Network Check
print(f"\n{YELLOW}[2/6] ตรวจสอบการเชื่อมต่อเครือข่ายอินเทอร์เน็ต...{NC}")
internet_ok = False
try:
    socket.setdefaulttimeout(3)
    socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
    print(f"   {GREEN}✅ เชื่อมต่ออินเทอร์เน็ตปกติ (Google DNS - 8.8.8.8:53 OK){NC}")
    internet_ok = True
except Exception as e:
    print(f"   {RED}❌ ไม่สามารถเชื่อมต่ออินเทอร์เน็ตได้: {e}{NC}")

# 3. Database Check
print(f"\n{YELLOW}[3/6] ตรวจสอบความสมบูรณ์ของฐานข้อมูล SQLite (SNC Database)...{NC}")
try:
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode;")
    mode = cursor.fetchone()[0]
    print(f"   - Database Journal Mode: {GREEN}{mode.upper()}{NC}")
    cursor.execute("PRAGMA integrity_check;")
    status = cursor.fetchone()[0]
    if status == "ok":
        print(f"   {GREEN}✅ ตรวจสอบความสมบูรณ์ของระบบไฟล์ SQLite ผ่าน (Integrity OK){NC}")
    else:
        print(f"   {RED}❌ ตรวจพบความเสียหายของฐานข้อมูล: {status}{NC}")
    cursor.execute("SELECT COUNT(*) FROM nurse_call_events")
    event_count = cursor.fetchone()[0]
    print(f"   - จำนวนเหตุการณ์บันทึกในฐานข้อมูลปัจจุบัน: {GREEN}{event_count} รายการ{NC}")
    conn.close()
except Exception as e:
    print(f"   {RED}❌ ตรวจสอบฐานข้อมูลล้มเหลว: {e}{NC}")

# 4. PBX Port connectivity Check
print(f"\n{YELLOW}[4/6] ตรวจสอบการสื่อสาร LAN ไปยังตู้ Phonik PBX...{NC}")
print(f"   - เป้าหมาย PBX IP: {PBX_IP}:{PBX_PORT}")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(4.0)
    result = sock.connect_ex((PBX_IP, PBX_PORT))
    if result == 0:
        print(f"   {GREEN}✅ ตู้สาขา Phonik PBX สแตนด์บายพร้อมเชื่อมต่อ (Port {PBX_PORT} Open){NC}")
    else:
        print(f"   {RED}❌ ไม่สามารถติดต่อพอร์ตตู้สาขาได้ (Port {PBX_PORT} Closed / Connection Refused){NC}")
        print(f"     [คำแนะนำ] ตรวจสอบสาย LAN ระหว่าง Raspberry Pi กับตู้ PBX หรือตรวจสอบ IP ของตู้{NC}")
    sock.close()
except Exception as e:
    print(f"   {RED}❌ ตรวจสอบพอร์ตตู้สาขาล้มเหลว: {e}{NC}")

# 5. API Keys and Integrations Verification
print(f"\n{YELLOW}[5/6] ตรวจสอบ API Integrations (Gemini AI & Google Chat)...{NC}")
if GOOGLE_CHAT_WEBHOOK_URL:
    masked_webhook = GOOGLE_CHAT_WEBHOOK_URL[:40] + "..."
    print(f"   - Google Chat Webhook: {GREEN}ตรวจพบ ({masked_webhook}){NC}")
else:
    print(f"   - Google Chat Webhook: {RED}ไม่พบการตั้งค่าใน .env (ระบบจะไม่ส่งข้อความแจ้งเตือนเรียลไทม์){NC}")

if not GEMINI_API_KEY:
    print(f"   - Gemini API Key: {RED}ไม่พบใน .env (ระบบจะทำงานในโหมด Local Fallback เท่านั้น){NC}")
else:
    masked_key = GEMINI_API_KEY[:8] + "..." + GEMINI_API_KEY[-5:] if len(GEMINI_API_KEY) > 15 else "..."
    print(f"   - Gemini API Key: {GREEN}ตรวจพบ ({masked_key}){NC}")
    if internet_ok:
        print("   - กำลังทดสอบส่ง Prompt ไปยัง Gemini API เพื่อเช็คโควตา...")
        try:
            is_openrouter = GEMINI_API_KEY.startswith("sk-or-")
            if is_openrouter:
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {GEMINI_API_KEY}",
                    "HTTP-Referer": "https://hotel.nithep.com",
                    "X-Title": "Smart Nurse Call (SNC)"
                }
                payload = {
                    "model": "meta-llama/llama-3.3-70b-instruct",
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 5
                }
            else:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{"parts": [{"text": "สวัสดีระบบทดสอบ ตอบสั้นๆว่า OK เท่านั้น"}]}],
                    "generationConfig": {"maxOutputTokens": 10}
                }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=8) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                if "error" in res_json:
                    raise Exception(res_json["error"].get("message", "API Error"))
                print(f"   {GREEN}✅ บริการ AI API ออนไลน์และพร้อมประมวลผลสรุปข้อมูล{NC}")
        except urllib.error.HTTPError as e:
            error_msg = e.read().decode("utf-8") if e.fp else str(e)
            print(f"   {YELLOW}⚠️  API ภายนอกตอบกลับ HTTP {e.code}: {error_msg[:80]}{NC}")
            print(f"   {GREEN}   └─> ระบบสลับเข้าใช้ Local Analytics Engine อัตโนมัติ (พร้อมสรุปผล 100% ฿0/เดือน){NC}")
        except Exception as e:
            print(f"   {YELLOW}⚠️  การเชื่อมต่อ API ภายนอกขัดข้อง: {e}{NC}")
            print(f"   {GREEN}   └─> ระบบสลับเข้าใช้ Local Analytics Engine อัตโนมัติ (พร้อมสรุปผล 100% ฿0/เดือน){NC}")
    else:
        print(f"   - {YELLOW}ข้ามการตรวจสอบสัญญาณ API เนื่องจากไม่มีอินเทอร์เน็ต (สลับเข้าโหมด Local Fallback อัตโนมัติ){NC}")

# 6. Service Process Check
print(f"\n{YELLOW}[6/6] แนะนำการจัดการ Service หน้างาน (Process Supervisor)...{NC}")
print(f"   - รันในโหมด Quick Start: {GREEN}cd ~/nithep/snc && ./ops/quick_start.sh{NC}")
print(f"   - ตรวจสอบสถานะ Backend CLI: {GREEN}curl -s http://localhost:8000/health{NC}")

print(f"\n{CYAN}============================================================{NC}")
print(f"🎉 ตรวจสอบสถานะเสร็จสิ้น กรุณาตรวจสอบผลลัพธ์สีแดง ({RED}❌{NC}) เพื่อแก้ไขก่อนการทดสอบจริง")
print(f"{CYAN}============================================================{NC}")

---
title: "SESSION_HANDOVER_2026-08-25 — Dashboard Overhaul + Real/Demo Separation + As-built PBX Mapping"
type: handover
tags: [status, dashboard, deploy, cloud-run, pbx, kpi, ai]
---

# SESSION_HANDOVER_2026-08-25 — Dashboard Overhaul + Real/Demo Separation + As-built PBX Mapping

> จัดทำ: 25 ส.ค. 2569 | ครอบคลุมงานคืนเดียวยาว: ตรวจ/แก้ dashboard, ปลดล็อก deploy Cloud Run, แยกข้อมูลจริง/จำลอง, KPI Views, ผังพอร์ต as-built
> ต่อจาก [[SESSION_HANDOVER_2026-08-23]]

## การตัดสินใจสำคัญ (Decision)

1. **แยกข้อมูลจริง/จำลองระดับ DB** — เพิ่มคอลัมน์ `source` (`real`/`demo`) ใน `nurse_call_events`: listener PBX (ส่ง `event_id` มาเสมอ ตาม [[0004-outbox-idempotency|ADR 0004]]) → `real`, ปุ่มจำลอง → `demo` — KPI/ประวัติ/กราฟนับเฉพาะ `real`
2. **Dashboard จริงไม่มีของจำลอง** — ถอด Demo Bar ออกทั้งชุด; ปุ่มทดสอบย้ายไปเป็นวิดเจ็ตสาธารณะบน Landing Page (`POST /api/demo/trigger` ไม่ต้องมี key แต่*บังคับ* source=demo ฝั่งเซิร์ฟเวอร์)
3. **ลบกราฟ trend ออกจาก dashboard** — เปลี่ยนเป็น KPI View Selector (ดูหัวข้องานด้านล่าง); endpoint `/api/analytics/trend` ยังอยู่ใน API (ไม่ถูกเรียกจาก UI)
4. **ตู้ PBX จริง: เบอร์สถานี = เลขห้องอยู่แล้ว (1100-1127)** → `room_map.json` ว่างไว้ (identity) — ผังฉบับเต็มดู [[PBX_PORT_ROOM_MAPPING]]
5. **เก็บกวาด DB ฝั่ง Pi** — ลบข้อมูลทดสอบ 89 เหตุการณ์ (backup ก่อนเสมอ) ให้ KPI เริ่มจากของจริง

## งานที่ทำ

### Dashboard — `app/index.html`
- **แก้ตาราง History ที่แตก**: แท็กเปิด `<div class="table-wrap"><table><thead><tr>` + หัวคอลัมน์ 2 ช่องหายไปตั้งแต่ commit `8c27b85` (restore จาก git history)
- **Redesign History**: 6 คอลัมน์ (badge ห้องสีตามสถานะ | ชื่อเหตุการณ์+อุปกรณ์ NCX-CORD/NCX-PULL/Handset | สถานะ | เวลารับเรื่อง/เคลียร์ แบบนาฬิกา | SLA 3 สถานะ) — แสดง 3 เหตุการณ์ล่าสุด
- **KPI View Selector**: dropdown `รวมทั้งระบบ` (การ์ด 5 ใบ) / `รายห้อง` / `รายประเภทเหตุการณ์` (ตาราง: จำนวน, avg ack, avg res, เกิน SLA, %compliance) — คำนวณ client-side จาก real events, จำค่าใน localStorage
- **Status Strip**: chip สถานะห้องปัจจุบัน (ปกติ/เรียก/รับเรื่อง) ใต้ KPI
- ลบ Demo Bar + settings checkbox; แก้ i18n keys หาย (`aiTitle/aiHint/aiUnavailable` ถูกกลืนตอนลบ demo keys)

### Backend — `api/`
- `storage.py`: คอลัมน์ `source` (self-migrate ผ่าน `ensure_column`), filter ทั้ง SQLiteStore + FirestoreStore, `get_trend(bucket=day|month|year)`
- `server.py`: ติดแท็ก `extension.source` ที่ `trigger_event`, query param `?source=` ที่ `/api/events` + `/api/analytics/kpi` (default `real`), endpoint ใหม่ `POST /api/demo/trigger` (public whitelist) และ `GET /api/analytics/trend`
- **`Dockerfile`: เพิ่ม `COPY core/ core/`** — เดิม image ไม่มีโมดูล `core/` ทำให้ container crash ตอน boot (`ModuleNotFoundError: No module named 'core'`) — ซ่อนมาตั้งแต่ commit e1107ae เพราะไม่เคย rebuild

### Listener — `pbx/`
- **Port→Room mapping**: `room_map.json` + `load_room_map()` hot-reload (แก้ไฟล์มีผลทันที) — แปลงที่ `_create_event_payload` จุดเดียว
- Tests 26 → **28** (เพิ่ม test mapping + hot-reload, ใช้ fixture `SNC_ROOM_MAP` ไม่พึ่งไฟล์จริง)

### Deploy Infra
- `ops/deploy_gcp_cloudrun.ps1`: เติม UTF-8 BOM (PS 5.1 parse ไทยพัง) + เปลี่ยน `--set-env-vars` → `--update-env-vars` (merge — กันลบ `SNC_API_KEY`/`GEMINI_API_KEY` บน service ตอนค่าในเครื่องว่าง)
- Cloud Run revisions: 00021 (core/ fix) → 00022 (GEMINI key) → 00023 (source separation) → **00024 (KPI views) — ตัวปัจจุบัน**

### AI / API Keys
- `GEMINI_API_KEY` บน Pi (`/home/ecs-agent/snc/api/.env`) เป็น **OpenRouter key** (`sk-or-…`) — `gemini_direct_service.py` ตรวจ prefix แล้วเลือกเอง: OpenRouter → `meta-llama/llama-3.3-70b-instruct`, Gemini key → `gemini-2.0-flash`, ไม่มี key → Local Fallback Engine
- Sync key ขึ้น Cloud Run แล้ว — ทดสอบ `/api/ai/daily-summary` ตอบไทยถูกต้องทั้ง Pi และ Cloud (Pi ↔ Cloud ใช้ key เดียวกัน ตามกฎ rotation guide)

### ข้อมูล / PBX As-built
- DB Pi: backup → wipe 89 test events (backup: `nurse_call_events_backup_20260824231358.db`)
- ผังพอร์ตตู้จริงบันทึกฉบับ as-built → [[PBX_PORT_ROOM_MAPPING]] (DX-COMPACT V5.4r1, SSID 136375, เบอร์ 1100-1127, **1116 ไม่มีบนระบบ**, 1100 = Master Console, data SLT = Grp 32)

## สถานะปัจจุบัน (ตรวจแล้ว)

| ระบบ | สถานะ |
|---|---|
| Pi (snc.nithep.com) | ไฟล์ md5 ตรงทุกแฟ้ม, `snc-backend` + `snc-pbx-listener` active, `/health` 200 |
| Cloud Run | rev `00024` serving 100%, `/health` healthy |
| Parser tests | 28/28 PASSED |
| E2E separation | demo trigger → `source=demo` ไม่เข้า KPI; **event จริงจากตู้** (0400, ack 9s, res 14s) → `source=real` ถูกนับ |
| AI Summary | ใช้งานได้ทั้ง Pi + Cloud (OpenRouter/Llama-3.3-70B) |

## ไฟล์ที่แก้ (✅ commit แล้ว — `1691657`)

> ⚠️ ~~หัวข้อเดิมเขียนว่า "ยังไม่ commit"~~ — **ล้าสมัยแล้ว**: รายการทั้งหมดรวมอยู่ใน commit `1691657` ("feat: milestone 25/8/2569 — แยก Real/Demo events + KPI Views + Port→Room Mapping + deploy fixes", 25 ส.ค. 2569 01:20 +07) และ working tree สะอาด ตรวจยืนยัน 25 ส.ค.

`app/index.html` · `app/landing.html` · `api/server.py` · `api/storage.py` · `api/Dockerfile` · `pbx/snc_pbx_listener.py` · `pbx/room_map.json` (ใหม่) · `pbx/test_smdr_parser.py` · `ops/deploy_gcp_cloudrun.ps1` · `doc/wiki/PBX_PORT_ROOM_MAPPING.md` (ใหม่)

## ผลตรวจสอบ Runtime (Audit 25 ส.ค. 2569 — เครื่อง dev Windows)

> ตามมาจากผู้ใช้รายงาน "ยังใช้งานไม่ได้ ยังไม่สมบูรณ์ หลายจุด" — boot backend จริง (`uvicorn server:app` :8000) + ทดสอบ endpoints + Edge headless เปิด dashboard → **ทุกรายการผ่าน**:

| การทดสอบ | ผล |
|---|---|
| `/health` | 200 healthy (SQLite) |
| Parser tests | **28/28 PASSED** |
| `/api/events?source=real\|demo` | แยกถูกต้อง (real 14 / demo แยกชุด) |
| `/api/analytics/kpi` (default) | นับเฉพาะ real — demo ไม่หลุดเข้า KPI ✓ |
| `/api/analytics/trend?bucket=month/year` | points ถูกต้อง (ดูหมายเหตุ `day` ด้านล่าง) |
| `POST /api/demo/trigger` | public ไม่ต้องมี key + บังคับ `source=demo` เสมอ ✓ |
| `POST /api/events/trigger` ไม่ใส่ `event_id` | ถูกแท็ก `demo` อัตโนมัติ (กันปนเปื้อนข้อมูลจริง) ✓ |
| WebSocket `/ws/nurse-station` | broadcast ทันที — roomId/sourceEventType/source/status ครบ ✓ |
| Dashboard `/index.html` (Edge headless) | render ครบ: 31 room cards + KPI cards + History 14 events + WS live pill — **console ไม่มี error** |
| i18n TH/EN | 96 keys ตรงกันทั้ง 2 ภาษา, `t()` calls + `data-i18n-key` resolve ครบ |
| Ack endpoint | 200 + status เปลี่ยนเป็น acknowledged |

### จุดที่พบว่า "เข้าใจผิดได้ว่าใช้ไม่ได้" (ไม่ใช่บั๊ก)

1. **`/` คือ Landing Page (marketing) ไม่ใช่ dashboard** — dashboard จริงอยู่ที่ [`/index.html`](http://localhost:8000/index.html) หรือ `/dashboard` (`server.py:151`) หน้า landing มี demo widget เด่นทั้งหน้า ทำให้ดูเหมือน "dashboard ยังมีของจำลอง/ไม่สมบูรณ์" ถ้าเข้าผิดหน้า
2. **เครื่อง dev ไม่มี `SNC_API_KEY`** (ไม่มี `api/.env`) → POST ทุกตัวผ่านโดยไม่บังคับ key — by design: auth เปิดเฉพาะเมื่อตั้ง key (บน Pi/Cloud Run มี key จึงคืน 401)
3. **`trend?bucket=day` คืน `points: []`** เพราะ query เฉพาะ **24 ชม.ล่าสุด** (`storage.py:255-263`) — events จาก 14 ส.ค. ต้องดู `bucket=month`
4. **History table แสดง 3 เหตุการณ์ล่าสุดเท่านั้น** (ดีไซน์ Nurse Station ตามหัวข้องานด้านบน) — ไม่ใช่ตารางหาย

### การเก็บกวาดหลัง audit
ลบ event ทดสอบ 5 รายการที่ audit สร้างขึ้น (demo 9999/8888/7777 + 0400×2 จาก trigger ไม่ใส่ event_id) ออกจาก DB dev — รวม 19 → เหลือ **real 14 เหตุการณ์** เท่าก่อน audit

## สิ่งค้าง / ข้อควรรู้

1. **Firestore มี test events เก่า** (ไม่มี field `source` → ถูกนับเป็น real) — เก็บกวาดก่อนถ้าจะ demo ผ่าน Cloud Run
2. `nursecall.nithep.com` DNS ไม่ resolve จากเครื่อง dev (ใช้ `snc.nithep.com` ซึ่งเสิร์ฟจาก Pi ผ่าน Cloudflare)
3. `GEMINI_API_KEY` ไม่ได้อยู่ใน Secret Manager (rotation guide เขียนไว้แต่ยังไม่ถูกปฏิบัติ) — key อยู่ใน `.env` ของ Pi + env ของ Cloud Run
4. **Config Builder หน้า Offline แสดงค่า default (1001-1028) ไม่ใช่ config จริง** — ต้อง Online → Read เท่านั้น (หลงมาแล้ว 1 ครั้ง)
5. Cloudflare บล็อก User-Agent แบบ python-urllib (403) — ทดสอบ API ด้วย UA อื่น ไม่ใช่บั๊ก
6. ห้อง 1116 ไม่มีตัวตนบนตู้ — dashboard แสดงการ์ด cosmetic (ไม่กระทบ KPI)

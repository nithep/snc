# ops/raw/ — Non-PHI Trace Dump (Event & Telemetry Traces)

> ตามสถาปัตยกรรม ADR 0013 — จุดรับ **Trace Dump แบบ Non-PHI** จากระบบ SNC
> เพื่อป้อนเข้าสู่กระบวนการกลั่นความรู้ (Fabric → Wiki / Playbooks) แบบอัตโนมัติ

## วัตถุประสงค์

- เก็บ **ต้นทางข้อมูล (raw traces)** สำหรับกระบวนการกลั่นความรู้ในคืน (Nightly Batch)
  โดย **ไม่รบกวน Critical Path** (PBX → Listener → Outbox → API → Dashboard)
- ข้อมูลมาจาก `pbx/event_outbox.py` (สำเนา trace ที่ไม่ใช่ PHI) และ Telemetry ระบบ
  (SLA timing, ความถี่ event, สถานะ service) — **ห้าม**ดึงข้อมูลจาก Critical Path กลับมา

## กฎ Non-PHI (บังคับ)

ไฟล์ในไดเรกทอรีนี้ **ต้องเป็น Non-PHI เท่านั้น**:

| อนุญาต ✅ | ห้าม ❌ |
|---|---|
| Event type, room ID (ตัวเลขห้อง), timestamp | ชื่อ-นามสกุลผู้ป่วย, HN, รายละเอียดอาการ |
| SLA timing (ack/resolution seconds) | ข้อมูลที่ระบุตัวบุคคลได้ (PDPA-sensitive) |
| สถิติรวม / aggregate ระดับกลุ่มห้อง | payload FHIR ดิบที่มี Patient resource |

> ✅ **Phase 3 เสร็จสิ้น (2026-09-04)** — มีสคริปต์ export แล้ว: `ops/export_traces.py`
> (ดูวิธีใช้ + การทดสอบด้านล่าง — ตาม ADR 0013)

## การสร้าง traces (export script)

```bash
# export ข้อมูล 1 วันที่ผ่านมา (ใช้ใน nightly loop) → ops/raw/traces-YYYYMMDD.jsonl
python3 ops/export_traces.py --days 1

# ตัวเลือกอื่น: --since 2026-09-01 (ตั้งแต่วันที่) · --stdout (print แทนเขียนไฟล์) · --db path
# exit code: 0 = มีข้อมูล · 1 = error · 2 = ไม่มีข้อมูลในช่วง (nightly loop จะข้าม)

# คำนวณสถิติ deterministic (เครื่อง) — ใช้เป็นตัวเลขหลักให้ LLM (กัน LLM นับผิด)
python3 ops/export_traces.py --stats --days 1
```

- อ่านจาก `api/nurse_call_events.db` แบบ **read-only** (ไม่รบกวน backend ที่รันอยู่)
- ตัดเฉพาะ field **Non-PHI whitelist** — `fhir_payload` ดิบไม่ถูก export (ADR 0013)
- ทดสอบ: `.venv/Scripts/python.exe -m pytest tests/test_export_traces.py` (6 tests)
- ตัวอย่าง traces สังเคราะห์สำหรับทดสอบ pattern: `ops/fabric/samples/sample-traces-20260903.jsonl`

## นโยบาย Git

- **เนื้อหาในไดเรกทอรีนี้ถูก gitignore** (`ops/raw/*`) — เป็น runtime artifacts
  ที่อาจสะสมจำนวนมาก ไม่ควร commit — ดู ADR 0013 และ `.gitignore`
- คงไว้เฉพาะ `README.md` นี้เท่านั้นที่ถูก track

## Conventions

- ไฟล์ traces: ใช้ extension `.jsonl` / `.ndjson` (1 record ต่อบรรทัด, UTF-8)
- ตั้งชื่อตามรอบ: `traces-YYYYMMDD.jsonl` (ตามลำดับเวลา ดูง่ายสำหรับ cron)
- ห้ามเก็บ trace ที่มีขนาดใหญ่โดยไม่จำกัด — ให้ cron นำไปกลั่นแล้วกวาดทิ้ง
---
title: "🔄 คู่มือหมุนเวียน Cloudflare Tunnel Credentials (Rotation Guide)"
type: guide
tags: [security]
---

# 🔄 คู่มือหมุนเวียน Cloudflare Tunnel Credentials (Rotation Guide)

> **เวอร์ชัน:** 1.0 | **อัปเดตล่าสุด:** 19 ส.ค. 2569
> **ใช้กับ:** Smart Nurse Call (SNC) PoC — โครงสร้าง 5-Core (`doc/BLUEPRINT_5CORE.md`)
> **อ้างอิง:** [`SNC_CLOUDFLARE_TUNNEL_SUMMARY.md`](SNC_CLOUDFLARE_TUNNEL_SUMMARY.md), [`SNC_CLOUDFLARE_SETUP_SUMMARY.md`](SNC_CLOUDFLARE_SETUP_SUMMARY.md)

---

## 📌 ควร rotate เมื่อไหร่

| กรณี | ความเร่งด่วน |
|---|---|
| Tunnel token / credentials รั่วใน git history / เอกสาร | 🔴 เร่งด่วนสุด |
| สงสัยว่ามีคนนอกทราบ token | 🔴 เร่งด่วน |
| Tunnel ถูกโอนย้าย ownership / ทีมเปลี่ยน | 🟡 เร็วที่สุด |
| หมุนเวียนประจำ (ทุก 90 วัน) | 🟢 ตามกำหนด |

---

## ⚙️ หลักการสำคัญ

1. **Tunnel token (credentials file / cloudflared token)** เป็นกุญแจให้ใครก็ได้ที่ถือมันเชื่อมเข้าเครือข่าย SNC ผ่าน Cloudflare → เป็น secret ที่ต้องปกป้องเทียบเท่า API key
2. **ห้าม commit credentials ลง git** — `.gitignore` ครอบคลุม `*credentials*.json`, `*.pem` เป็นต้น (ตรวจ `git status --ignored` ว่าไฟล์ legit ถูกกลืนไหม)
3. **ห้ามใช้ IP วงแลนใน Service URL** — ชี้ `http://localhost:8000` เสมอ (กฎเหล็ก — ดู Tunnel Summary) ป้องกัน 502
4. **rotate แล้ว token เก่าไร้ค่าทันที** — Cloudflare revoke ฝั่ง Zero Trust Dashboard

---

## 📍 ตำแหน่ง credentials ทั้งระบบ

| Component | ตำแหน่ง | วิธีอ่าน |
|---|---|---|
| Tunnel credentials (Pi4) | `/home/ecs-agent/snc-poc/.cloudflared/*.json` (หรือ `cert.pem`) | `ls -la .cloudflared/` |
| cloudflared token (ถ้าใช้ Remote Tunnel) | ตั้งค่าใน Zero Trust Dashboard + env | `cloudflared tunnel list` |
| Config file | `/home/ecs-agent/snc-poc/.cloudflared/config.yml` | `cat config.yml` |

---

## 🔄 ขั้นตอน rotate (ฉบับสมบูรณ์ — Remote Tunnel)

### Step 1: Backup credentials เดิมบน Pi4

```bash
ssh pi4 "cd /home/ecs-agent/snc-poc && ts=\$(date +%Y%m%d%H%M%S) && \
  cp -r .cloudflared backups/cloudflared.\$ts && \
  echo \"Backup: backups/cloudflared.\$ts\""
```

### Step 2: สร้าง Tunnel token ใหม่ (ฝั่ง Zero Trust Dashboard)

1. เข้า Cloudflare Zero Trust → **Access → Tunnels**
2. เลือก tunnel ที่ใช้ (`nursecall` / `hotel`) → **Configuration → Token**
3. **Regenerate token** / Rotate — คัดลอก token ใหม่

### Step 3: อัปเดต token บน Pi4

```bash
NEW_TOKEN="<token ใหม่จาก Step 2>"

ssh pi4 "sudo systemctl stop cloudflared && \
  cloudflared tunnel token '$NEW_TOKEN' --cred-file /home/ecs-agent/snc-poc/.cloudflared/cred.json"
```

> ℹ️ วิธีที่แน่นอนขึ้นกับวิธี deploy (ดูหมายเหตุท้าย) — ตรวจว่าค่าใน `cred.json` ตรงกับ tunnel ID

### Step 4: ตรวจ config ว่า Service URL ยังเป็น `localhost` (ไม่ใช่ IP วงแลน)

```bash
ssh pi4 "cat /home/ecs-agent/snc-poc/.cloudflared/config.yml | grep -A2 'service:'"
```

ต้องเห็น `http://localhost:8000` หรือ `http://127.0.0.1:8000` — **ห้ามเป็น `192.168.1.x`**

### Step 5: Restart cloudflared + ตรวจสอบ

```bash
ssh pi4 "sudo systemctl restart cloudflared && \
  sleep 10 && systemctl is-active cloudflared"
```

### Step 6: ทดสอบผ่านโดเมนสาธารณะ

```bash
curl -I https://snc.nithep.com/dashboard-status.html
```

> **เกณฑ์ผ่าน:** `HTTP/2 200` (ไม่ใช่ 502/504)

```bash
curl -H "X-API-Key: [SNC_API_KEY]" https://snc.nithep.com/api/events
```

---

## 🔄 ขั้นตอน rotate (กรณีใช้ token file แบบ Local Tunnel)

ถ้าใช้ local tunnel (run `cloudflared tunnel run` จาก config):

```bash
ssh pi4 "cd /home/ecs-agent/snc-poc && \
  cloudflared tunnel login   # ใหม่ — ได้ cert.pem ใหม่ \
  cloudflared tunnel create snc-tunnel 2>/dev/null || true"
```

แล้วอัปเดต `config.yml` ให้ชี้ไปที่ tunnel ID ใหม่ + restart (Step 5-6 เดิม)

---

## ✅ Checklist หลัง rotate

- [ ] token เก่าถูก Regenerate/Revoke แล้ว (ฝั่ง Zero Trust)
- [ ] `cred.json`/`cert.pem` ใหม่บน Pi4 (chmod 600)
- [ ] config Service URL เป็น `localhost` (ไม่ใช่ IP วงแลน)
- [ ] `cloudflared` active + อุโมงค์เชื่อมถึง
- [ ] `curl -I` → `HTTP/2 200` (ไม่ใช่ 502)
- [ ] API ผ่านอุโมงค์ตอบถูกต้อง (X-API-Key)
- [ ] ไม่มี credentials เก่าหลงเหลือใน repo/เอกสาร (grep ตรวจ)

---

## ↩️ Rollback (ถ้าจำเป็น)

```bash
ssh pi4 "cd /home/ecs-agent/snc-poc && \
  rm -rf .cloudflared && cp -r backups/cloudflared.<ts> .cloudflared && \
  sudo systemctl restart cloudflared"
```

> ⚠️ หมายเหตุ: token เก่าที่ Regenerate แล้วใช้ไม่ได้ — rollback ต้อง restore credential file เก่าก่อน revoke (จึงต้อง backup ใน Step 1 ก่อนเสมอ)

---

*จัดทำโดย: Senior Software Engineer — 19 ส.ค. 2569*

---
title: "ADR 0009 — แยก OpenCode Agent เป็น headless service + Cloudflare Tunnel เฉพาะกิจ"
type: adr
tags: [architecture, opencode, tunnel, pi4]
---

# ADR 0009 — แยก OpenCode Agent เป็น headless service + Cloudflare Tunnel เฉพาะกิจ

- สถานะ: **Accepted**
- วันที่: 2026-08-20

## บริบท
ต้องการให้ทีมสามารถรัน **OpenCode coding agent** บน Raspberry Pi 4 (192.168.1.94, user `ecs-agent`)
ได้จากระยะไกลอย่างปลอดภัย เพื่อใช้งานเป็น agent ช่วยพัฒนาโปรเจกต์ SNC เอง
โดยไม่ไปแทรกแซงระบบ production ที่มีอยู่ (backend `snc.nithep.com` และ tunnel `hotel-ecs` ของระบบโรงแรม)

ข้อจำกัดที่พบระหว่างลงมือ:
- `cloudflared` CLI ไม่รองรับการสร้าง Cloudflare Access Application หรือการลบ DNS record → ต้องใช้ Cloudflare API Token หรือ Dashboard
- ใบรับรอง Universal SSL ของโซน `nithep.com` ครอบคลุมได้แค่ 1 ระดับ (`*.nithep.com`) จึงไม่สามารถใช้ subdomain 2 ระดับได้

## การตัดสินใจ
1. รัน OpenCode แบบ **headless** ด้วย `opencode serve --port 4096 --hostname 0.0.0.0`
   เป็น systemd service แยกชื่อ `snc-opencode` (WorkingDirectory `~/snc`, user `ecs-agent`)
2. พิทักษ์รหัสผ่านผ่าน env var `OPENCODE_SERVER_PASSWORD` (HTTP Basic Auth, user `opencode`)
   เก็บคู่กับ `OPENROUTER_API_KEY` ในไฟล์ `~/.config/opencode/opencode.env` (chmod 600, `EnvironmentFile=`)
3. สร้าง **Cloudflare Tunnel แยกต่างหาก** ชื่อ `snc-opencode` (ID `72cb8359-9a5e-437a-b88d-abfac71ae292`)
   ไม่แตะ tunnel `hotel-ecs` ของเดิม
4. ใช้ hostname **`snc-opencode.nithep.com`** (single-level subdomain) เพื่อให้อยู่ในขอบเขต `*.nithep.com`
   ชี้ ingress ไป `http://localhost:4096`
5. รัน tunnel ด้วย systemd service `snc-cloudflared` (`--no-autoupdate`, `--config /etc/cloudflared/config-snc-opencode.yml`)
6. ตั้ง Cloudflare Access (Zero Trust) ครอบ hostname นี้เป็นชั้น 2
   - **สถานะ 2026-08-20**: สร้าง Access Application แล้ว (Service = `snc-opencode.nithep.com`, Type = Published, Description = `http://localhost:4096`, Additional settings = Using defaults) — domain ถูกต้อง
   - **ยังไม่เปิด Login method** (Settings → Authentication → Login methods ยังไม่มี One-time PIN/Google) จึงยังไม่มีฟอร์มล็อกอิน → Access ยังไม่สามารถใช้งานได้จริง (browser ได้หน้า "Welcome to Cloudflare Zero Trust" ทั่วไป)
   - **เลื่อน (deferred)**: ทีมตัดสินใจพึ่งพา HTTP Basic Auth รหัสสุ่ม 32 ตัว + Cloudflare TLS/DDoS ไปก่อนในระยะ PoC
   - **Todo เมื่อว่าง**: เปิด One-time PIN (1 คลิก) เพื่อปิดช่องโหว่ `/config/providers` ที่พ่น OpenRouter key — ดู wiki guide

## ผลกระทบ
- OpenCode เข้าถึงได้จากภายนอกผ่าน `https://snc-opencode.nithep.com` (TLS 1.3, zero open port)
- Service ทั้งสอง (`snc-opencode`, `snc-cloudflared`) เปิดอัตโนมัติหลัง reboot
- ต้องรักษาความลับไฟล์ `.env` (chmod 600) และหมุนรหัสผ่านสม่ำเสมอ
- Endpoint `/config/providers` ของ opencode **คืนค่า OpenRouter API key กลางจอ** → จึงต้องพึ่ง Basic Auth + (แนะนำ) Cloudflare Access อย่างเข้มงวด มิฉะนั้นผู้รู้รหัสจะดึง key ได้

## ช่องโหว่ที่ทราบและเลื่อนการแก้ (Known Gap — Deferred)
- **การพิทักษ์ชั้นเดียว (Basic Auth เท่านั้น)**: หากรหัส `OPENCODE_SERVER_PASSWORD` รั่ว ผู้ได้รหัสจะเข้า opencode ได้และอ่าน OpenRouter key จาก `/config/providers`
- ** mitigation ชั่วคราวที่พอใช้ได้**: รหัสเป็นสุ่ม 32 ตัว + อยู่หลัง Cloudflare (TLS 1.3, WAF, DDoS) → brute-force ในทางปฏิบัติทำไม่ได้
- **เป้าหมายระยะยาว**: เปิด Cloudflare Access + One-time PIN (หรือ IdP อื่น) เป็นชั้น 2 เพื่อเพิ่ม 2FA ให้ endpoint ที่พ่น key
- **คำเตือน**: ห้าม commit รหัสผ่านหรือ API key ลง git — เก็บเฉพาะใน `~/.config/opencode/opencode.env` (chmod 600) บน Pi4

## ทางเลือก (Alternatives)
- **TUI ภายใต้ tmux/screen**: ปัดตก เพราะไม่สามารถเข้าถึงเป็น HTTP/server ได้ และไม่รันเป็น service ที่จัดการเองได้
- **นำ route `opencode.snc.nithep.com` ไปไว้ใน tunnel เดิม `hotel-ecs`**: ปัดตก ผิดหลักแยก SNC/Hotel-ECS ตาม ADR 0007 และจะไปแตะ production route เดิม
- **ใช้ `opencode.snc.nithep.com` (2 ระดับ)**: ปัดตก เพราะไม่อยู่ใน `*.nithep.com` Universal SSL → Cloudflare ไม่มี cert ให้ → TLS handshake failure (พิสูจน์แล้วระหว่างลงมือ)
- **รวม opencode เข้า `snc.nithep.com` เส้นทางเดิม**: ปัดตก เพราะผสม agent เข้ากับ backend production

## ADR ที่เกี่ยวข้อง
- `0007` แยก nomenclature SNC / Hotel-ECS — ต้นทางของการไม่แตะ `hotel-ecs`
- `0008` system topology — สถาปัตย์ Pi4 + Cloudflare Tunnel ภาพรวม
- `wiki/SNC_OPENCODE_SETUP_GUIDE.md` — วิธีลงมือ (operational step-by-step)

## บันทึกเหตุการณ์ (Incident Log)

### 2026-08-20 — Public `https://snc-opencode.nithep.com` ขึ้น Cloudflare Error 1033 (Ray ID a2e1ae391f71f8cc)
- **อาการ**: เปิดเว็บผ่าน Tunnel ได้หน้า `Error 1033` (origin/tunnel ไม่ผ่านการรับรอง)
- **สาเหตุที่แท้จริง**: cloudflared ต่อทะเบียน Tunnel ไม่สำเร็จด้วยข้อความ
  `ERR Register tunnel error from server side error="Unauthorized: Invalid tunnel secret"`
  ไฟล์ `credentials` (`/home/ecs-agent/.cloudflared/72cb8359-…-abfac71ae292.json`)
  เก็บ `TunnelSecret` ที่ล้าสมัย/ไม่ตรงกับฝั่ง Cloudflare แม้ Tunnel ID จะยังมีอยู่ครบ
  (พบว่า `tunnel list` แสดง `snc-opencode` ด้วย 0 connections)
  — นอกจากนี้พบไฟล์ `cert.pem` ถูกเขียนทับเป็น **Argo Tunnel Token**
  (`-----BEGIN ARGO TUNNEL TOKEN-----`) แทนใบรับรองบัญชี (282 bytes, เล็กกว่าปกติ ~1.6KB)
  แต่ยังโชคดีที่ `cloudflared tunnel token` ทำงานได้ (API auth ผ่านได้)
- **การแก้ไข (บน Pi4 192.168.1.94, user ecs-agent)**:
  1. สร้างไฟล์ `credentials` ใหม่จาก token ที่ถูกต้อง:
     `cloudflared tunnel token snc-opencode` → ถอดรหัส JSON (`a`=AccountTag, `s`=TunnelSecret, `t`=TunnelID)
     เขียนลง `credentials` JSON ด้วยฟิลด์ `AccountTag` / `TunnelID` / `TunnelSecret`
  2. `chmod 600` ไฟล์ credentials
  3. ฆ่า cloudflared ตัวโยง (stray `PID 1628` ที่รัน `cloudflared tunnel run` โดยไม่มี `--config`)
  4. `sudo systemctl restart snc-cloudflared.service`
- **ผลลัพธ์การตรวจสอบ**:
  - `cloudflared tunnel list` แสดง `snc-opencode` มี connections แล้ว (`2xbkk02, 1xsin02, 1xsin13`)
  - Log ไม่มี `Invalid tunnel secret` ซ้ำ
  - ทดสอบผ่าน `curl https://snc-opencode.nithep.com/` ได้ **HTTP 401** (Tunnel ต่อถึง opencode แล้ว
    และ opencode เรียก Basic Auth ตามปกติ) — ไม่ใช่ Error 1033  again
- **บทเรียน / ข้อควรป้องกัน**:
  - ห้ามนำ Argo Tunnel Token ไปเขียนทับ `cert.pem` (ให้แยกไฟล์ต่างหาก)
  - หากพบ `Invalid tunnel secret` ให้ต่ออายุ secret ด้วย `cloudflared tunnel token <name>`
    แล้วเขียนลง credentials file ใหม่ (เวอร์ชัน cloudflared ที่ติดตั้งไม่มีคำสั่ง `tunnel inherit`)
  - ตรวจสอบไม่ให้มี cloudflared หลายกระบวนการรันทับกันโดยไม่มี `--config`

## กรณีศึกษา: ไฟฟ้าดับ (ไม่มี UPS) และการฟื้นตัวอัตโนมัติบน Pi4

### บริบท
- สถานที่ไม่มี **UPS** ครอบทุกระบบ → หากไฟฟ้าดับ ทุกเครื่อง (รวมถึง Pi4 `192.168.1.94`) จะถูกตัดการทำงานทันที
- เป้าหมาย: เมื่อไฟฟ้ากลับมา Pi4 ต้อง **เปิดและฟื้นระบบทั้งหมดเองได้อัตโนมัติ** โดยไม่ต้องคนเข้าไปแตะเครื่อง — เหมือนกับระบบ SNC หลักที่ออกแบบมา "แข็งแรงมาก" (self-healing ผ่าน systemd)

### ทำไม SNC (และ opencode tunnel) ถึงฟื้นเองได้
ทุก service ถูกตั้งเป็น `enabled` + มีนโยบายเริ่มใหม่อัตโนมัติ:
- `snc-opencode.service` — `Restart=on-failure` → คืนชีพ opencode (`:4096`) เอง
- `snc-cloudflared.service` — `Restart=` + `WantedBy=multi-user.target` → คืนชีพ Tunnel เอง
- ระบบหลัก `snc.nithep.com` (backend `:8000`, PBX listener) ก็ใช้กลไกเดียวกัน
- เมื่อ Pi4 บูตเสร็จ systemd จะเรียก service ทุกตัวที่ `enabled` กลับมาทำงาน → ปกติแค่นี้ก็กลับมาใช้งานได้เลย

### เหตุการณ์ 2026-08-20 (ไฟฟ้าดับ → Error 1033)
1. ไฟฟ้าดับ → Pi4 ปิดฉุบับ → ทุก service หยุดทำงาน
2. ไฟฟ้ากลับ → Pi4 บูต → systemd เรียก `snc-opencode` + `snc-cloudflared` กลับมา **โดยอัตโนมัติ**
3. ปรากฏการณ์: เว็บ `https://snc-opencode.nithep.com` ขึ้น **Cloudflare Error 1033**
4. สาเหตุร่วม: ปกติฟื้นเองได้ แต่วาระนี้ Tunnel เจอ `Invalid tunnel secret` (credentials เดิมล้า)
   → จึงไม่ใช่ความล้มเหลวของการออกแบบฟื้นเอง แตเป็น "จิ๊กซอว์ secret" ที่ไปปรากฏตอนรีบูต
5. การแก้ไข (ดู Incident Log ด้านบน): สร้างไฟล์ `credentials` ใหม่จาก `cloudflared tunnel token`
   → หลังแก้ Tunnel ต่อคล่องและกลับมา 401 ตามปกติ

### บทสรุป (สำหรับอธิบายง่ายๆ)
- **ไฟดับ = ทุกเครื่องหลับไปพร้อมกัน** (เพราะไม่มี UPS ประคอง)
- **ไฟมา = Pi4 ตื่นและเปิด service ทุกตัวเอง** (systemd จัดการ) → นี่คือความ "แข็งแรง" ของ SNC
- คราวนี้มีอาการ 1033 เพราะตอนตื่นมาเจอ **รหัสผ่าน Tunnel เก่า (stale secret)** ไม่ใช่เพราะระบบพัง
- แก้แค่ "ทำกุญแจใหม่ให้ Tunnel" (`tunnel token` → เขียน credentials) จบ แล้วกลับมาปกติเหมือนเดิม
- ข้อเสนอแนะป้องกันซ้ำ: ติด **UPS** ให้ Pi4 (กันไฟกระชาก/ดับสั้นๆ) และ/หรือตั้ง cron ตรวจสอบ Tunnel
  ทุกเช้าว่ามี connections หรือไม่ (ถ้า 0 → รันสคริปต์ต่ออายุ secret อัตโนมัติ)
- **นำไปปฏิบัติแล้ว**: สร้าง `ops/tunnel-self-heal.sh` — ตรวจ connections ทุก 15 นาที ผ่าน cron ของ `ecs-agent`
  ถ้า 0 จะรัน `cloudflared tunnel token` → เขียน `credentials` ใหม่ → `sudo systemctl restart snc-cloudflared.service`
  (ecs-agent ได้รับ NOPASSWD สำหรับ restart เฉพาะ service นี้ใน `/etc/sudoers.d/snc-tunnel`)
  ทดสอบมืออาชีพแล้ว: ตรวจพบ connections ปกติและจบเงียบ (exit 0)

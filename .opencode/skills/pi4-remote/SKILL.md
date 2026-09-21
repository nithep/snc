---
name: pi4-remote
description: >
  Guardrail for any work touching Raspberry Pi 4 edge (192.168.1.94, ssh pi4,
  ecs-agent, /home/ecs-agent/snc) or multi-machine workflow (git clone snc,
  deploy from another computer). Forces reading ops/CAUTIONS_MULTIMACHINE.md
  and ops/SETUP_MULTIMACHINE.md before scp, ssh, systemctl, DB, or secret work.
  Use when user mentions pi4, 192.168.1.94, ecs-agent, remote ssh, deploy-snc,
  multi-machine, MateBook, or works from a non-Pi machine.
user-invocable: false
when-to-use: >
  pi4, 192.168.1.94, ssh pi4, ecs-agent, remote work, multi-machine,
  deploy-snc-one-shot, MateBook, another computer, cautions before Pi work
---

# Pi4 Remote Guardrail — อ่านก่อนแตะ Pi4 ทุกครั้ง

**Role:** Edge safety gate. ทำงานคู่กับ `snc` skill (snc = ตัวระบบ, skill นี้ = วิธีแตะ Pi อย่างปลอดภัยจากหลายเครื่อง)

## 0. บังคับอ่าน (2 ไฟล์นี้ก่อนเสมอ)

1. `ops/CAUTIONS_MULTIMACHINE.md` — ข้อห้าม (secret, drift, DB, network)
2. `ops/SETUP_MULTIMACHINE.md` — วิธี clone + ssh + deploy ที่ถูกต้อง

ถ้ายังไม่อ่าน 2 ไฟล์นี้ ห้ามสั่ง `ssh / scp / systemctl / sqlite3` เด็ดขาด

## 1. Source of truth

- GitHub (`nithep/landing, nithep/portal, nithep/snc, nithep/cctv`) คือตัวกลาง
- Pi4 (`/home/ecs-agent/snc`) คือตัวรัน ไม่ใช่ที่เก็บหลัก
- เริ่มงาน: `git pull --rebase` เสมอ จบงาน: `git push` + checklist ใน CAUTIONS §5

## 2. ห้ามทำ (Hard block)

1. ห้าม `scp -r` ทับ Pi — ใช้ `ops/deploy-snc-one-shot.sh` เท่านั้น (มี drift check + backup + md5 + health verify)
2. ห้ามรัน `landing/portal` บน Pi — landing = Cloudflare Pages, portal = Cloud Run (แยกตาม README เดิม)
3. ห้ามใส่ `cctv` (yolov8n.pt prototype) เป็น autostart — กันแย่ง CPU/RAM กับ `snc-backend` (critical path)
4. ห้ามแตะ `nurse_call_events.db` ตรงๆ — backup ด้วย `ops/backup-snc-db.sh` ก่อน
5. ห้าม commit `.env / *.pem / *service-account*.json / *credentials*.json` — key แจกเป็น env ต่อเครื่อง (`chmod 600`) หมุนตาม `doc/wiki/SNC_API_KEY_ROTATION_GUIDE.md`
6. ห้ามเปิด port 22 ออกเน็ต — นอก LAN ต้องผ่าน Tailscale / Cloudflare Tunnel
7. ห้ามใช้ LAN IP ใน Cloudflare ingress — ใช้ `localhost` (กัน 502 จาก DHCP drift)

## 3. Preflight ก่อน ssh/deploy (รันจากเครื่อง dev)

```bash
git status --short --branch   # ต้อง clean หรือรู้ว่า dirty อะไร
ssh pi4 "echo OK; sudo -n true && echo sudo-OK"
./ops/deploy-snc-one-shot.sh --dry-run
```

## 4. Post-verify หลังแตะ Pi (ห้ามปิดงานถ้าไม่ผ่าน)

```bash
curl -s http://localhost:8000/health
sudo systemctl status snc-backend snc-pbx-listener --no-pager
```

## 5. PBX context (กันแก้ผิด)

- PBX จริง `192.168.1.91:23` เจอเฉพาะใน LAN — เครื่องนอก LAN ให้ dev ด้วย mock (`ops/mock-floor11-data.py`) ห้ามแก้ IP จริงในโค้ด
- ตู้รับ telnet ได้ session เดียว — listener ถือ `:23` ไว้ ให้ PC อื่นใช้ proxy `:2323` (ดู `snc` skill STEP 4)

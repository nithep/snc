# SETUP_MULTIMACHINE — ทำงานหลายเครื่องโดยไม่ต้องเปิด MateBook

> หลักการ: GitHub เป็นตัวกลาง, Pi4 (192.168.1.94) เป็นตัวรัน SNC เท่านั้น
> `landing` → Cloudflare Pages, `portal` → Cloud Run, `snc/cctv` → Pi4
> ห้ามยุบ landing/portal เข้า snc (คนละ deploy target + security boundary)

> **Tailscale ยกเลิกแล้ว (2026-09-28)** — Pi กับ MateBook logged out + service disabled แล้ว
> `ssh pi4` ใช้ได้เฉพาะใน LAN (หรือผ่าน WireGuard tunnel → `10.0.0.1`); นอก LAN ใช้ web terminal ที่ `https://snc-opencode.nithep.com` (Basic auth, รันในฐานะ ecs-agent) — ไม่ใช่ SSH เต็มรูปแบบ; งานยาวรันใน `tmux` (ติดตั้งบน Pi แล้ว 2026-09-28) กัน browser หลุดแล้ว process ตาย
> rollback Pi: `sudo systemctl enable --now tailscaled && sudo tailscale up`; MateBook: `sc config Tailscale start= auto` + `tailscale up`

## 1. สถานะปัจจุบัน (ตรวจ 2026-09-21 บน MateBook)

| repo | remote | branch | สถานะ |
|---|---|---|---|
| `landing` | `github.com/nithep/landing.git` | `main` | clean, ตรง origin |
| `portal` | `github.com/nithep/portal.git` | `main` | clean, ตรง origin |
| `snc` | `github.com/nithep/snc.git` | `main` | clean, ตรง origin |
| `cctv` | `github.com/nithep/cctv.git` | `master` | **dirty (8 ไฟล์)** — commit/push ก่อนย้ายเครื่อง |

```bash
# บน MateBook — เคลียร์ cctv ก่อน
cd D:\nithep-platform\cctv
git add -A && git commit -m "chore: sync prototype notes" && git push origin master
```

## 2. เครื่องใหม่ (คอมเครื่องอื่น) — เริ่มงาน

```bash
# 1) clone ทั้ง 4 ตัว (หรือเฉพาะตัวที่จะทำ)
git clone https://github.com/nithep/landing.git
git clone https://github.com/nithep/portal.git
git clone https://github.com/nithep/snc.git
git clone https://github.com/nithep/cctv.git
```

```bash
# 2) ตั้ง SSH alias ไป Pi (ใช้ครั้งเดียวต่อเครื่อง)
# ~/.ssh/config
Host pi4
  HostName 192.168.1.94
  User ecs-agent
```

```bash
# 3) ก็อป key ขึ้น Pi (จะได้ไม่ต้องใส่รหัส + deploy script ใช้ BatchMode)
ssh-copy-id ecs-agent@192.168.1.94
ssh pi4 "echo OK; sudo -n true && echo sudo-OK"
```

## 3. วิธีทำงานประจำวัน

```bash
# dev บนเครื่องไหนก็ได้ → push ขึ้น GitHub เสมอ
git pull --rebase
# ... แก้ไข ...
git add -A && git commit -m "..." && git push
```

```bash
# deploy SNC ขึ้น Pi (รันจากเครื่องไหนก็ได้ใน LAN)
cd snc
./ops/deploy-snc-one-shot.sh
# หรือจำลองก่อน: ./ops/deploy-snc-one-shot.sh --dry-run
```

```bash
# แก้หน้างานบน Pi โดยตรง (ผ่าน VSCode Remote-SSH)
ssh pi4
cd ~/snc  # หรือ /home/ecs-agent/snc (ดูค่า SNC_ROOT ใน deploy script)
curl -s http://localhost:8000/health
sudo systemctl status snc-backend snc-pbx-listener --no-pager
```

## 4. กฎกันงานทับกัน

1. ห้าม `scp` โฟลเดอร์ดิบทับ Pi ตรงๆ — ใช้ `deploy-snc-one-shot.sh` (มี drift check + backup + md5 verify)
2. `node_modules/`, `.venv/`, `*.db`, `.env` ไม่ต้อง commit — `npm install` / สร้าง `.env` ใหม่บนแต่ละเครื่อง
3. `Pass-Key.txt` ใน nithep-platform ห้ามเข้า git, ห้ามวางบน Pi แบบ plaintext
4. `cctv` เป็น prototype — รัน manual เท่านั้น ห้ามใส่ autostart ทับ SNC (critical path)
5. นอกบ้าน (ไม่อยู่ LAN 192.168.1.x) — `ssh` ใช้ไม่ได้ (Tailscale ยกเลิก 2026-09-28) ให้ (ก) เข้า LAN/WireGuard แล้ว ssh เต็มรูปแบบ หรือ (ข) ใช้ web terminal `https://snc-opencode.nithep.com` (Basic auth) สำหรับแก้โค้ด/รัน agent ห้ามเปิด port 22 ออกเน็ตตรงๆ

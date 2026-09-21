# ข้อควรระวัง — ทำงานหลายเครื่อง (git clone + ssh pi4)

> ขอบเขต: `git clone https://github.com/nithep/snc.git` แล้ว `ssh ecs-agent@192.168.1.94`
> อ่านคู่กับ `SETUP_MULTIMACHINE.md` (วิธีทำ) — ไฟล์นี้คือสิ่งที่ห้ามพลาด

## 1. Secret / Key — ห้ามหลุดเด็ดขาด

1. ห้าม commit `.env`, `*.pem`, `*service-account*.json`, `*credentials*.json` ขึ้น GitHub
2. `Pass-Key.txt` ที่อยู่บน MateBook ห้ามเข้า git ห้าม scp ขึ้น Pi แบบ plaintext — กรอกเป็น env บนแต่ละเครื่องแล้ว `chmod 600`
3. คอมเครื่องใหม่ต้องขอ key ใหม่ (SNC_API_KEY, Telegram token, Cloudflare) แล้วทำตาม `doc/wiki/SNC_API_KEY_ROTATION_GUIDE.md` — ห้ามก็อปไฟล์ key เก่าแจกกัน
4. ก่อน push ทุกครั้งรัน `git status --ignored` ตรวจว่าไม่มีไฟล์ควร track โดน ignore เงียบ

## 2. กันงานทับกัน (Drift)

1. เริ่มงานทุกครั้งด้วย `git pull --rebase` — Pi กับ MateBook ไม่ใช่ source of truth, GitHub คือตัวกลาง
2. ห้ามแก้ไฟล์ตรงบน Pi แล้วลืม commit กลับ — `deploy-snc-one-shot.sh` มี drift check ถ้าขึ้นเตือนให้หยุดแล้ว `diff` ก่อน
3. ห้าม `scp -r` ทับทั้งโฟลเดอร์ — ใช้ deploy script เท่านั้น (มี backup + md5 verify + restart + health check)
4. ทำงานพร้อมกัน 2 คนให้แยก branch — ห้าม push ตรง `main` ชนกันโดยไม่ pull ก่อน

## 3. Pi4 — ข้อจำกัด Edge

1. ห้ามรัน `landing/portal` บน Pi — `landing` อยู่ Cloudflare Pages, `portal` อยู่ Cloud Run (แยกตาม README เดิม)
2. `cctv` เป็น prototype (มี `yolov8n.pt` หนักเครื่อง) — รัน manual เท่านั้น ห้ามใส่ `systemd autostart` เด็ดขาด กันแย่ง CPU/RAM กับ `snc-backend`
3. ห้ามลบ/เขียนทับ `nurse_call_events.db` (SQLite WAL) บน Pi — backup ด้วย `ops/backup-snc-db.sh` ก่อนแตะทุกครั้ง
4. PBX จริงอยู่ที่ `192.168.1.91:23` — เครื่องใหม่ที่ไม่ได้อยู่ LAN เดียวกันจะ listener ไม่เจอ ถือว่าปกติ ให้ dev ด้วย mock (`ops/mock-floor11-data.py`) อย่าแก้ IP จริงในโค้ด
5. Pi บูตจาก SD เสื่อมง่าย — งานเขียนถี่ๆ (log/output) อย่าเปิด debug ค้างไว้ ดู log ด้วย `journalctl` แบบ `--no-pager` และ `view-logs.sh`

## 4. Network / SSH

1. `ssh ecs-agent@192.168.1.94` ใช้ได้เฉพาะใน LAN — นอกบ้านต้องผ่าน Tailscale/Cloudflare Tunnel ก่อน ห้าม forward port 22 ออกเน็ตตรงๆ
2. deploy script ต้องใช้ key แบบไม่ใส่รหัส (`BatchMode=yes`) + `sudo -n` แบบไม่ใส่รหัส — ถ้าเครื่องใหม่ยังใส่รหัสอยู่ให้แก้ `~/.ssh/config` + `ssh-copy-id` ก่อน อย่าแก้ script ไปใช้รหัส
3. หลัง deploy ทุกครั้งต้อง `curl -s http://localhost:8000/health` + `systemctl status snc-backend snc-pbx-listener` — health ไม่ OK ห้ามปิดเครื่องหนี

## 5. Checklist ก่อนปิดงานจากเครื่องอื่น

- [ ] `git push` แล้ว? (`git status` ต้อง clean)
- [ ] ถ้าแก้บน Pi ตรง — sync กลับเข้า git แล้วหรือยัง?
- [ ] `/health` OK? services `active`?
- [ ] ถ้าแตะ secret — เขียน rotation guide / แจ้งคนอื่นหรือยัง?

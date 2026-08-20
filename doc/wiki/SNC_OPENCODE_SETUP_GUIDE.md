# SNC OpenCode Setup Guide — Pi4 (aarch64)

คู่มือลงมือติดตั้ง OpenCode coding agent บน Raspberry Pi 4 ให้รันเป็น headless server
และเปิดผ่าน Cloudflare Tunnel แยกต่างหาก (`snc-opencode.nithep.com`)

> อัปเดตล่าสุด: 2026-08-20 — ดู ADR 0009 ประกอบ

## สถาปัตย์ภาพรวม
```
คุณ (เบราว์เซอร์/agent client)
   │ HTTPS + Basic Auth (opencode:******)  + แนะนำ Cloudflare Access
   ▼
Cloudflare Tunnel snc-opencode  (outbound, zero open port)
   ▼
Pi4 192.168.1.94  ── snc-cloudflared.service ──► localhost:4096
                                      ▲
                              snc-opencode.service
                       (opencode serve --port 4096 --hostname 0.0.0.0)
```

## 1. ติดตั้ง OpenCode (aarch64)
```bash
curl -fsSL https://opencode.ai/install | bash
# ติดตั้งที่ ~/.opencode/bin/opencode  เพิ่ม PATH ใน .bashrc อัตโนมัติ
```

## 2. ไฟล์ลับ `.env` (chmod 600)
`~/.config/opencode/opencode.env`
```
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxx
OPENCODE_SERVER_PASSWORD=<รหัสแข็งแกร่ง>
```
- ห้าม commit ไฟล์นี้ (ดู AGENTS.md กฎ .gitignore)
- หมุนรหัสผ่านได้ด้วย:
  ```bash
  NEW=$(openssl rand -hex 18)
  sed -i "s|^OPENCODE_SERVER_PASSWORD=.*|OPENCODE_SERVER_PASSWORD=$NEW|" ~/.config/opencode/opencode.env
  chmod 600 ~/.config/opencode/opencode.env
  sudo systemctl restart snc-opencode.service
  ```

## 3. systemd `snc-opencode.service`
```ini
[Unit]
Description=SNC OpenCode Server (headless HTTP)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ecs-agent
Group=ecs-agent
WorkingDirectory=/home/ecs-agent/snc
EnvironmentFile=/home/ecs-agent/.config/opencode/opencode.env
ExecStart=/home/ecs-agent/.opencode/bin/opencode serve --port 4096 --hostname 0.0.0.0
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now snc-opencode.service
```

## 4. Cloudflare Tunnel (แยกจาก `hotel-ecs`)
```bash
# ติดตั้ง cloudflared (aarch64)
curl -fsSL -o /tmp/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64
sudo mv /tmp/cloudflared /usr/local/bin/cloudflared && sudo chmod +x /usr/local/bin/cloudflared

# authenticate (เปิด URL ในเบราว์เซอร์ เลือกโดเมน nithep.com)
cloudflared tunnel login

# สร้าง tunnel แยก
cloudflared tunnel create snc-opencode
# → ได้ ID 72cb8359-9a5e-437a-b88d-abfac71ae292  และ credentials ใน ~/.cloudflared/<id>.json

# config: /etc/cloudflared/config-snc-opencode.yml
# ⚠ ใช้ HOSTNAME ระดับเดียวเท่านั้น (snc-opencode.nithep.com) เพราะ Universal SSL *.nithep.com ครอบได้แค่ 1 ระดับ
tunnel: 72cb8359-9a5e-437a-b88d-abfac71ae292
credentials-file: /home/ecs-agent/.cloudflared/72cb8359-9a5e-437a-b88d-abfac71ae292.json
ingress:
  - hostname: snc-opencode.nithep.com
    service: http://localhost:4096
  - service: http_status:404

# ตั้ง DNS CNAME
cloudflared tunnel route dns snc-opencode snc-opencode.nithep.com

# systemd snc-cloudflared.service
# ExecStart=/usr/local/bin/cloudflared --no-autoupdate tunnel --config /etc/cloudflared/config-snc-opencode.yml run
sudo systemctl daemon-reload
sudo systemctl enable --now snc-cloudflared.service
```

## 5. ตรวจสอบ
```bash
curl -s -u opencode:<PASSWORD> https://snc-opencode.nithep.com/global/health
# → {"healthy":true,"version":"1.18.18"}
```

## 6. ความปลอดภัย (สำคัญ)
- **ตั้ง Cloudflare Access (Zero Trust)** ครอบ `snc-opencode.nithep.com` เป็นชั้น 2
  (อีเมล / One-time PIN) — ทำผ่าน Cloudflare Dashboard หรือ Cloudflare API (ต้องมี API Token)
- Endpoint `/config/providers` ของ opencode **คืนค่า OpenRouter API key** → ห้ามเปิดโล่ง
  ต้องมี Basic Auth + Access อย่างเข้มงวด
- หมุน `OPENCODE_SERVER_PASSWORD` สม่ำเสมอ (ดูข้อ 2)
- cloudflared CLI **ไม่สามารถ** สร้าง Access App หรือลบ DNS record → ใช้ Dashboard/API Token

## 7. การแก้ปัญหา
| อาการ | สาเหตุ | แก้ไข |
|---|---|---|
| TLS handshake failure (no cert) | ใช้ subdomain 2 ระดับ (เช่น `opencode.snc.nithep.com`) | เปลี่ยนเป็น 1 ระดับ (`snc-opencode.nithep.com`) |
| 502 จาก Cloudflare | origin ยังไม่ฟังพอร์ตหลัง restart | รอสักครู่แล้วทดสอบใหม่ |
| health ตอบแต่ local ไม่ตอบ public | tunnel หลุด | `sudo systemctl restart snc-cloudflared.service` |

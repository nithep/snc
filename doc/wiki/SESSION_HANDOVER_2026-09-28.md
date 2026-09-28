---
title: "SESSION_HANDOVER_2026-09-28 — Remote Access Cleanup"
type: handover
tags: [status, handover, pi4, remote-access, tailscale, wireguard]
---

# SESSION_HANDOVER_2026-09-28 — Remote Access Cleanup

> จัดทำ: 28 ก.ย. 2569 | ต่อจาก [[SESSION_HANDOVER_2026-09-18]]
> ครอบคลุม: ยกเลิก Tailscale, ยืนยัน remote access, ติดตั้ง tmux, ตรวจสถานะ WireGuard/Termius

## งานที่ทำและผลตรวจ

### Remote access
- Pi `hotel-gateway`: `tailscale logout` และ `systemctl disable --now tailscaled` ทำก่อนหน้า; ต่อมารัน `apt-get purge -y tailscale` สำเร็จ
- ตรวจหลัง purge: `dpkg-query` ไม่พบ package `tailscale`; `tailscaled.service` ไม่มีแล้ว
- MateBook: `tailscale logout` สำเร็จ; Windows service `Tailscale` disabled + stopped. Package บน MateBook ยังคงติดตั้ง
- Web terminal `https://snc-opencode.nithep.com`: public request ได้ HTTP 401 Basic challenge; ตรวจ `cloudflared_tunnel_total_requests` บน Pi เพิ่ม 745 → 746 หลังยิง URL จึงยืนยันว่า request ผ่าน public Cloudflare Tunnel มาถึง Pi
- Web terminal รันในฐานะ `ecs-agent`; เป็น shell/เว็บแอป ไม่ใช่ SSH เต็มรูปแบบ
- WireGuard `hotel-admin`: MateBook peer `10.0.0.3/32`, Pi `wg0` `10.0.0.1/24`, endpoint ใน config เป็น LAN `192.168.1.94:51820`; ใช้ได้เมื่อ route ถึง LAN endpoint ไม่ใช่ remote relay
- MateBook WireGuard GUI แสดง “out of date”; ไฟล์ติดตั้งรายงาน version 1.1.1. `winget upgrade --id WireGuard.WireGuard` แจ้งว่าไม่มีรุ่นใหม่กว่าใน source ที่ตั้งไว้ จึงยังไม่ได้อัปเดต
- ติดตั้ง `tmux 3.5a` บน Pi; smoke test สร้าง/แสดง/ลบ session ผ่าน

### Git / docs
- Push docs เสร็จบน `origin/main`:
  - `e48567a` — Tailscale decommission notice
  - `2c8448d` — ระบุ web terminal เป็นช่องทางนอก LAN และ SSH เฉพาะ LAN/WireGuard
  - `68a5f7e` — บันทึกการติดตั้ง tmux
  - `5fb285f` — บันทึก purge package บน Pi
- Pi repo origin เป็น HTTPS; local MateBook `snc` repo origin ถูกเปลี่ยนเป็น `git@github.com:nithep/snc.git` เพื่อ push ผ่าน SSH

## ค้าง / ต้องทำโดยเจ้าของบัญชี
1. **Termius subscription:** ยังไม่ได้ยกเลิกหรือยืนยันสถานะ — ต้องเข้า Apple App Store, Google Play หรือ Termius account ตามช่องทางซื้อ
2. **Tailscale Android nodes:** `dby-w09` และ `gla-lx1` ยังไม่ได้ลบ; ต้องยืนยันตัวตน tailnet admin ใน Admin Console แล้วลบจาก Machines
3. ถ้าต้องการให้ WireGuard GUI หาย “out of date” ต้องตรวจ updater/installer จากช่องทางทางการ; Winget source ปัจจุบันไม่เสนอ upgrade
4. Tailscale package บน MateBook ยังติดตั้งอยู่ แต่ service disabled และเครื่อง logout แล้ว

## สถานะสรุป

| รายการ | สถานะ |
|---|---|
| Pi Tailscale | Purged; service หาย |
| MateBook Tailscale | Logged out; service disabled; package ยังอยู่ |
| Android Tailscale nodes | ยังอยู่ใน tailnet; รอ admin action |
| Web terminal | Public tunnel path ยืนยัน; Basic auth (HTTP 401 unauthenticated) |
| SSH | LAN/WireGuard path; port 22 ไม่เปิดสู่อินเทอร์เน็ต |
| WireGuard MateBook | 1.1.1; Winget แจ้งไม่มีรุ่นใหม่กว่า |
| tmux บน Pi | 3.5a; ติดตั้งและ smoke-tested |
| Termius subscription | ยังไม่ยืนยันการยกเลิก; รอเจ้าของบัญชี |

## อ้างอิง
- [[ops/SETUP_MULTIMACHINE]]
- [[ops/CAUTIONS_MULTIMACHINE]]
- [[SESSION_HANDOVER_2026-09-18]]

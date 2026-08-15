#!/bin/bash
# ตรวจทุก 5 นาที: ถ้าไม่มี TCP :23 ไปตู้ PBX -> บันทึกลง log
if ! ss -tn 2>/dev/null | grep -q '192.168.1.91:23'; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') PBX_DISCONNECTED (no TCP 192.168.1.91:23)" >> /home/ecs-agent/snc-poc/pbx_watchdog.log
fi

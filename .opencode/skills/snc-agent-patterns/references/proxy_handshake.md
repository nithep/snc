# TCP proxy handshake (`:2323`) — session reference
Used by Room Manager mirror when `:23` is held by listener.

Order (listener → client on connect): banner `Phonik PABX Telnet system\r\n..\r\n`
Then respond to PC commands:
- `..tcmd=` → `===tcmd=1`
- `..VERS=` → `===VERS=DX-COMPACT V5.4r1 (V5.1r0)`
- `..PASS=` → `===ACKW`
- `..EVNT=` → `===EVNT=END`
- `.` / `..` → `..`

Strip IAC/control bytes (`0xFF ...`) before matching. Broadcast raw SMDR lines (`\r\n`-terminated) to all connected clients (`broadcast_to_proxy_clients`).

Verify: `telnet <pi-ip> 2323` → send `..VERS=` → expect `===VERS=DX-COMPACT V5.4r1 (V5.1r0)`.

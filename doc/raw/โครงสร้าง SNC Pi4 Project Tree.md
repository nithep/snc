snc/
├── .github/workflows/          # CI/CD: release-installers.yml
├── .opencode/                  # OpenCode config
│
├── api/                        # 🔧 FastAPI Backend (snc-backend:8000)
│   ├── server.py               # Main FastAPI app
│   ├── storage.py              # SQLite (Pi4) / Firestore (Cloud) abstraction
│   ├── health_check.py         # Health check + diagnostics
│   ├── bridge_server.py        # Cloud Run bridge
│   ├── check_events.py         # Event inspector
│   ├── integration_test.py     # Integration tests
│   ├── services/
│   │   ├── gemini_direct_service.py  # Gemini AI summary
│   │   └── test_gemini_integration.py
│   ├── Dockerfile / Dockerfile.bridge
│   ├── cloudbuild.yaml / cloudbuild-bridge.yaml
│   ├── requirements.txt / requirements-bridge.txt
│   └── .env.example
│
├── app/                        # 🖥️ Frontend (Nurse Dashboard)
│   ├── index.html              # Main dashboard (i18n: TH/EN)
│   └── dashboard-status.html   # Status page
│
├── core/                       # 📦 Shared core modules
│   ├── approval.py
│   ├── download_service.py
│   └── route_registry.py
│
├── pbx/                        # 📞 PBX Listener (snc-pbx-listener)
│   ├── snc_pbx_listener.py     # Telnet SMDR parser
│   ├── event_outbox.py         # Outbox pattern (idempotency)
│   ├── debug_smdr_records.py
│   ├── test_event_outbox.py
│   ├── test_smdr_parser.py
│   └── .env.example
│
├── ops/                        # ⚙️ Operations & Scripts
│   ├── snc-backend.service     # systemd units
│   ├── snc-pbx-listener.service
│   ├── snc-cloudflared.service
│   ├── snc-tg-agent.service
│   ├── deploy-snc-one-shot.sh  # One-shot deploy to Pi4
│   ├── deploy-to-pi.bat        # Windows deploy script
│   ├── backup-snc-db.sh        # SQLite backup
│   ├── backup-offsite.sh       # Offsite backup
│   ├── burnin-monitor.sh       # Burn-in 48hr monitor
│   ├── burnin-reminder.sh
│   ├── pbx_watchdog.sh         # PBX watchdog
│   ├── monitor-snc-status.sh   # Status monitor
│   ├── nurse_call_serial_listener.py  # Edge serial listener
│   ├── snc_telegram_agent.py   # Telegram alerts
│   ├── terraform/              # IaC (GCP)
│   │   ├── main.tf / variables.tf / versions.tf
│   └── monitoring/             # Cloud monitoring setup
│
├── packaging/                  # 📦 Installer builder
│   └── build_installers.py     # .deb (Pi4), .msi (Windows)
│
├── surfaces/gui/               # 🖼️ GUI
│   └── service_portal.html
│
├── tests/                      # 🧪 Tests
│   └── test_architecture_layout.py
│
├── doc/                        # 📚 Documentation
│   ├── ARCHITECTURE_*.md       # Architecture diagrams & flow
│   ├── DEPLOYMENT_PI4.md       # Pi4 deployment guide
│   ├── DEPLOYMENT_CHECKLIST.md
│   ├── BLUEPRINT_5CORE.md      # 5-Core project blueprint
│   ├── adr/                    # Architecture Decision Records (7 ADRs)
│   ├── wiki/                   # Session handovers, guides, timeline
│   └── raw/                    # Raw analysis docs
│
├── AGENTS.md                   # Agent instructions
├── MIGRATION_RUNBOOK.md        # Migration runbook
├── README.md                   # Project overview
└── LICENSE
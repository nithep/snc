#!/usr/bin/env python3
"""
build_installers.py — Build real SNC installers/packaging for macOS, Windows, Pi OS
================================================================================
สร้าง installer artifacts ที่ใช้งานได้จริงสำหรับแต่ละ platform:

  macOS (ARM64 / Intel):
    - .app bundle (py2app) หรือ .zip portable
    - Homebrew formula (.rb)

  Windows (x64):
    - Inno Setup installer (.exe)
    - Portable .zip

  Raspberry Pi OS (ARM64):
    - .deb package (dpkg-deb)
    - Docker image (.tar)
    - systemd service files ( included )

วิธีใช้:
  python3 packaging/build_installers.py                    # build ทุก platform ที่ compile ได้
  python3 packaging/build_installers.py --platform pi      # build เฉพาะ Pi OS
  python3 packaging/build_installers.py --platform pi --version 1.1.0  # build + ระบุเวอร์ชัน (default 1.0.0)
  python3 packaging/build_installers.py --platform macos   # build เฉพาะ macOS
  python3 packaging/build_installers.py --platform windows # build เฉพาะ Windows (requires Inno Setup)
  python3 packaging/build_installers.py --list             # แสดง platform ที่ build ได้
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "packaging" / "dist"
DIST.mkdir(exist_ok=True)

VERSION = "1.0.0"
APP_NAME = "Smart Nurse Call"
APP_SLUG = "snc"
SNC_ROOT = "/home/ecs-agent/snc"


# ============================================================================
# Helpers
# ============================================================================

def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run command, raise on failure."""
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, cwd=str(ROOT), **kwargs)


def arch_tag() -> str:
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "arm64"
    elif machine in ("x86_64", "amd64"):
        return "x64"
    return machine


def write_file(path: Path, content: str, executable: bool = False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if executable:
        path.chmod(0o755)
    print(f"  ✅ {path.relative_to(ROOT)}")


# ============================================================================
# macOS Build
# ============================================================================

def build_macos() -> list[Path]:
    """Build macOS portable zip + launch script."""
    print("\n🍎 Building macOS package...")
    out = DIST / f"snc-macos-{arch_tag()}"
    out.mkdir(exist_ok=True)

    # Create app bundle directory
    app_dir = out / "Smart Nurse Call.app" / "Contents"
    (app_dir / "MacOS").mkdir(parents=True)
    (app_dir / "Resources").mkdir(parents=True)

    # Info.plist
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>{APP_NAME}</string>
  <key>CFBundleIdentifier</key>
  <string>com.nithep.snc</string>
  <key>CFBundleVersion</key>
  <string>{VERSION}</string>
  <key>CFBundleShortVersionString</key>
  <string>{VERSION}</string>
  <key>CFBundleExecutable</key>
  <string>snc-launcher</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>LSMinimumSystemVersion</key>
  <string>11.0</string>
</dict>
</plist>"""
    (app_dir / "Info.plist").write_text(plist, encoding="utf-8")

    # Launcher script
    launcher = f"""#!/bin/bash
# SNC Launcher — starts backend for local development
# This app bundles the SNC backend for macOS
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SNC_DIR="${{SNC_DIR:-$HOME/snc}}"

echo "🏥 Smart Nurse Call v{VERSION}"
echo "================================"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
  echo "❌ Python 3 not found. Install: brew install python@3.11"
  exit 1
fi

echo "✅ Python: $(python3 --version)"

# Install deps if needed
if ! python3 -c "import fastapi" 2>/dev/null; then
  echo "📦 Installing dependencies..."
  pip3 install --break-system-packages fastapi uvicorn pydantic aiohttp websockets httpx requests
fi

# Start backend
echo "🚀 Starting SNC Backend on port 8000..."
echo "   Dashboard: http://localhost:8000"
echo "   Health:    http://localhost:8000/health"
echo ""
cd "$SNC_DIR/api" 2>/dev/null || cd "$(dirname "$0")/../../Contents/Resources"
python3 -m uvicorn server:app --host 127.0.0.1 --port 8000
"""
    write_file(app_dir / "MacOS" / "snc-launcher", launcher, executable=True)

    # Requirements file for macOS
    req = (ROOT / "api" / "requirements.txt").read_text(encoding="utf-8")
    # Remove Firestore dependency (not needed on local Pi/macOS)
    req_clean = "\n".join(
        line for line in req.splitlines()
        if "google-cloud" not in line and line.strip()
    )
    (app_dir / "Resources" / "requirements.txt").write_text(req_clean, encoding="utf-8")

    # Homebrew formula
    formula_dir = out / "homebrew"
    formula_dir.mkdir(exist_ok=True)
    formula = f"""# SNC Homebrew Formula — macOS ARM64 / Intel
class Snc < Formula
  desc "{APP_NAME} — Raspberry Pi 4 Edge Backend"
  homepage "https://nursecall.nithep.com"
  version "{VERSION}"
  license "MIT"

  depends_on "python@3.11"

  def install
    # Copy api/ and app/ to prefix
    (prefix/"snc").install Dir["api/*"]
    (prefix/"snc").install Dir["app/*"]
    (prefix/"snc").mkpath
  end

  def caveats
    <<~EOS
      To run SNC locally:
        cd {SNC_ROOT}/api && python3 -m uvicorn server:app --host 127.0.0.1 --port 8000

      To install on Raspberry Pi:
        sudo ./ops/setup_pi.sh
    EOS
  end

  test do
    system "python3", "-c", "import fastapi; print(fastapi.__version__)"
  end
end
"""
    write_file(formula_dir / "snc.rb", formula)

    # Portable zip
    zip_path = DIST / f"snc-macos-{arch_tag()}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in out.rglob("*"):
            zf.write(f, f"Smart Nurse Call/{f.relative_to(out)}")
    print(f"  📦 Created: {zip_path.name} ({zip_path.stat().st_size // 1024} KB)")

    return [zip_path]


# ============================================================================
# Windows Build
# ============================================================================

def build_windows() -> list[Path]:
    """Build Windows portable zip + Inno Setup script."""
    print("\n🪟 Building Windows package...")
    out = DIST / f"snc-windows-x64"
    out.mkdir(exist_ok=True)

    # Portable launcher
    launcher_ps1 = f"""# SNC Launcher — Windows PowerShell
# Start Smart Nurse Call backend locally
$ErrorActionPreference = "Stop"

Write-Host "🏥 Smart Nurse Call v{VERSION}" -ForegroundColor Cyan
Write-Host "================================"
Write-Host ""

# Check Python
try {{
    $ver = python --version 2>&1
    Write-Host "✅ $ver" -ForegroundColor Green
}} catch {{
    Write-Host "❌ Python not found. Install from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}}

# Install deps
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
pip install fastapi uvicorn pydantic aiohttp websockets httpx requests 2>$null | Out-Null
Write-Host "✅ Dependencies installed" -ForegroundColor Green

# Start backend
Write-Host ""
Write-Host "🚀 Starting SNC Backend on port 8000..." -ForegroundColor Yellow
Write-Host "   Dashboard: http://localhost:8000"
Write-Host "   Health:    http://localhost:8000/health"
Write-Host ""

$apiDir = Join-Path $PSScriptRoot "api"
if (Test-Path $apiDir) {{
    Set-Location $apiDir
}} else {{
    Write-Host "⚠️  api/ directory not found — run from repo root" -ForegroundColor Yellow
}}

python -m uvicorn server:app --host 127.0.0.1 --port 8000
"""
    write_file(out / "snc-launcher.ps1", launcher_ps1)

    # Batch launcher for users who don't know PowerShell
    launcher_bat = f"""@echo off
REM SNC Launcher — Windows Batch
echo ========================================
echo Smart Nurse Call v{VERSION}
echo ========================================
echo.
python -m uvicorn server:app --host 127.0.0.1 --port 8000
pause
"""
    write_file(out / "snc-launcher.bat", launcher_bat)

    # Inno Setup script (for real installer .exe)
    inno_script = f"""[Setup]
AppId={{{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}}}}
AppName={APP_NAME}
AppVersion={VERSION}
AppPublisher=nithep.com
DefaultDirName={{autopf}}\\snc
DefaultGroupName={APP_NAME}
OutputDir=..\\dist
OutputBaseFilename=snc-windows-x64-setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "thai"; MessagesFile: "compiler:Languages\\Thai.isl"

[Files]
Source: "api\\*"; DestDir: "{{app}}\\api"; Flags: recursesubdirs
Source: "app\\*"; DestDir: "{{app}}\\app"; Flags: recursesubdirs
Source: "snc-launcher.bat"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "snc-launcher.ps1"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "..\\..\\api\\requirements.txt"; DestDir: "{{app}}"

[Icons]
Name: "{{group}}\\{APP_NAME}"; Filename: "{{app}}\\snc-launcher.bat"
Name: "{{group}}\\Uninstall"; Filename: "{{uninstallexe}}"

[Run]
Filename: "{{app}}\\snc-launcher.bat"; Description: "Start SNC now"; Flags: postinstall nowait
"""
    write_file(out / "snc-setup.iss", inno_script)

    # Portable zip
    zip_path = DIST / f"snc-windows-x64.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in out.rglob("*"):
            zf.write(f, f"SNC/{f.relative_to(out)}")
    print(f"  📦 Created: {zip_path.name} ({zip_path.stat().st_size // 1024} KB)")

    return [zip_path]


# ============================================================================
# Raspberry Pi OS Build
# ============================================================================

def build_pi() -> list[Path]:
    """Build .deb package + Docker image + systemd bundle for Pi OS ARM64."""
    print("\n🍓 Building Raspberry Pi OS package...")
    artifacts = []

    # --- .deb package ---
    deb_dir = DIST / f"snc-pi-arm64" / "deb"
    pkg_dir = deb_dir / f"snclite_{VERSION}_arm64"

    # Debian package structure
    control_dir = pkg_dir / "DEBIAN"
    control_dir.mkdir(parents=True)

    control = f"""Package: snclite
Version: {VERSION}
Section: net
Priority: optional
Architecture: arm64
Maintainer: nithep <noreply@nithep.com>
Depends: python3 (>= 3.11), python3-pip, sqlite3, systemd
Description: {APP_NAME} — Raspberry Pi 4 Edge Backend
 SNC is a Smart Nurse Call system that converts Phonik PBX nurse call
 signals into real-time web dashboard alerts and SLA tracking.
 .
 This package installs the complete 5-Core system:
 api/ (FastAPI backend), app/ (nurse dashboard),
 pbx/ (SMDR listener), ops/ (DevOps scripts).
 .
 Public URL: https://nursecall.nithep.com
"""
    write_file(control_dir / "control", control)

    # Post-install script
    postinst = f"""#!/bin/bash
set -e

SNC_ROOT="{SNC_ROOT}"
SNC_USER="ecs-agent"

echo "[SNC] Post-install setup..."

# Create user if missing
if ! id "$SNC_USER" &>/dev/null; then
  useradd --create-home --shell /bin/bash "$SNC_USER"
fi

# Copy installed files to SNC_ROOT
if [ -d "$SNC_ROOT" ]; then
  cp -r /usr/share/snc/api/* "$SNC_ROOT/api/" 2>/dev/null || true
  cp -r /usr/share/snc/app/* "$SNC_ROOT/app/" 2>/dev/null || true
  cp -r /usr/share/snc/pbx/* "$SNC_ROOT/pbx/" 2>/dev/null || true
  cp -r /usr/share/snc/ops/* "$SNC_ROOT/ops/" 2>/dev/null || true
  chown -R "$SNC_USER:$SNC_USER" "$SNC_ROOT"
fi

# Install Python deps
pip3 install --break-system-packages \\
  "fastapi>=0.95.0,<0.100.0" \\
  "uvicorn>=0.24.0" \\
  "pydantic>=1.10.0,<2.0.0" \\
  "httpx>=0.25.2" \\
  "python-multipart>=0.0.6" \\
  "aiohttp>=3.9.0" \\
  "websockets>=12.0" \\
  "requests>=2.31.0" 2>/dev/null || true

# Install systemd services
for svc in snc-backend snc-pbx-listener; do
  SVC_FILE="$SNC_ROOT/ops/${{svc}}.service"
  if [ -f "$SVC_FILE" ]; then
    cp "$SNC_FILE" "/etc/systemd/system/${{svc}}.service" 2>/dev/null || true
  fi
done
systemctl daemon-reload

echo ""
echo "✅ SNC installed! Next steps:"
echo "   sudo systemctl start snc-backend snc-pbx-listener"
echo "   curl http://localhost:8000/health"
"""
    write_file(control_dir / "postinst", postinst, executable=True)

    # Pre-remove script
    prerm = f"""#!/bin/bash
set -e
systemctl stop snc-backend 2>/dev/null || true
systemctl stop snc-pbx-listener 2>/dev/null || true
systemctl disable snc-backend 2>/dev/null || true
systemctl disable snc-pbx-listener 2>/dev/null || true
"""
    write_file(control_dir / "prerm", prerm, executable=True)

    # Data files: copy api, app, pbx, ops
    for subdir in ["api", "app", "pbx", "ops"]:
        src = ROOT / subdir
        dst = pkg_dir / "usr" / "share" / "snc" / subdir
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True,
                          ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".env", "node_modules"))
            print(f"  ✅ Copied {subdir}/ → deb")

    # Build .deb
    deb_out = DIST / f"snclite_{VERSION}_arm64.deb"
    try:
        run(["dpkg-deb", "--build", "--root-owner-group", str(pkg_dir), str(deb_out)])
        print(f"  📦 Created: {deb_out.name} ({deb_out.stat().st_size // 1024} KB)")
        artifacts.append(deb_out)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("  ⚠️  dpkg-deb not available (not on Debian/Ubuntu) — skipping .deb")
        shutil.rmtree(deb_dir, ignore_errors=True)

    # --- Docker image ---
    dockerfile = f"""FROM python:3.11-slim AS runtime
WORKDIR /app

# Copy dependencies
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code (5-Core)
COPY api/ ./api/
COPY app/ ./app/
COPY pbx/ ./pbx/
COPY ops/ ./ops/

# Create non-root user
RUN useradd --create-home --uid 10001 nonroot && chown -R nonroot:nonroot /app
USER nonroot

ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \\
  CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"]

CMD ["python3", "-m", "uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
"""
    write_file(DIST / "Dockerfile.pi", dockerfile)

    # Docker build context: copy sources
    docker_ctx = DIST / "docker-pi-context"
    for subdir in ["api", "app", "pbx", "ops"]:
        src = ROOT / subdir
        dst = docker_ctx / subdir
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True,
                          ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".env", "node_modules"))

    try:
        # Try to build Docker image (may fail on non-Docker hosts)
        run(["docker", "build", "-f", str(DIST / "Dockerfile.pi"),
             "-t", f"snc-pi:{VERSION}", str(docker_ctx)],
            timeout=120)

        # Export to tar
        docker_tar = DIST / f"snc-pi-{VERSION}-arm64.tar"
        run(["docker", "save", f"snc-pi:{VERSION}", "-o", str(docker_tar)])
        print(f"  🐳 Created: {docker_tar.name} ({docker_tar.stat().st_size // 1024 // 1024} MB)")
        artifacts.append(docker_tar)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        print("  ⚠️  Docker not available — skipping Docker image build")

    return artifacts


# ============================================================================
# Generate manifest + README
# ============================================================================

def generate_manifest(artifacts: dict[str, list[Path]]):
    """Generate download_manifest.json + INSTALL.md."""
    # ไฟล์ installer เผยแพร่ผ่าน GitHub Releases (nithep/snc)
    base_url = "https://github.com/nithep/snc/releases/latest/download"

    entries = []
    for platform_name, paths in artifacts.items():
        for p in paths:
            if p.exists():
                entries.append({
                    "platform": platform_name,
                    "label": p.name,
                    "meta": "Published via GitHub Releases (nithep/snc)",
                    "link": f"{base_url}/{p.name}",
                    "type": p.suffix.lstrip(".") or "bin",
                    "filename": p.name,
                    "size_bytes": p.stat().st_size,
                    "sha256": _sha256(p),
                })

    manifest = {
        "version": VERSION,
        "build_date": datetime.utcnow().isoformat() + "Z",
        "platforms": {
            "macOS": {"architectures": ["arm64", "x64"], "minimum": "macOS 11.0"},
            "Windows": {"architectures": ["x64"], "minimum": "Windows 10"},
            "Raspberry Pi OS": {"architectures": ["arm64"], "minimum": "Bookworm (Debian 12)"},
        },
        "downloads": entries,
        "service": {
            "name": APP_NAME,
            "base_url": "https://nursecall.nithep.com",
            "health": "https://nursecall.nithep.com/health",
            "dashboard": "https://nursecall.nithep.com/",
        },
    }
    write_file(DIST / "download_manifest.json", json.dumps(manifest, indent=2))

    # INSTALL.md
    install_md = f"""# 📥 Smart Nurse Call — Installation Guide

**Version:** {VERSION}
**Build Date:** {datetime.utcnow().strftime('%Y-%m-%d')}

---

## 🍓 Raspberry Pi OS (ARM64) — Primary Target

### Option A: .deb Package (Recommended)
```bash
# Copy to Pi
scp snclite_{VERSION}_arm64.deb pi4:/home/ecs-agent/

# Install on Pi
ssh pi4
sudo dpkg -i ~/snclite_{VERSION}_arm64.deb

# Configure
sudo ./setup-cloudflared.sh --token <CLOUDFLARE_TOKEN>
sudo systemctl start snc-backend snc-pbx-listener
```

### Option B: Docker
```bash
# Load image
docker load < snc-pi-{VERSION}-arm64.tar

# Run
docker run -d --name snc \\
  -p 8000:8000 \\
  -v /home/ecs-agent/snc/api/nurse_call_events.db:/app/api/nurse_call_events.db \\
  snc-pi:{VERSION}
```

---

## 🍎 macOS (Apple Silicon / Intel)

```bash
# Unzip
open "Smart Nurse Call.app"

# Or manual
cd ~/snc/api && python3 -m uvicorn server:app --host 127.0.0.1 --port 8000
```

### Homebrew
```bash
brew install --formula snc.rb
```

---

## 🪟 Windows (10/11)

1. Run `snc-launcher.bat` or `snc-launcher.ps1`
2. Backend starts at http://localhost:8000

### For installer (.exe)
1. Install [Inno Setup](https://jrsoftware.org/isinfo.php)
2. Open `snc-setup.iss` in Inno Setup
3. Build → produces `snc-windows-x64-setup.exe`

---

## 🔗 Access

| Interface | URL |
|-----------|-----|
| Dashboard | https://nursecall.nithep.com |
| Health | https://nursecall.nithep.com/health |
| LAN (Pi) | http://192.168.1.94:8000 |
"""
    write_file(DIST / "INSTALL.md", install_md)


def _sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ============================================================================
# Main
# ============================================================================

def main():
    global VERSION
    parser = argparse.ArgumentParser(description="Build SNC installers")
    parser.add_argument("--platform", choices=["macos", "windows", "pi", "all"], default="all")
    parser.add_argument("--version", default=VERSION,
                        help="Release version to stamp into artifacts (e.g. 1.0.0 or v1.0.0). Default: %(default)s")
    parser.add_argument("--list", action="store_true", help="List available platforms")
    args = parser.parse_args()

    # ใช้เวอร์ชันจาก --version (strip ตัว v หน้า เพราะ Debian version ต้องขึ้นต้นด้วยตัวเลข)
    VERSION = args.version.lstrip("v")

    if args.list:
        current = platform.system().lower()
        print(f"Current platform: {current} ({platform.machine()})")
        print(f"Available builds:")
        print(f"  macos   — {'✅' if current == 'darwin' else '⚠️  (cross-build possible)'}")
        print(f"  windows — {'✅' if current == 'windows' else '⚠️  (cross-build possible)'}")
        print(f"  pi      — ✅ (always available)")
        return

    print(f"🏥 SNC Installer Builder v{VERSION}")
    print(f"   Platform: {platform.system()} {platform.machine()}")
    print(f"   Output: {DIST}")

    artifacts: dict[str, list[Path]] = {}

    if args.platform in ("macos", "all"):
        try:
            artifacts["macOS"] = build_macos()
        except Exception as e:
            print(f"  ❌ macOS build failed: {e}")

    if args.platform in ("windows", "all"):
        try:
            artifacts["Windows"] = build_windows()
        except Exception as e:
            print(f"  ❌ Windows build failed: {e}")

    if args.platform in ("pi", "all"):
        try:
            artifacts["Raspberry Pi OS"] = build_pi()
        except Exception as e:
            print(f"  ❌ Pi build failed: {e}")

    # Generate manifest
    if artifacts:
        generate_manifest(artifacts)

    # Summary
    print(f"\n{'='*60}")
    print(f"✅ Build complete! Artifacts in: {DIST}")
    print(f"{'='*60}")
    for plat, paths in artifacts.items():
        for p in paths:
            if p.exists():
                size = p.stat().st_size
                unit = "KB" if size < 1024*1024 else "MB"
                val = size // 1024 if unit == "KB" else size // (1024*1024)
                print(f"  {plat:20s} {p.name:40s} {val:>6} {unit}")


if __name__ == "__main__":
    main()

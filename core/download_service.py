from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class DownloadService:
    """Read the packaged installer manifest and expose download metadata."""

    def __init__(self, manifest_path: str | Path | None = None) -> None:
        if manifest_path is None:
            manifest_path = Path(__file__).resolve().parent.parent / "packaging" / "dist" / "download_manifest.json"
        self.manifest_path = Path(manifest_path)

    def load_manifest(self) -> Dict[str, Any]:
        if not self.manifest_path.exists():
            return {"downloads": [], "service": {"name": "Smart Nurse Call", "base_url": "", "health": "", "dashboard": ""}}
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def get_downloads(self) -> List[Dict[str, Any]]:
        return self.load_manifest().get("downloads", [])

    def get_service_urls(self) -> Dict[str, str]:
        return self.load_manifest().get("service", {})

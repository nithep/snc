from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


def test_modular_layout_exists():
    assert (REPO / "core").is_dir()
    assert (REPO / "surfaces" / "gui").is_dir()
    assert (REPO / "packaging").is_dir()
    assert (REPO / "tests").is_dir()


def test_service_portal_has_expected_menu():
    portal = REPO / "surfaces" / "gui" / "service_portal.html"
    assert portal.is_file()
    text = portal.read_text(encoding="utf-8")
    # Portal เป็น dynamic — รายการโหลด (platform) มาจาก GET /api/downloads
    # (ดู packaging/download_manifest.json) ไม่ได้ hardcode ใน HTML แล้ว
    assert "Downloads & Service Portal" in text
    assert "GET /api/downloads" in text
    assert "GitHub Releases" in text


def test_download_manifest_covers_platforms():
    import json
    manifest_path = REPO / "packaging" / "download_manifest.json"
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # manifest เป็น source ของ platform ใน portal — ต้องครบทั้ง 3 (macOS/Windows/Pi)
    assert set(manifest["platforms"].keys()) == {"macOS", "Windows", "Raspberry Pi OS"}


def test_packaging_has_dist_manifest():
    manifest = REPO / "packaging" / "dist" / "download_manifest.json"
    assert manifest.is_file()

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
    assert "Downloads & Service Portal" in text
    assert "macOS" in text
    assert "Windows" in text
    assert "Raspberry Pi OS" in text


def test_packaging_has_dist_manifest():
    manifest = REPO / "packaging" / "dist" / "download_manifest.json"
    assert manifest.is_file()

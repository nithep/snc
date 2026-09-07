#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ops/check_vault_links.py — ตรวจ wikilink ใน Obsidian vault ให้ resolve กับเอกสารจริงทั้งหมด

หลักการ (เหมือนที่ nightly KB loop ใช้):
- กวาดไฟล์ .md ทั้ง vault (root = repo root ตาม .obsidian) สร้าง inventory ชื่อไฟล์ (basename)
- ตรวจเฉพาะลิงก์จริง — ข้ามเนื้อหาใน ``` fence และ `inline code` (Obsidian ไม่ resolve ตรงนั้น)
- สนับสนุน [[ไฟล์]], [[ไฟล์|alias]], [[ไฟล์#heading]], [[path/ไฟล์]]
- resolve แบบ case-insensitive ตามพฤติกรรมของ Obsidian

วิธีใช้:
    python ops/check_vault_links.py                # ตรวจทั้งหมด (exit 0 = ผ่าน / 1 = มีลิงก์ตาย)
    python ops/check_vault_links.py --quiet        # แสดงเฉพาะปัญหา
    python ops/check_vault_links.py --skip "doc/raw"   # ข้ามไดเรกทอรีเพิ่ม (ใช้ซ้ำได้)

ข้อกำหนด: Python 3.8+ (stdlib เท่านั้น — ไม่ต้องติดตั้ง dependency)
"""
from __future__ import annotations

import argparse
import collections
import os
import re
import sys
from pathlib import Path

# ไดเรกทอรีที่ไม่ใช่ส่วน vault / หนักเกินไป — ไม่นับเป็น source หรือ target
DEFAULT_SKIP = {
    ".agents", ".freebuff", ".git", ".obsidian", ".opencode", ".pytest_cache",
    ".venv", "Phonik", "__pycache__", "logs", "node_modules",
}

LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
FENCE_RE = re.compile(r"```.*?```", re.S)
INLINE_RE = re.compile(r"`[^`]*`")


def repo_root() -> Path:
    """Root ของ repo = โฟลเดอร์แม่ของ ops/ (สมมติสคริปต์อยู่ที่ <root>/ops/)."""
    return Path(__file__).resolve().parent.parent


def gather_md_files(root: Path, extra_skip: set[str]) -> list[Path]:
    files: list[Path] = []
    skip = DEFAULT_SKIP | {s.rstrip("/\\") for s in extra_skip}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in filenames:
            if fn.lower().endswith(".md"):
                files.append(Path(dirpath) / fn)
    return files


def build_inventory(md_files: list[Path]) -> dict[str, list[str]]:
    """basename (lowercase) -> ชื่อไฟล์จริง — รองรับชื่อซ้ำข้ามโฟลเดอร์."""
    inventory: dict[str, list[str]] = collections.defaultdict(list)
    for p in md_files:
        inventory[p.stem.lower()].append(p.stem)
    return inventory


def find_links(text: str) -> list[str]:
    """ดึง wikilink จริง (ข้าม fence + inline code) แล้วคืนชื่อ target."""
    text = FENCE_RE.sub("", text)
    text = INLINE_RE.sub("", text)
    return [m.group(1).strip() for m in LINK_RE.finditer(text)]


def resolve(target: str, inventory: dict[str, list[str]], root: Path) -> bool:
    if target.lower() in inventory:
        return True
    # รองรับ [[folder/file]] / [[./folder/file]]
    if "/" in target or "\\" in target:
        rel = target.lstrip("./").lstrip(".\\").replace("\\", "/")
        if (root / rel).is_file():
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ตรวจ wikilink ใน Obsidian vault ว่า resolve กับไฟล์จริงทั้งหมด")
    parser.add_argument("--quiet", action="store_true", help="แสดงเฉพาะลิงก์ตาย (เหมาะกับ cron/CI)")
    parser.add_argument("--skip", action="append", default=[],
                        metavar="DIR", help="ไดเรกทอรีให้ข้ามเพิ่มเติม (ใช้ซ้ำได้)")
    args = parser.parse_args(argv)

    root = repo_root()
    md_files = gather_md_files(root, set(args.skip))
    if not md_files:
        print(f"[ERR] ไม่พบไฟล์ .md ใต้ {root}", file=sys.stderr)
        return 2

    inventory = build_inventory(md_files)

    # source: เนื้อหาใน doc/ ทั้งหมด + ไฟล์ .md ระดับ root (README, AGENTS ฯลฯ)
    sources = [p for p in md_files
               if str(p).startswith(str(root / "doc")) or p.parent == root]

    broken: list[tuple[str, str]] = []
    per_link: dict[str, int] = collections.defaultdict(int)
    checked = 0
    for path in sorted(sources):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"[WARN] อ่าน {path} ไม่ได้: {exc}", file=sys.stderr)
            continue
        rel = path.relative_to(root).as_posix()
        for target in find_links(text):
            checked += 1
            per_link[target] += 1
            if not resolve(target, inventory, root):
                broken.append((rel, target))

    if args.quiet:
        for rel, target in broken:
            print(f"{rel}: [[{target}]]")
    else:
        print(f"vault md files: {len(md_files)} | sources ตรวจ: {len(sources)} | "
              f"wikilinks: {checked} | broken: {len(broken)}")
        for rel, target in sorted(broken):
            print(f"  [BROKEN] {rel} -> [[{target}]]")

    if broken:
        print(f"[FAIL] พบลิงก์ตาย {len(broken)} จุด — แก้ก่อน merge (ห้าม merge broken link ตาม ADR 0013)",
              file=sys.stderr)
        return 1
    if not args.quiet:
        print("[OK] wikilink ครบ — resolve ได้ทุกจุด")
    return 0


if __name__ == "__main__":
    sys.exit(main())

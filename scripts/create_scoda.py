#!/usr/bin/env python3
"""Create a .scoda package from kstrati.db.

A .scoda file is a ZIP archive containing:
  manifest.json   — package identity, version, checksum
  data.db         — the SQLite database
"""

import hashlib
import json
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "kstrati.db"
OUTPUT_PATH = ROOT / "kstrati.scoda"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def count_data_records(db_path: Path) -> int:
    scoda_tables = {
        "artifact_metadata", "provenance", "schema_descriptions",
        "ui_display_intent", "ui_queries", "ui_manifest",
    }
    conn = sqlite3.connect(str(db_path))
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    total = 0
    for (name,) in tables:
        if name not in scoda_tables and not name.startswith("sqlite_"):
            total += conn.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
    conn.close()
    return total


def build_manifest(db_path: Path) -> dict:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    meta = {
        row["key"]: row["value"]
        for row in conn.execute("SELECT key, value FROM artifact_metadata")
    }
    conn.close()

    return {
        "format": "scoda",
        "format_version": "1.0",
        "name": meta.get("artifact_id", "kstrati"),
        "version": meta.get("version", "0.1.0"),
        "title": f"{meta.get('name', 'KStrati')} - {meta.get('description', '')}",
        "description": meta.get("description", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "license": meta.get("license", "CC-BY-4.0"),
        "data_file": "data.db",
        "record_count": count_data_records(db_path),
        "data_checksum_sha256": sha256_file(db_path),
    }


def main():
    if not DB_PATH.exists():
        print(f"Error: {DB_PATH} not found. Run create_database.py and add_scoda_tables.py first.")
        raise SystemExit(1)

    manifest = build_manifest(DB_PATH)

    with zipfile.ZipFile(OUTPUT_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
        zf.write(DB_PATH, "data.db")

    size = OUTPUT_PATH.stat().st_size
    print(f"Created: {OUTPUT_PATH}")
    print(f"  Size:     {size:,} bytes")
    print(f"  Name:     {manifest['name']}")
    print(f"  Version:  {manifest['version']}")
    print(f"  Records:  {manifest['record_count']}")
    print(f"  Checksum: {manifest['data_checksum_sha256'][:16]}...")
    print(f"\nmanifest.json:")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

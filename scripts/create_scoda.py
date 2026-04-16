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
DIST_DIR = ROOT / "dist"


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


def _read_version(db_path: Path) -> str:
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT value FROM artifact_metadata WHERE key='version'"
        ).fetchone()
        return row[0] if row else "0.0.0"
    finally:
        conn.close()


def main():
    if not DB_PATH.exists():
        print(f"Error: {DB_PATH} not found. Run create_database.py and add_scoda_tables.py first.")
        raise SystemExit(1)

    version = _read_version(DB_PATH)
    DIST_DIR.mkdir(exist_ok=True)

    scoda_path = DIST_DIR / f"kstrati-{version}.scoda"
    manifest_path = DIST_DIR / f"kstrati-{version}.manifest.json"
    manifest = build_manifest(DB_PATH)

    # Write .scoda (ZIP)
    with zipfile.ZipFile(scoda_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
        zf.write(DB_PATH, "data.db")

    # Write .manifest.json
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    size = scoda_path.stat().st_size
    print(f"Created: {scoda_path}")
    print(f"         {manifest_path}")
    print(f"  Size:     {size:,} bytes")
    print(f"  Name:     {manifest['name']}")
    print(f"  Version:  {manifest['version']}")
    print(f"  Records:  {manifest['record_count']}")
    print(f"  Checksum: {manifest['data_checksum_sha256'][:16]}...")


if __name__ == "__main__":
    main()

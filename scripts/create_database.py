#!/usr/bin/env python3
"""Build kstrati SQLite database from JSON source data."""

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = ROOT / "kstrati.db"


def create_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS strat_units (
            id        INTEGER PRIMARY KEY,
            name      TEXT NOT NULL,
            name_ko   TEXT,
            rank      TEXT NOT NULL,   -- 'group' or 'formation'
            parent_id INTEGER,
            prev_id   INTEGER,
            next_id   INTEGER,
            sort_order  INTEGER NOT NULL DEFAULT 0,
            alt_name    TEXT,
            alt_name_ko TEXT,
            faunal_province TEXT,
            facies    TEXT,
            FOREIGN KEY (parent_id) REFERENCES strat_units(id),
            FOREIGN KEY (prev_id)   REFERENCES strat_units(id),
            FOREIGN KEY (next_id)   REFERENCES strat_units(id)
        );

        CREATE TABLE IF NOT EXISTS biozones (
            id      INTEGER PRIMARY KEY,
            name    TEXT NOT NULL,
            prev_id INTEGER,
            next_id INTEGER,
            note    TEXT,
            FOREIGN KEY (prev_id) REFERENCES biozones(id),
            FOREIGN KEY (next_id) REFERENCES biozones(id)
        );

        CREATE TABLE IF NOT EXISTS provenance (
            id          INTEGER PRIMARY KEY,
            source_type TEXT NOT NULL,
            citation    TEXT NOT NULL,
            description TEXT,
            year        INTEGER,
            url         TEXT
        );

        CREATE TABLE IF NOT EXISTS biozone_occurrences (
            id            INTEGER PRIMARY KEY,
            biozone_id    INTEGER NOT NULL,
            formation_id  INTEGER NOT NULL,
            provenance_id INTEGER REFERENCES provenance(id),
            basis         TEXT NOT NULL DEFAULT 'stated',
            FOREIGN KEY (biozone_id)   REFERENCES biozones(id),
            FOREIGN KEY (formation_id) REFERENCES strat_units(id)
        );

        CREATE TABLE IF NOT EXISTS age_assignments (
            id             INTEGER PRIMARY KEY,
            entity_type    TEXT NOT NULL,   -- 'formation' or 'biozone'
            entity_id      INTEGER NOT NULL,
            ics_series     TEXT,
            ics_stage      TEXT,
            stage_original TEXT,
            age_relation   TEXT DEFAULT 'within',
            provenance_id  INTEGER REFERENCES provenance(id),
            basis          TEXT NOT NULL DEFAULT 'chart_inferred'
        );
    """)


def normalize_list(val):
    """Ensure value is a list."""
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


def seed_provenance(conn: sqlite3.Connection):
    """Insert the primary provenance record so FK references work."""
    conn.execute(
        "INSERT OR IGNORE INTO provenance (id, source_type, citation, description, year) VALUES (?,?,?,?,?)",
        (1, "primary",
         "Choi, D.K. (2011) A new view on the early Paleozoic paleogeography and paleoenvironments of the Taebaeksan Basin, Korea. "
         "Journal of the Paleontological Society of Korea, 27(1), 1–11.",
         "태백산분지의 전기 고생대 고지리, 고환경에 관한 새로운 견해",
         2011),
    )
    conn.commit()


def load_data(conn: sqlite3.Connection, source: dict):
    cur = conn.cursor()

    # --- name -> id lookup tables (filled as we insert) ---
    unit_ids = {}   # "Taebaek Group" -> id, "Dumugol" -> id
    bz_ids = {}     # "Kayseraspis" -> id

    # ── Pass 1: Insert groups and formations (without prev/next) ──
    for gi, group in enumerate(source["groups"]):
        cur.execute(
            "INSERT INTO strat_units (name, name_ko, rank, sort_order, faunal_province, facies) VALUES (?,?,?,?,?,?)",
            (group["name"], group["name_ko"], "group", gi,
             group["faunal_province"], group["facies"]),
        )
        group_id = cur.lastrowid
        unit_ids[group["name"]] = group_id

        # Formations are listed youngest-first in JSON;
        # sort_order: youngest = smallest so tree renders top-down = young→old
        for fi, fm in enumerate(group["formations"]):
            cur.execute(
                "INSERT INTO strat_units (name, name_ko, rank, parent_id, sort_order, alt_name, alt_name_ko) VALUES (?,?,?,?,?,?,?)",
                (fm["name"], fm["name_ko"], "formation", group_id, fi,
                 fm.get("alt_name"), fm.get("alt_name_ko")),
            )
            unit_ids[fm["name"]] = cur.lastrowid

    # ── Pass 2: Resolve prev/next for formations ──
    for group in source["groups"]:
        for fm in group["formations"]:
            fm_id = unit_ids[fm["name"]]
            prev_id = unit_ids.get(fm.get("prev")) if fm.get("prev") else None
            next_id = unit_ids.get(fm.get("next")) if fm.get("next") else None
            cur.execute(
                "UPDATE strat_units SET prev_id=?, next_id=? WHERE id=?",
                (prev_id, next_id, fm_id),
            )

    # ── Pass 3: Insert biozones (without prev/next) ──
    for bz in source["biozones"]:
        cur.execute(
            "INSERT INTO biozones (name, note) VALUES (?,?)",
            (bz["name"], bz.get("note")),
        )
        bz_ids[bz["name"]] = cur.lastrowid

    # ── Pass 4: Resolve prev/next for biozones ──
    for bz in source["biozones"]:
        bz_id = bz_ids[bz["name"]]
        prev_id = bz_ids.get(bz.get("prev")) if bz.get("prev") else None
        next_id = bz_ids.get(bz.get("next")) if bz.get("next") else None
        cur.execute(
            "UPDATE biozones SET prev_id=?, next_id=? WHERE id=?",
            (prev_id, next_id, bz_id),
        )

    # ── Pass 5: Biozone occurrences ──
    for bz in source["biozones"]:
        bz_id = bz_ids[bz["name"]]
        for occ in bz["occurrences"]:
            fm_id = unit_ids[occ["formation"]]
            cur.execute(
                "INSERT INTO biozone_occurrences (biozone_id, formation_id, provenance_id, basis) VALUES (?,?,1,'stated')",
                (bz_id, fm_id),
            )

    # ── Pass 6: Age assignments for formations ──
    for group in source["groups"]:
        for fm in group["formations"]:
            fm_id = unit_ids[fm["name"]]
            age = fm["age"]

            # Determine series values
            series_list = normalize_list(age.get("series") or age.get("series_ics"))
            series_original = age.get("series_original")

            # Determine stage values and originals
            stages = normalize_list(age.get("stage") or age.get("stage_ics"))
            stage_originals = normalize_list(age.get("stage_original"))

            if stages:
                for i, stage in enumerate(stages):
                    original = stage_originals[i] if i < len(stage_originals) else None
                    series = series_list[0] if len(series_list) == 1 else (
                        series_list[i] if i < len(series_list) else series_list[-1]
                    )
                    # If the series name differs from ICS, record original
                    if series_original and not age.get("series"):
                        series = age.get("series_ics") if isinstance(age.get("series_ics"), str) else series
                    cur.execute(
                        "INSERT INTO age_assignments (entity_type, entity_id, ics_series, ics_stage, stage_original, provenance_id, basis) VALUES (?,?,?,?,?,1,'chart_inferred')",
                        ("formation", fm_id, series, stage, original),
                    )
            elif series_list:
                for series in series_list:
                    cur.execute(
                        "INSERT INTO age_assignments (entity_type, entity_id, ics_series, provenance_id, basis) VALUES (?,?,?,1,'chart_inferred')",
                        ("formation", fm_id, series),
                    )

    conn.commit()


def print_summary(conn: sqlite3.Connection):
    cur = conn.cursor()
    tables = ["strat_units", "biozones", "biozone_occurrences", "age_assignments"]
    print("── Database summary ──")
    for t in tables:
        count = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {count} rows")

    print("\n── Strat units ──")
    for row in cur.execute(
        "SELECT u.id, u.name, u.rank, u.sort_order, p.name AS parent, prev.name AS prev, nxt.name AS next "
        "FROM strat_units u "
        "LEFT JOIN strat_units p ON u.parent_id = p.id "
        "LEFT JOIN strat_units prev ON u.prev_id = prev.id "
        "LEFT JOIN strat_units nxt ON u.next_id = nxt.id "
        "ORDER BY u.id"
    ):
        print(f"  [{row[0]:2d}] {row[2]:10s} {row[1]:20s}  order={row[3]}  parent={row[4] or '-':20s}  prev={row[5] or '-':12s}  next={row[6] or '-':12s}")

    print("\n── Biozones (first 10) ──")
    for row in cur.execute(
        "SELECT b.id, b.name, prev.name AS prev, nxt.name AS next "
        "FROM biozones b "
        "LEFT JOIN biozones prev ON b.prev_id = prev.id "
        "LEFT JOIN biozones nxt ON b.next_id = nxt.id "
        "ORDER BY b.id LIMIT 10"
    ):
        print(f"  [{row[0]:2d}] {row[1]:30s}  prev={row[2] or '-':30s}  next={row[3] or '-':20s}")

    print("\n── Cross-group biozones ──")
    for row in cur.execute(
        "SELECT b.name, GROUP_CONCAT(u.name, ', ') AS formations "
        "FROM biozone_occurrences bo "
        "JOIN biozones b ON bo.biozone_id = b.id "
        "JOIN strat_units u ON bo.formation_id = u.id "
        "GROUP BY b.id HAVING COUNT(*) > 1"
    ):
        print(f"  {row[0]:20s} -> {row[1]}")


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()

    with open(DATA_DIR / "taebaeksan_basin.json", encoding="utf-8") as f:
        source = json.load(f)

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    create_tables(conn)
    seed_provenance(conn)
    load_data(conn, source)
    print_summary(conn)

    conn.close()
    print(f"\n-> {DB_PATH}")


if __name__ == "__main__":
    main()

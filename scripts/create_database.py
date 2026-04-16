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
            alt_name    TEXT,
            alt_name_ko TEXT,
            faunal_province TEXT,
            facies    TEXT
        );

        CREATE TABLE IF NOT EXISTS strat_edge_cache (
            provenance_id INTEGER NOT NULL REFERENCES provenance(id),
            child_id      INTEGER NOT NULL REFERENCES strat_units(id),
            parent_id     INTEGER REFERENCES strat_units(id),
            prev_id       INTEGER REFERENCES strat_units(id),
            next_id       INTEGER REFERENCES strat_units(id),
            sort_order    INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (provenance_id, child_id)
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
            short_name  TEXT NOT NULL,
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
    """Insert provenance records so FK references work."""
    conn.execute(
        "INSERT OR IGNORE INTO provenance (id, source_type, short_name, citation, description, year) VALUES (?,?,?,?,?,?)",
        (1, "primary", "Choi (2011)",
         "Choi, D.K. (2011) A new view on the early Paleozoic paleogeography and paleoenvironments of the Taebaeksan Basin, Korea. "
         "Journal of the Paleontological Society of Korea, 27(1), 1–11.",
         "태백산분지의 전기 고생대 고지리, 고환경에 관한 새로운 견해",
         2011),
    )
    conn.execute(
        "INSERT OR IGNORE INTO provenance (id, source_type, short_name, citation, description, year) VALUES (?,?,?,?,?,?)",
        (2, "primary", "Kim & Lee (2017)",
         "Kim, M.G., and Lee, Y.I., 2017, The stratigraphy and correlation of the upper Paleozoic "
         "Pyeongan Supergroup of southern Korean Peninsula - A review: Journal of the Geological "
         "Society of Korea, v. 53, p. 321–338.",
         "남한에 분포하는 상부고생대 평안누층군의 층서 및 대비 - 총설",
         2017),
    )
    conn.commit()


def load_data(conn: sqlite3.Connection, source: dict):
    cur = conn.cursor()

    # --- name -> id lookup tables (filled as we insert) ---
    unit_ids = {}   # "Taebaek Group" -> id, "Dumugol" -> id
    bz_ids = {}     # "Kayseraspis" -> id

    # ── Pass 1: Insert supergroup, groups, and formations (unit attributes only) ──
    sg = source.get("supergroup")
    if sg:
        cur.execute(
            "INSERT INTO strat_units (name, name_ko, rank) VALUES (?,?,?)",
            (sg["name"], sg["name_ko"], "supergroup"),
        )
        unit_ids[sg["name"]] = cur.lastrowid

    for gi, group in enumerate(source["groups"]):
        cur.execute(
            "INSERT INTO strat_units (name, name_ko, rank, faunal_province, facies) VALUES (?,?,?,?,?)",
            (group["name"], group["name_ko"], "group",
             group["faunal_province"], group["facies"]),
        )
        unit_ids[group["name"]] = cur.lastrowid

        for fi, fm in enumerate(group["formations"]):
            cur.execute(
                "INSERT INTO strat_units (name, name_ko, rank, alt_name, alt_name_ko) VALUES (?,?,?,?,?)",
                (fm["name"], fm["name_ko"], "formation",
                 fm.get("alt_name"), fm.get("alt_name_ko")),
            )
            unit_ids[fm["name"]] = cur.lastrowid

    # ── Pass 2: Populate strat_edge_cache (provenance-dependent hierarchy) ──
    PROV_ID = 1  # Choi (2011)
    sg_id = unit_ids.get(sg["name"]) if sg else None

    # Supergroup edge: root node
    if sg_id:
        cur.execute(
            "INSERT INTO strat_edge_cache (provenance_id, child_id, parent_id, prev_id, next_id, sort_order) VALUES (?,?,?,?,?,?)",
            (PROV_ID, sg_id, None, None, None, 0),
        )

    for gi, group in enumerate(source["groups"]):
        group_id = unit_ids[group["name"]]
        # Group edge: parent=supergroup (or root if no supergroup)
        cur.execute(
            "INSERT INTO strat_edge_cache (provenance_id, child_id, parent_id, prev_id, next_id, sort_order) VALUES (?,?,?,?,?,?)",
            (PROV_ID, group_id, sg_id, None, None, gi),
        )
        # Formation edges: parent=group, with prev/next and sort_order
        for fi, fm in enumerate(group["formations"]):
            fm_id = unit_ids[fm["name"]]
            prev_id = unit_ids.get(fm.get("prev")) if fm.get("prev") else None
            next_id = unit_ids.get(fm.get("next")) if fm.get("next") else None
            cur.execute(
                "INSERT INTO strat_edge_cache (provenance_id, child_id, parent_id, prev_id, next_id, sort_order) VALUES (?,?,?,?,?,?)",
                (PROV_ID, fm_id, group_id, prev_id, next_id, fi),
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


def load_pyeongan_data(conn: sqlite3.Connection, source: dict):
    """Load Pyeongan Supergroup data (coalfield-based hierarchy, no biozones)."""
    cur = conn.cursor()
    PROV_ID = 2  # Pyeongan correlation

    # --- Insert supergroup ---
    sg = source["supergroup"]
    cur.execute(
        "INSERT INTO strat_units (name, name_ko, rank) VALUES (?,?,?)",
        (sg["name"], sg["name_ko"], "supergroup"),
    )
    sg_id = cur.lastrowid

    cur.execute(
        "INSERT INTO strat_edge_cache (provenance_id, child_id, parent_id, prev_id, next_id, sort_order) VALUES (?,?,?,?,?,?)",
        (PROV_ID, sg_id, None, None, None, 0),
    )

    # --- Insert coalfields and their formations ---
    for ci, coalfield in enumerate(source["coalfields"]):
        # Insert coalfield as a strat_unit
        cur.execute(
            "INSERT INTO strat_units (name, name_ko, rank) VALUES (?,?,?)",
            (coalfield["name"], coalfield["name_ko"], "coalfield"),
        )
        cf_id = cur.lastrowid

        cur.execute(
            "INSERT INTO strat_edge_cache (provenance_id, child_id, parent_id, prev_id, next_id, sort_order) VALUES (?,?,?,?,?,?)",
            (PROV_ID, cf_id, sg_id, None, None, ci),
        )

        # Insert formations for this coalfield
        # Use scoped lookup: key = (coalfield_index, fm_name)
        fm_ids = {}  # fm_name -> id within this coalfield
        for fi, fm in enumerate(coalfield["formations"]):
            cur.execute(
                "INSERT INTO strat_units (name, name_ko, rank) VALUES (?,?,?)",
                (fm["name"], fm["name_ko"], "formation"),
            )
            fm_id = cur.lastrowid
            fm_ids[fm["name"]] = fm_id

        # Second pass: resolve prev/next and insert edge_cache + age_assignments
        for fi, fm in enumerate(coalfield["formations"]):
            fm_id = fm_ids[fm["name"]]
            prev_id = fm_ids.get(fm.get("prev"))
            next_id = fm_ids.get(fm.get("next"))
            cur.execute(
                "INSERT INTO strat_edge_cache (provenance_id, child_id, parent_id, prev_id, next_id, sort_order) VALUES (?,?,?,?,?,?)",
                (PROV_ID, fm_id, cf_id, prev_id, next_id, fi),
            )

            # Age assignments
            age = fm["age"]
            stages = normalize_list(age.get("stage"))
            epoch = age.get("epoch", "")
            period = age.get("period", "")

            if stages:
                for stage in stages:
                    cur.execute(
                        "INSERT INTO age_assignments (entity_type, entity_id, ics_series, ics_stage, stage_original, provenance_id, basis) VALUES (?,?,?,?,?,?,?)",
                        ("formation", fm_id, epoch, stage, None, PROV_ID, "chart_inferred"),
                    )
            else:
                cur.execute(
                    "INSERT INTO age_assignments (entity_type, entity_id, ics_series, ics_stage, stage_original, provenance_id, basis) VALUES (?,?,?,?,?,?,?)",
                    ("formation", fm_id, epoch, None, None, PROV_ID, "chart_inferred"),
                )

    conn.commit()


def print_summary(conn: sqlite3.Connection):
    cur = conn.cursor()
    tables = ["strat_units", "strat_edge_cache", "biozones", "biozone_occurrences", "age_assignments"]
    print("── Database summary ──")
    for t in tables:
        count = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {count} rows")

    print("\n── Strat units (provenance_id=1) ──")
    for row in cur.execute(
        "SELECT u.id, u.name, u.rank, e.sort_order, p.name AS parent, prev.name AS prev, nxt.name AS next "
        "FROM strat_units u "
        "JOIN strat_edge_cache e ON e.child_id = u.id AND e.provenance_id = 1 "
        "LEFT JOIN strat_units p ON e.parent_id = p.id "
        "LEFT JOIN strat_units prev ON e.prev_id = prev.id "
        "LEFT JOIN strat_units nxt ON e.next_id = nxt.id "
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

    with open(DATA_DIR / "joseon_supergroup.json", encoding="utf-8") as f:
        joseon = json.load(f)

    with open(DATA_DIR / "pyeongan_supergroup.json", encoding="utf-8") as f:
        pyeongan = json.load(f)

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    create_tables(conn)
    seed_provenance(conn)
    load_data(conn, joseon)
    load_pyeongan_data(conn, pyeongan)
    print_summary(conn)

    conn.close()
    print(f"\n-> {DB_PATH}")


if __name__ == "__main__":
    main()

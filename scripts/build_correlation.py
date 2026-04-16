#!/usr/bin/env python3
"""Build pre-computed correlation chart rows.

Joseon Supergroup: biozone-slot rows from data/correlation_chart.json
Pyeongan Supergroup: stage-based rows computed from data/pyeongan_supergroup.json
"""

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = ROOT / "kstrati.db"


def compute_rowspans(values):
    """Compute rowspan for each row: first occurrence gets the span count, rest get 0."""
    n = len(values)
    spans = [0] * n
    i = 0
    while i < n:
        j = i + 1
        while j < n and values[j] == values[i]:
            j += 1
        spans[i] = j - i
        i = j
    return spans


def normalize_list(val):
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Joseon Supergroup (Taebaek / Yeongwol)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_joseon_correlation(conn):
    with open(DATA_DIR / "correlation_chart.json", encoding="utf-8") as f:
        data = json.load(f)
    raw_rows = [tuple(row) for row in data["rows"]]

    conn.execute("DROP TABLE IF EXISTS correlation_chart")
    conn.execute("""
        CREATE TABLE correlation_chart (
            row_num             INTEGER NOT NULL,
            provenance_id       INTEGER NOT NULL DEFAULT 1,
            period              TEXT,
            period_rowspan      INTEGER DEFAULT 0,
            stage               TEXT,
            stage_rowspan       INTEGER DEFAULT 0,
            taebaek_fm          TEXT,
            taebaek_fm_rowspan  INTEGER DEFAULT 0,
            taebaek_bz          TEXT,
            yeongwol_fm         TEXT,
            yeongwol_fm_rowspan INTEGER DEFAULT 0,
            yeongwol_bz         TEXT,
            PRIMARY KEY (provenance_id, row_num)
        )
    """)

    periods = [r[0] for r in raw_rows]
    stages = [r[1] for r in raw_rows]
    tb_fms = [r[2] for r in raw_rows]
    yw_fms = [r[4] for r in raw_rows]

    period_spans = compute_rowspans(periods)
    stage_spans = compute_rowspans(stages)
    tb_fm_spans = compute_rowspans(tb_fms)
    yw_fm_spans = compute_rowspans(yw_fms)

    for i, row in enumerate(raw_rows):
        conn.execute(
            """INSERT INTO correlation_chart
               (row_num, period, period_rowspan, stage, stage_rowspan,
                taebaek_fm, taebaek_fm_rowspan, taebaek_bz,
                yeongwol_fm, yeongwol_fm_rowspan, yeongwol_bz)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (i, row[0], period_spans[i], row[1], stage_spans[i],
             row[2], tb_fm_spans[i], row[3],
             row[4], yw_fm_spans[i], row[5]),
        )
    conn.commit()

    print("── Joseon correlation chart ──")
    print(f"  {len(raw_rows)} rows")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Pyeongan Supergroup (coalfield correlation)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ICS stages youngest→oldest (top→bottom in chart)
PYEONGAN_STAGE_ROWS = [
    ("Triassic",      "Middle Triassic",       "Anisian"),
    ("Triassic",      "Lower Triassic",        "Olenekian"),
    ("Triassic",      "Lower Triassic",        "Induan"),
    ("Permian",       "Lopingian",             "Changhsingian"),
    ("Permian",       "Lopingian",             "Wuchiapingian"),
    ("Permian",       "Guadalupian",           "Capitanian"),
    ("Permian",       "Guadalupian",           "Wordian"),
    ("Permian",       "Guadalupian",           "Roadian"),
    ("Permian",       "Cisuralian",            "Kungurian"),
    ("Permian",       "Cisuralian",            "Artinskian"),
    ("Permian",       "Cisuralian",            "Sakmarian"),
    ("Permian",       "Cisuralian",            "Asselian"),
    ("Carboniferous", "Upper Pennsylvanian",   "Gzhelian"),
    ("Carboniferous", "Upper Pennsylvanian",   "Kasimovian"),
    ("Carboniferous", "Middle Pennsylvanian",  "Moscovian"),
    ("Carboniferous", "Middle Pennsylvanian",  "Moscovian"),
    ("Carboniferous", "Middle Pennsylvanian",  "Moscovian"),
    ("Carboniferous", "Lower Pennsylvanian",   "Bashkirian"),
]

COALFIELD_COLS = [
    ("Samcheok coalfield",                "samcheok_fm"),
    ("Gangreung coalfield",               "gangreung_fm"),
    ("Jeongseon-Pyeongchang coalfield",   "jeongseon_fm"),
    ("Yeongweol coalfield",               "yeongweol_fm"),
    ("Jecheon area",                      "jecheon_fm"),
    ("Danyang coalfield",                 "danyang_fm"),
    ("Mungyeong coalfield",               "mungyeong_fm"),
    ("Boeun coalfield",                   "boeun_fm"),
    ("Western Boeun area",                "western_boeun_fm"),
    ("Wanju-Geumsan area",                "wanju_geumsan_fm"),
    ("Hwasun coalfield",                  "hwasun_fm"),
    ("Boseong area",                      "boseong_fm"),
    ("Haenam-Gangjin area",               "haenam_gangjin_fm"),
]


def build_pyeongan_correlation(conn):
    with open(DATA_DIR / "pyeongan_supergroup.json", encoding="utf-8") as f:
        source = json.load(f)

    # For each coalfield, separate Moscovian formations from others
    coalfield_data = {}
    for cf in source["coalfields"]:
        stage_map = {}       # stage -> formation name (non-Moscovian)
        moscovian_fms = []   # formations at Moscovian, youngest-first

        for fm in cf["formations"]:  # JSON order = youngest first
            stages = normalize_list(fm["age"]["stage"])
            if "Moscovian" in stages:
                moscovian_fms.append(fm["name"])
            for stage in stages:
                if stage != "Moscovian" and stage not in stage_map:
                    stage_map[stage] = fm["name"]

        coalfield_data[cf["name"]] = {
            "stage_map": stage_map,
            "moscovian_fms": moscovian_fms,
        }

    # Build row data
    rows = []
    moscovian_idx = 0
    for period, epoch, stage in PYEONGAN_STAGE_ROWS:
        row = {"period": period, "epoch": epoch, "stage": stage}

        for cf_name, col_name in COALFIELD_COLS:
            cd = coalfield_data.get(cf_name, {"stage_map": {}, "moscovian_fms": []})

            if stage == "Moscovian":
                fms = cd["moscovian_fms"]
                n = len(fms)
                if n == 0:
                    row[col_name] = ""
                elif n == 1:
                    row[col_name] = fms[0]              # spans all 3 sub-rows
                elif n == 2:
                    row[col_name] = fms[0] if moscovian_idx == 0 else fms[1]
                else:  # n >= 3
                    row[col_name] = fms[min(moscovian_idx, n - 1)]
            else:
                row[col_name] = cd["stage_map"].get(stage, "")

        rows.append(row)
        moscovian_idx = (moscovian_idx + 1) if stage == "Moscovian" else 0

    # Create table
    col_defs = ["row_num INTEGER PRIMARY KEY"]
    col_defs += ["period TEXT", "period_rowspan INTEGER DEFAULT 0"]
    col_defs += ["epoch TEXT", "epoch_rowspan INTEGER DEFAULT 0"]
    col_defs += ["stage TEXT", "stage_rowspan INTEGER DEFAULT 0"]
    for _, col_name in COALFIELD_COLS:
        col_defs += [f"{col_name} TEXT", f"{col_name}_rowspan INTEGER DEFAULT 0"]

    conn.execute("DROP TABLE IF EXISTS pyeongan_correlation")
    conn.execute(f"CREATE TABLE pyeongan_correlation ({', '.join(col_defs)})")

    # Compute rowspans
    n = len(rows)
    period_spans = compute_rowspans([r["period"] for r in rows])
    epoch_spans = compute_rowspans([r["epoch"] for r in rows])
    stage_spans = compute_rowspans([r["stage"] for r in rows])

    cf_spans = {}
    for _, col_name in COALFIELD_COLS:
        cf_spans[col_name] = compute_rowspans([r[col_name] for r in rows])

    # Insert
    for i, row in enumerate(rows):
        values = [i]
        values += [row["period"], period_spans[i]]
        values += [row["epoch"], epoch_spans[i]]
        values += [row["stage"], stage_spans[i]]
        for _, col_name in COALFIELD_COLS:
            values += [row[col_name], cf_spans[col_name][i]]

        placeholders = ",".join(["?"] * len(values))
        conn.execute(f"INSERT INTO pyeongan_correlation VALUES ({placeholders})", values)

    conn.commit()

    # Summary
    print(f"\n── Pyeongan correlation chart ──")
    print(f"  {n} rows × {len(COALFIELD_COLS)} coalfields")
    for i, row in enumerate(rows):
        fms = [row[col] or "-" for _, col in COALFIELD_COLS]
        active = sum(1 for f in fms if f != "-")
        print(f"  [{i:2d}] {row['stage']:20s}  {active:2d} fms  |  {' | '.join(f[:6] for f in fms[:7])}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    conn = sqlite3.connect(str(DB_PATH))
    build_joseon_correlation(conn)
    build_pyeongan_correlation(conn)
    conn.close()
    print(f"\n-> {DB_PATH}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build pre-computed correlation chart rows for the Taebaeksan Basin.

Each row = one biozone slot in the chart.
Rowspan values are computed for period, stage, and formation columns.
Reads source data from data/correlation_chart.json.
"""

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = ROOT / "kstrati.db"


def load_raw_rows():
    with open(DATA_DIR / "correlation_chart.json", encoding="utf-8") as f:
        data = json.load(f)
    return [tuple(row) for row in data["rows"]]


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


def create_table(conn):
    conn.execute("DROP TABLE IF EXISTS correlation_chart")
    conn.execute("""
        CREATE TABLE correlation_chart (
            row_num             INTEGER PRIMARY KEY,
            period              TEXT,
            period_rowspan      INTEGER DEFAULT 0,
            stage               TEXT,
            stage_rowspan       INTEGER DEFAULT 0,
            taebaek_fm          TEXT,
            taebaek_fm_rowspan  INTEGER DEFAULT 0,
            taebaek_bz          TEXT,
            yeongwol_fm         TEXT,
            yeongwol_fm_rowspan INTEGER DEFAULT 0,
            yeongwol_bz         TEXT
        )
    """)


def populate(conn, raw_rows):
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


def print_summary(conn, raw_rows):
    print("── Correlation chart ──")
    print(f"  {len(raw_rows)} rows")
    for row in conn.execute("SELECT * FROM correlation_chart ORDER BY row_num"):
        parts = []
        if row[2]: parts.append(f"P:{row[1]}({row[2]})")
        if row[4]: parts.append(f"S:{row[3]}({row[4]})")
        if row[6]: parts.append(f"TF:{row[5]}({row[6]})")
        parts.append(f"TB:{row[7] or '-':25s}")
        if row[9]: parts.append(f"YF:{row[8]}({row[9]})")
        parts.append(f"YB:{row[10] or '-'}")
        print(f"  [{row[0]:2d}] {' | '.join(parts)}")


def main():
    raw_rows = load_raw_rows()
    conn = sqlite3.connect(str(DB_PATH))
    create_table(conn)
    populate(conn, raw_rows)
    print_summary(conn, raw_rows)
    conn.close()
    print(f"\n-> {DB_PATH}")


if __name__ == "__main__":
    main()

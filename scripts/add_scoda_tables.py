#!/usr/bin/env python3
"""Add SCODA metadata tables and UI manifest to kstrati.db."""

import argparse
import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "kstrati.db"

ASSERTION_VERSION = "0.1.2"

NOW = datetime.now(timezone.utc).isoformat()
TODAY = str(date.today())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  1. Schema creation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_scoda_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS artifact_metadata (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
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

        CREATE TABLE IF NOT EXISTS schema_descriptions (
            table_name  TEXT NOT NULL,
            column_name TEXT,
            description TEXT NOT NULL,
            PRIMARY KEY (table_name, column_name)
        );

        CREATE TABLE IF NOT EXISTS ui_display_intent (
            id           INTEGER PRIMARY KEY,
            entity       TEXT NOT NULL,
            default_view TEXT NOT NULL,
            description  TEXT,
            source_query TEXT,
            priority     INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS ui_queries (
            id          INTEGER PRIMARY KEY,
            name        TEXT NOT NULL UNIQUE,
            description TEXT,
            sql         TEXT NOT NULL,
            params_json TEXT,
            created_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ui_manifest (
            name         TEXT PRIMARY KEY,
            description  TEXT,
            manifest_json TEXT NOT NULL,
            created_at   TEXT NOT NULL
        );
    """)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2. Metadata population
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def populate_artifact_metadata(conn, version: str):
    metadata = [
        ("artifact_id", "kstrati"),
        ("name", "KStrati"),
        ("version", version),
        ("schema_version", "1.0"),
        ("created_at", TODAY),
        ("description", "Korean stratigraphic and biozone database for the Taebaeksan Basin (Cambrian-Ordovician)"),
        ("license", "CC-BY-4.0"),
    ]
    for key, value in metadata:
        conn.execute("INSERT OR REPLACE INTO artifact_metadata (key, value) VALUES (?,?)", (key, value))


def populate_provenance(conn):
    sources = [
        (1, "primary", "Choi (2011)",
         "Choi, D.K. (2011) A new view on the early Paleozoic paleogeography and paleoenvironments of the Taebaeksan Basin, Korea. "
         "Journal of the Paleontological Society of Korea, 27(1), 1–11.",
         "태백산분지의 전기 고생대 고지리, 고환경에 관한 새로운 견해 — primary reference for litho- and biostratigraphic correlation of Taebaek and Yeongwol groups",
         2011, None),
    ]
    for s in sources:
        conn.execute(
            "INSERT OR REPLACE INTO provenance (id, source_type, short_name, citation, description, year, url) VALUES (?,?,?,?,?,?,?)", s)


def populate_schema_descriptions(conn):
    descs = [
        # -- strat_units --
        ("strat_units", None, "Lithostratigraphic units: groups and formations of the Taebaeksan Basin"),
        ("strat_units", "id", "Primary key"),
        ("strat_units", "name", "Unit name (romanized)"),
        ("strat_units", "name_ko", "Unit name (Korean)"),
        ("strat_units", "rank", "Stratigraphic rank: 'group' or 'formation'"),
        ("strat_units", "alt_name", "Alternative name (romanized), e.g. Myeonsan for Jangsan"),
        ("strat_units", "alt_name_ko", "Alternative name (Korean)"),
        ("strat_units", "faunal_province", "Faunal province: Hwangho (shallow) or Jiangnan (deep-water)"),
        ("strat_units", "facies", "Depositional facies description"),
        # -- strat_edge_cache --
        ("strat_edge_cache", None, "Provenance-dependent stratigraphic hierarchy (parent-child, ordering, prev/next links)"),
        ("strat_edge_cache", "provenance_id", "FK to provenance.id — which source defines this hierarchy"),
        ("strat_edge_cache", "child_id", "FK to strat_units.id — the unit being placed in the hierarchy"),
        ("strat_edge_cache", "parent_id", "FK to strat_units.id — parent unit (formation→group)"),
        ("strat_edge_cache", "prev_id", "FK to strat_units.id — next older (lower) unit within the same parent"),
        ("strat_edge_cache", "next_id", "FK to strat_units.id — next younger (upper) unit within the same parent"),
        ("strat_edge_cache", "sort_order", "Display order within parent (0 = youngest/top)"),
        # -- biozones --
        ("biozones", None, "Biozones: independent temporal markers based on index fossils"),
        ("biozones", "id", "Primary key"),
        ("biozones", "name", "Biozone name (index taxon)"),
        ("biozones", "prev_id", "FK to next older biozone within the same group sequence"),
        ("biozones", "next_id", "FK to next younger biozone within the same group sequence"),
        ("biozones", "note", "Additional notes, e.g. cross-group correlation significance"),
        # -- biozone_occurrences --
        ("biozone_occurrences", None, "Many-to-many association between biozones and formations"),
        ("biozone_occurrences", "id", "Primary key"),
        ("biozone_occurrences", "biozone_id", "FK to biozones.id"),
        ("biozone_occurrences", "formation_id", "FK to strat_units.id (must be a formation)"),
        ("biozone_occurrences", "provenance_id", "FK to provenance.id — source of this occurrence record"),
        ("biozone_occurrences", "basis", "How the occurrence was established: 'stated' (explicitly described in source), 'chart_inferred' (read from correlation chart), 'composite' (synthesized from multiple sources)"),
        # -- age_assignments --
        ("age_assignments", None, "ICS chronostratigraphic age assignments for formations and biozones"),
        ("age_assignments", "id", "Primary key"),
        ("age_assignments", "entity_type", "Type of entity: 'formation' or 'biozone'"),
        ("age_assignments", "entity_id", "ID of the entity in its respective table"),
        ("age_assignments", "ics_series", "ICS series name, e.g. 'Furongian', 'Lower Ordovician', 'Miaolingian'"),
        ("age_assignments", "ics_stage", "ICS stage name, e.g. 'Tremadocian', 'Paibian', 'Wuliuan'"),
        ("age_assignments", "stage_original", "Original publication term if different from ICS, e.g. 'Arenigian'"),
        ("age_assignments", "age_relation", "Relationship: 'within', 'spans', 'base', 'top'"),
        ("age_assignments", "provenance_id", "FK to provenance.id — source of this age assignment"),
        ("age_assignments", "basis", "How the assignment was established: 'stated' (explicitly described), 'chart_inferred' (read from correlation chart), 'gssp_definition' (follows from GSSP boundary), 'composite' (synthesized from multiple sources)"),
    ]
    for table_name, column_name, desc in descs:
        conn.execute(
            "INSERT OR REPLACE INTO schema_descriptions (table_name, column_name, description) VALUES (?,?,?)",
            (table_name, column_name, desc))


def populate_display_intent(conn):
    intents = [
        (1, "stratigraphy", "tree", "Group-Formation hierarchy as primary view", "strat_tree", 0),
        (2, "formations", "table", "Flat formation list for search", "formations_list", 1),
        (3, "biozones", "table", "Biozone list with formation associations", "biozones_list", 1),
    ]
    for i in intents:
        conn.execute(
            "INSERT OR REPLACE INTO ui_display_intent (id, entity, default_view, description, source_query, priority) VALUES (?,?,?,?,?,?)", i)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  3. Named queries
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

QUERIES = [
    # -- Provenance selector (for global_controls dropdown) --
    {
        "name": "provenance_selector",
        "description": "List provenance sources for dropdown selector",
        "sql": """
            SELECT id, short_name, source_type, year
            FROM provenance
            WHERE COALESCE(:provenance_id, 1) > 0
            ORDER BY id
        """,
    },
    # -- Tree / hierarchy --
    {
        "name": "strat_tree",
        "description": "Group-Formation hierarchy for tree view",
        "sql": """
            SELECT u.id, u.name, u.name_ko, u.rank,
                   e.parent_id, e.sort_order,
                   u.faunal_province, u.facies,
                   (SELECT COUNT(*) FROM biozone_occurrences bo
                    WHERE bo.formation_id = u.id
                      AND bo.provenance_id = COALESCE(:provenance_id, bo.provenance_id)) AS biozone_count
            FROM strat_units u
            JOIN strat_edge_cache e ON e.child_id = u.id
                AND e.provenance_id = COALESCE(:provenance_id, 1)
            ORDER BY e.sort_order
        """,
    },
    # -- Formation list --
    {
        "name": "formations_list",
        "description": "All formations with group and age info",
        "sql": """
            SELECT f.id, f.name, f.name_ko,
                   g.name AS group_name,
                   g.faunal_province,
                   prev.name AS prev_formation,
                   nxt.name AS next_formation,
                   GROUP_CONCAT(DISTINCT a.ics_stage) AS stages,
                   GROUP_CONCAT(DISTINCT COALESCE(a.stage_original, a.ics_stage)) AS stages_original
            FROM strat_units f
            JOIN strat_edge_cache e ON e.child_id = f.id
                AND e.provenance_id = COALESCE(:provenance_id, 1)
            JOIN strat_units g ON e.parent_id = g.id
            LEFT JOIN strat_units prev ON e.prev_id = prev.id
            LEFT JOIN strat_units nxt ON e.next_id = nxt.id
            LEFT JOIN age_assignments a ON a.entity_type = 'formation' AND a.entity_id = f.id
                AND a.provenance_id = COALESCE(:provenance_id, a.provenance_id)
            WHERE f.rank = 'formation'
            GROUP BY f.id
            ORDER BY g.id, f.id
        """,
    },
    # -- Biozones list --
    {
        "name": "biozones_list",
        "description": "All biozones with formation occurrences",
        "sql": """
            SELECT b.id, b.name,
                   GROUP_CONCAT(u.name, ', ') AS formations,
                   GROUP_CONCAT(g.name, ', ') AS groups,
                   prev.name AS prev_biozone,
                   nxt.name AS next_biozone,
                   b.note
            FROM biozones b
            LEFT JOIN biozones prev ON b.prev_id = prev.id
            LEFT JOIN biozones nxt ON b.next_id = nxt.id
            LEFT JOIN biozone_occurrences bo ON bo.biozone_id = b.id
                AND bo.provenance_id = COALESCE(:provenance_id, bo.provenance_id)
            LEFT JOIN strat_units u ON bo.formation_id = u.id
            LEFT JOIN strat_edge_cache ue ON ue.child_id = u.id
                AND ue.provenance_id = COALESCE(:provenance_id, 1)
            LEFT JOIN strat_units g ON ue.parent_id = g.id
            GROUP BY b.id
            ORDER BY b.id
        """,
    },
    # -- Formation detail --
    {
        "name": "formation_detail",
        "description": "Full detail for a single formation",
        "sql": """
            SELECT f.id, f.name, f.name_ko, f.rank,
                   f.alt_name, f.alt_name_ko,
                   g.name AS group_name, g.name_ko AS group_name_ko,
                   g.faunal_province, g.facies,
                   prev.name AS prev_formation, prev.name_ko AS prev_formation_ko,
                   nxt.name AS next_formation, nxt.name_ko AS next_formation_ko
            FROM strat_units f
            JOIN strat_edge_cache e ON e.child_id = f.id
                AND e.provenance_id = COALESCE(:provenance_id, 1)
            JOIN strat_units g ON e.parent_id = g.id
            LEFT JOIN strat_units prev ON e.prev_id = prev.id
            LEFT JOIN strat_units nxt ON e.next_id = nxt.id
            WHERE f.id = :id
        """,
        "params": {"id": None},
    },
    # -- Biozones for a formation --
    {
        "name": "formation_biozones",
        "description": "Biozones occurring in a specific formation",
        "sql": """
            SELECT b.id, b.name,
                   prev.name AS prev_biozone,
                   nxt.name AS next_biozone,
                   b.note,
                   bo.basis,
                   p.citation AS provenance
            FROM biozone_occurrences bo
            JOIN biozones b ON bo.biozone_id = b.id
            LEFT JOIN biozones prev ON b.prev_id = prev.id
            LEFT JOIN biozones nxt ON b.next_id = nxt.id
            LEFT JOIN provenance p ON bo.provenance_id = p.id
            WHERE bo.formation_id = :formation_id
              AND bo.provenance_id = COALESCE(:provenance_id, bo.provenance_id)
            ORDER BY b.id
        """,
        "params": {"formation_id": None},
    },
    # -- Age assignments for a formation --
    {
        "name": "formation_ages",
        "description": "ICS age assignments for a specific formation",
        "sql": """
            SELECT a.id, a.ics_series, a.ics_stage, a.stage_original, a.age_relation,
                   a.basis,
                   p.citation AS provenance
            FROM age_assignments a
            LEFT JOIN provenance p ON a.provenance_id = p.id
            WHERE a.entity_type = 'formation' AND a.entity_id = :id
              AND a.provenance_id = COALESCE(:provenance_id, a.provenance_id)
            ORDER BY a.id
        """,
        "params": {"id": None},
    },
    # -- Biozone detail --
    {
        "name": "biozone_detail",
        "description": "Full detail for a single biozone",
        "sql": """
            SELECT b.id, b.name,
                   prev.name AS prev_biozone,
                   nxt.name AS next_biozone,
                   b.note
            FROM biozones b
            LEFT JOIN biozones prev ON b.prev_id = prev.id
            LEFT JOIN biozones nxt ON b.next_id = nxt.id
            WHERE b.id = :id
              AND COALESCE(:provenance_id, 1) > 0
        """,
        "params": {"id": None},
    },
    # -- Formations containing a biozone --
    {
        "name": "biozone_formations",
        "description": "Formations where a specific biozone occurs",
        "sql": """
            SELECT f.id, f.name, f.name_ko,
                   g.name AS group_name, g.faunal_province,
                   bo.basis,
                   p.citation AS provenance
            FROM biozone_occurrences bo
            JOIN strat_units f ON bo.formation_id = f.id
            JOIN strat_edge_cache e ON e.child_id = f.id
                AND e.provenance_id = COALESCE(:provenance_id, 1)
            JOIN strat_units g ON e.parent_id = g.id
            LEFT JOIN provenance p ON bo.provenance_id = p.id
            WHERE bo.biozone_id = :biozone_id
              AND bo.provenance_id = COALESCE(:provenance_id, bo.provenance_id)
            ORDER BY g.id, f.id
        """,
        "params": {"biozone_id": None},
    },
    # -- Cross-group correlation biozones --
    {
        "name": "correlation_biozones",
        "description": "Biozones that occur in more than one group (correlation markers)",
        "sql": """
            SELECT b.id, b.name, b.note,
                   GROUP_CONCAT(u.name, ', ') AS formations,
                   GROUP_CONCAT(g.name, ', ') AS groups
            FROM biozones b
            JOIN biozone_occurrences bo ON bo.biozone_id = b.id
                AND bo.provenance_id = COALESCE(:provenance_id, bo.provenance_id)
            JOIN strat_units u ON bo.formation_id = u.id
            JOIN strat_edge_cache ue ON ue.child_id = u.id
                AND ue.provenance_id = COALESCE(:provenance_id, 1)
            JOIN strat_units g ON ue.parent_id = g.id
            GROUP BY b.id
            HAVING COUNT(DISTINCT g.id) > 1
        """,
    },
    # -- Correlation chart (Joseon) --
    {
        "name": "correlation_chart",
        "description": "Pre-computed correlation chart rows with rowspan values (Joseon Supergroup)",
        "sql": """
            SELECT row_num,
                   period, period_rowspan,
                   stage, stage_rowspan,
                   taebaek_fm, taebaek_fm_rowspan, taebaek_bz,
                   yeongwol_fm, yeongwol_fm_rowspan, yeongwol_bz
            FROM correlation_chart
            WHERE provenance_id = COALESCE(:provenance_id, 1)
            ORDER BY row_num
        """,
    },
    # -- Correlation chart (Pyeongan) --
    {
        "name": "pyeongan_correlation_chart",
        "description": "Stage-based correlation chart for the Pyeongan Supergroup across 13 coalfields",
        "sql": """
            SELECT row_num,
                   period, period_rowspan,
                   epoch, epoch_rowspan,
                   stage, stage_rowspan,
                   samcheok_fm, samcheok_fm_rowspan,
                   gangreung_fm, gangreung_fm_rowspan,
                   jeongseon_fm, jeongseon_fm_rowspan,
                   yeongweol_fm, yeongweol_fm_rowspan,
                   jecheon_fm, jecheon_fm_rowspan,
                   danyang_fm, danyang_fm_rowspan,
                   mungyeong_fm, mungyeong_fm_rowspan,
                   boeun_fm, boeun_fm_rowspan,
                   western_boeun_fm, western_boeun_fm_rowspan,
                   wanju_geumsan_fm, wanju_geumsan_fm_rowspan,
                   hwasun_fm, hwasun_fm_rowspan,
                   boseong_fm, boseong_fm_rowspan,
                   haenam_gangjin_fm, haenam_gangjin_fm_rowspan
            FROM pyeongan_correlation
            WHERE COALESCE(:provenance_id, 2) > 0
            ORDER BY row_num
        """,
    },
]


def populate_queries(conn):
    for q in QUERIES:
        params_json = json.dumps(q["params"]) if q.get("params") else None
        conn.execute(
            "INSERT OR REPLACE INTO ui_queries (name, description, sql, params_json, created_at) VALUES (?,?,?,?,?)",
            (q["name"], q["description"], q["sql"], params_json, NOW))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  4. UI Manifest
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MANIFEST = {
    "default_view": "strat_tree",
    "global_controls": [
        {
            "type": "select",
            "param": "provenance_id",
            "label": "Provenance",
            "source_query": "provenance_selector",
            "value_key": "id",
            "label_key": "short_name",
            "default": 1,
        },
    ],
    "views": {
        # ── Stratigraphy tree ──
        "strat_tree": {
            "type": "hierarchy",
            "display": "tree",
            "title": "Stratigraphy",
            "description": "Group-Formation hierarchy of the Taebaeksan Basin",
            "source_query": "strat_tree",
            "icon": "bi-layers",
            "hierarchy_options": {
                "id_key": "id",
                "parent_key": "parent_id",
                "label_key": "name",
                "rank_key": "rank",
                "sort_by": "order_key",
                "order_key": "sort_order",
            },
            "tree_display": {
                "leaf_rank": "formation",
                "count_key": "biozone_count",
                "on_node_info": {
                    "detail_view": "formation_detail",
                    "id_key": "id",
                },
                "item_query": "formation_biozones",
                "item_param": "formation_id",
                "item_columns": [
                    {"key": "name", "label": "Biozone", "italic": True},
                    {"key": "prev_biozone", "label": "Prev (older)"},
                    {"key": "next_biozone", "label": "Next (younger)"},
                    {"key": "note", "label": "Note", "truncate": 40},
                ],
                "on_item_click": {
                    "detail_view": "biozone_detail",
                    "id_key": "id",
                },
            },
        },
        # ── Correlation chart (provenance-variant) ──
        "correlation_chart": {
            "type": "hierarchy",
            "display": "correlation",
            "title": "Correlation Chart",
            "description": "Chronostratigraphic–lithostratigraphic correlation",
            "icon": "bi-layout-three-columns",
            "variant_key": "provenance_id",
            "default_variant": "1",
            "variants": {
                "1": {
                    "description": "Joseon Supergroup — Taebaek and Yeongwol groups (Cambrian–Ordovician)",
                    "source_query": "correlation_chart",
                    "correlation_display": {
                        "column_groups": [
                            {"label": "AGE", "colspan": 2},
                            {"label": "Taebaek Group (태백층군)", "colspan": 2},
                            {"label": "Yeongwol Group (영월층군)", "colspan": 2},
                        ],
                        "columns": [
                            {"key": "period", "label": "", "rowspan_key": "period_rowspan", "css_class": "corr-period"},
                            {"key": "stage", "label": "Stage", "rowspan_key": "stage_rowspan", "css_class": "corr-stage"},
                            {"key": "taebaek_fm", "label": "Formation", "rowspan_key": "taebaek_fm_rowspan", "css_class": "corr-fm"},
                            {"key": "taebaek_bz", "label": "Biozone", "css_class": "corr-bz", "italic": True, "border_follow": "taebaek_fm_rowspan", "border_bottom_values": ["Fenghuangella"]},
                            {"key": "yeongwol_fm", "label": "Formation", "rowspan_key": "yeongwol_fm_rowspan", "css_class": "corr-fm"},
                            {"key": "yeongwol_bz", "label": "Biozone", "css_class": "corr-bz", "italic": True, "border_follow": "yeongwol_fm_rowspan", "border_bottom_values": ["Glyptagnostus reticulatus"]},
                        ],
                    },
                },
                "2": {
                    "description": "Pyeongan Supergroup — coalfield correlation (Carboniferous–Triassic)",
                    "source_query": "pyeongan_correlation_chart",
                    "correlation_display": {
                        "column_groups": [
                            {"label": "AGE", "colspan": 3},
                            {"label": "삼척", "colspan": 1},
                            {"label": "강릉", "colspan": 1},
                            {"label": "정선-평창", "colspan": 1},
                            {"label": "영월", "colspan": 1},
                            {"label": "제천", "colspan": 1},
                            {"label": "단양", "colspan": 1},
                            {"label": "문경", "colspan": 1},
                            {"label": "보은", "colspan": 1},
                            {"label": "보은서부", "colspan": 1},
                            {"label": "완주-금산", "colspan": 1},
                            {"label": "화순", "colspan": 1},
                            {"label": "보성", "colspan": 1},
                            {"label": "해남-강진", "colspan": 1},
                        ],
                        "columns": [
                            {"key": "period", "label": "", "rowspan_key": "period_rowspan", "css_class": "corr-period"},
                            {"key": "epoch", "label": "Epoch", "rowspan_key": "epoch_rowspan", "css_class": "corr-stage"},
                            {"key": "stage", "label": "Stage", "rowspan_key": "stage_rowspan", "css_class": "corr-stage"},
                            {"key": "samcheok_fm", "label": "Formation", "rowspan_key": "samcheok_fm_rowspan", "css_class": "corr-fm"},
                            {"key": "gangreung_fm", "label": "Formation", "rowspan_key": "gangreung_fm_rowspan", "css_class": "corr-fm"},
                            {"key": "jeongseon_fm", "label": "Formation", "rowspan_key": "jeongseon_fm_rowspan", "css_class": "corr-fm"},
                            {"key": "yeongweol_fm", "label": "Formation", "rowspan_key": "yeongweol_fm_rowspan", "css_class": "corr-fm"},
                            {"key": "jecheon_fm", "label": "Formation", "rowspan_key": "jecheon_fm_rowspan", "css_class": "corr-fm"},
                            {"key": "danyang_fm", "label": "Formation", "rowspan_key": "danyang_fm_rowspan", "css_class": "corr-fm"},
                            {"key": "mungyeong_fm", "label": "Formation", "rowspan_key": "mungyeong_fm_rowspan", "css_class": "corr-fm"},
                            {"key": "boeun_fm", "label": "Formation", "rowspan_key": "boeun_fm_rowspan", "css_class": "corr-fm"},
                            {"key": "western_boeun_fm", "label": "Formation", "rowspan_key": "western_boeun_fm_rowspan", "css_class": "corr-fm"},
                            {"key": "wanju_geumsan_fm", "label": "Formation", "rowspan_key": "wanju_geumsan_fm_rowspan", "css_class": "corr-fm"},
                            {"key": "hwasun_fm", "label": "Formation", "rowspan_key": "hwasun_fm_rowspan", "css_class": "corr-fm"},
                            {"key": "boseong_fm", "label": "Formation", "rowspan_key": "boseong_fm_rowspan", "css_class": "corr-fm"},
                            {"key": "haenam_gangjin_fm", "label": "Formation", "rowspan_key": "haenam_gangjin_fm_rowspan", "css_class": "corr-fm"},
                        ],
                    },
                },
            },
        },
        # ── Formations table ──
        "formations_table": {
            "type": "table",
            "title": "Formations",
            "description": "All formations with age and group info",
            "source_query": "formations_list",
            "icon": "bi-stack",
            "columns": [
                {"key": "name", "label": "Formation", "sortable": True, "searchable": True},
                {"key": "name_ko", "label": "Korean", "sortable": True, "searchable": True},
                {"key": "group_name", "label": "Group", "sortable": True, "searchable": True},
                {"key": "faunal_province", "label": "Province", "sortable": True},
                {"key": "stages", "label": "ICS Stage(s)", "sortable": True},
                {"key": "stages_original", "label": "Original", "sortable": True},
                {"key": "prev_formation", "label": "Prev (older)"},
                {"key": "next_formation", "label": "Next (younger)"},
            ],
            "default_sort": {"key": "name", "direction": "asc"},
            "searchable": True,
            "on_row_click": {
                "detail_view": "formation_detail",
                "id_key": "id",
            },
        },
        # ── Biozones table ──
        "biozones_table": {
            "type": "table",
            "title": "Biozones",
            "description": "All biozones with formation associations",
            "source_query": "biozones_list",
            "icon": "bi-bug",
            "columns": [
                {"key": "name", "label": "Biozone", "sortable": True, "searchable": True, "italic": True},
                {"key": "formations", "label": "Formation(s)", "sortable": True, "searchable": True},
                {"key": "groups", "label": "Group(s)", "sortable": True},
                {"key": "prev_biozone", "label": "Prev (older)"},
                {"key": "next_biozone", "label": "Next (younger)"},
                {"key": "note", "label": "Note", "truncate": 50},
            ],
            "default_sort": {"key": "name", "direction": "asc"},
            "searchable": True,
            "on_row_click": {
                "detail_view": "biozone_detail",
                "id_key": "id",
            },
        },
        # ── Formation detail ──
        "formation_detail": {
            "type": "detail",
            "title": "Formation Detail",
            "source_query": "formation_detail",
            "source_param": "id",
            "title_template": {
                "format": "{name} ({name_ko})",
            },
            "sub_queries": {
                "biozones": {
                    "query": "formation_biozones",
                    "params": {"formation_id": "id"},
                },
                "ages": {
                    "query": "formation_ages",
                    "params": {"id": "id"},
                },
            },
            "sections": [
                {
                    "title": "Basic Information",
                    "type": "field_grid",
                    "fields": [
                        {"key": "name", "label": "Name"},
                        {"key": "name_ko", "label": "Korean Name"},
                        {"key": "alt_name", "label": "Alternative Name", "condition": "alt_name"},
                        {"key": "group_name", "label": "Group"},
                        {"key": "faunal_province", "label": "Faunal Province"},
                        {"key": "facies", "label": "Facies"},
                        {"key": "prev_formation", "label": "Below (older)"},
                        {"key": "next_formation", "label": "Above (younger)"},
                    ],
                },
                {
                    "title": "Age Assignments",
                    "type": "linked_table",
                    "data_key": "ages",
                    "columns": [
                        {"key": "ics_series", "label": "ICS Series"},
                        {"key": "ics_stage", "label": "ICS Stage"},
                        {"key": "stage_original", "label": "Original Term"},
                        {"key": "age_relation", "label": "Relation"},
                    ],
                },
                {
                    "title": "Biozones",
                    "type": "linked_table",
                    "data_key": "biozones",
                    "columns": [
                        {"key": "name", "label": "Biozone", "italic": True},
                        {"key": "prev_biozone", "label": "Prev (older)"},
                        {"key": "next_biozone", "label": "Next (younger)"},
                        {"key": "note", "label": "Note"},
                    ],
                    "on_row_click": {
                        "detail_view": "biozone_detail",
                        "id_key": "id",
                    },
                },
                {
                    "title": "Annotations",
                    "type": "annotations",
                },
            ],
        },
        # ── Biozone detail ──
        "biozone_detail": {
            "type": "detail",
            "title": "Biozone Detail",
            "source_query": "biozone_detail",
            "source_param": "id",
            "title_template": {
                "format": "<i>{name}</i>",
            },
            "sub_queries": {
                "formations": {
                    "query": "biozone_formations",
                    "params": {"biozone_id": "id"},
                },
            },
            "sections": [
                {
                    "title": "Basic Information",
                    "type": "field_grid",
                    "fields": [
                        {"key": "name", "label": "Biozone Name", "format": "italic"},
                        {"key": "prev_biozone", "label": "Prev (older)"},
                        {"key": "next_biozone", "label": "Next (younger)"},
                        {"key": "note", "label": "Note", "condition": "note"},
                    ],
                },
                {
                    "title": "Occurrences",
                    "type": "linked_table",
                    "data_key": "formations",
                    "columns": [
                        {"key": "name", "label": "Formation"},
                        {"key": "name_ko", "label": "Korean"},
                        {"key": "group_name", "label": "Group"},
                        {"key": "faunal_province", "label": "Province"},
                    ],
                    "on_row_click": {
                        "detail_view": "formation_detail",
                        "id_key": "id",
                    },
                },
                {
                    "title": "Annotations",
                    "type": "annotations",
                },
            ],
        },
    },
}


def populate_manifest(conn):
    conn.execute(
        "INSERT OR REPLACE INTO ui_manifest (name, description, manifest_json, created_at) VALUES (?,?,?,?)",
        ("default", "Default UI manifest for KStrati SCODA viewer", json.dumps(MANIFEST, ensure_ascii=False), NOW))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def print_summary(conn):
    tables = ["artifact_metadata", "provenance", "schema_descriptions",
              "ui_display_intent", "ui_queries", "ui_manifest"]
    print("── SCODA metadata summary ──")
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {count} rows")

    print("\n── Named queries ──")
    for row in conn.execute("SELECT name, description FROM ui_queries ORDER BY id"):
        print(f"  {row[0]:25s}  {row[1]}")

    print("\n── Manifest views ──")
    manifest = json.loads(conn.execute("SELECT manifest_json FROM ui_manifest WHERE name='default'").fetchone()[0])
    for name, view in manifest["views"].items():
        print(f"  {name:25s}  type={view['type']:12s}  {view['title']}")


def main():
    parser = argparse.ArgumentParser(description="Add SCODA metadata to kstrati.db")
    parser.add_argument(
        "--version", default=ASSERTION_VERSION,
        help=f"Version string (default: {ASSERTION_VERSION})")
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys=ON")

    create_scoda_tables(conn)
    populate_artifact_metadata(conn, version=args.version)
    populate_provenance(conn)
    populate_schema_descriptions(conn)
    populate_display_intent(conn)
    populate_queries(conn)
    populate_manifest(conn)

    conn.commit()
    print_summary(conn)
    conn.close()
    print(f"\n-> {DB_PATH}  (version {args.version})")


if __name__ == "__main__":
    main()

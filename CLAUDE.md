# kstrati

Korean stratigraphic and biozone data, packaged as a SCODA (Self-Contained Data Artifact).

## Project Purpose

Organize Korean sedimentary basin stratigraphy (formations, biozones, age correlations) into a structured, queryable dataset. The primary focus is the Taebaeksan Basin (Taebaek Group + Yeongwol Group), covering Cambrian through Ordovician.

## SCODA Overview

SCODA is an architecture where **data is the primary artifact** — immutable, versioned, and self-describing. A `.scoda` package is a ZIP containing:

```
kstrati.scoda
├── manifest.json        # Package identity, version, checksum, dependencies
├── data.db              # SQLite database (canonical data + SCODA metadata tables)
└── assets/              # Optional SPA viewer
```

### Key SCODA Principles
- **Immutable canonical data**: each version is read-only; changes require a new release
- **Manifest-driven UI**: the data declares how viewers should display it (views, queries, columns)
- **Overlay annotations**: user notes stored in a separate `_overlay.db`, never touching canonical data
- **Multi-DB ATTACH**: at runtime, canonical + overlay + dependency DBs are joined via SQLite ATTACH

### SCODA Metadata Tables (in data.db)
| Table | Purpose |
|-------|---------|
| `artifact_metadata` | Package identity (key-value: name, version, license, etc.) |
| `provenance` | Data sources and citations |
| `schema_descriptions` | Human-readable descriptions for all tables/columns |
| `ui_display_intent` | Default view type hints per entity |
| `ui_queries` | Named parameterized SQL queries |
| `ui_manifest` | Complete declarative UI definition (JSON) |

### Dependencies
- **scoda-engine** (`../scoda-engine`): Core library (`scoda_engine_core`) and runtime (FastAPI server, MCP server, generic viewer)
- **paleocore** (shared infrastructure `.scoda`): Countries, regions, geological formations, ICS chronostratigraphy — attached as `pc` alias at runtime
- **trilobase** (`../trilobase`): Reference SCODA implementation for trilobite taxonomy; use as a model for manifest structure, build scripts, and UI patterns

## Data Model

### Core Entities

**Group → Formation** (strict hierarchy via parent_id):
- Group: Taebaek Group (태백층군), Yeongwol Group (영월층군)
- Formation: Jangsan, Myobong, Daegi, Sesong, Hwajeol, Dongjeom, Dumugol, Makgol, Jigunsan, Duwibong (Taebaek); Sambangsan, Machari, Wagok, Mungok, Yeongheung (Yeongwol)
- Formations have prev/next links (older/younger) within their Group

**Biozone** (independent entity, associated with formations):
- NOT a child of Formation — biozones are independent temporal markers
- Associated with formations via a junction table (many-to-many)
- Biozones have prev/next links (older/younger) within their Group's sequence
- Same biozone appearing in multiple Groups serves as a **cross-group correlation marker** (e.g., Kayseraspis in both Dumugol and Yeongheung)
- Biozones indicate relative age; they are not precise but serve as correlation tools

**Age** (ICS Chronostratigraphy):
- Follow the latest ICS standard
- Map legacy terms to ICS: "Arenigian" → Floian+Dapingian, "Cambrian Series 3" → Miaolingian
- Paleocore dependency provides ICS reference data

### Table Structure

| Table | Rows | Purpose |
|-------|------|---------|
| `strat_units` | 17 | Group(2) + Formation(15), parent_id hierarchy, prev/next/sort_order |
| `biozones` | 39 | Independent temporal markers, prev/next chain per group |
| `biozone_occurrences` | 40 | Many-to-many Formation-Biozone association |
| `age_assignments` | 25 | ICS stage mapping with original terms |
| `correlation_chart` | 28 | Pre-computed correlation chart rows with rowspan values |

`strat_units` includes a `sort_order` column for tree view ordering (hierarchy_options: `sort_by: "order_key"`, `order_key: "sort_order"`).

## Source Data

- `data/taebaeksan_basin.json` — Group/Formation hierarchy + Biozone definitions with occurrences
- `data/correlation_chart.json` — Correlation chart row layout (period, stage, formations, biozones per row)

## Build Pipeline

```
data/taebaeksan_basin.json ──→ scripts/create_database.py ──→ kstrati.db (data tables)
data/correlation_chart.json ─→ scripts/build_correlation.py ─→ kstrati.db (+ correlation_chart)
                                scripts/add_scoda_tables.py ──→ kstrati.db (+ SCODA metadata)
                                scripts/create_scoda.py ──────→ kstrati.scoda (ZIP package)
```

To rebuild everything:
```bash
python scripts/create_database.py
python scripts/build_correlation.py
python scripts/add_scoda_tables.py
python scripts/create_scoda.py
```

## UI Views (in manifest)

| View | Type | Description |
|------|------|-------------|
| `strat_tree` | hierarchy/tree | Group→Formation 트리, leaf에서 biozone 목록 |
| `correlation_chart` | hierarchy/correlation | 양쪽 Group 나란히 correlation table (scoda-engine 확장) |
| `formations_table` | table | 전체 Formation 목록 |
| `biozones_table` | table | 전체 Biozone 목록 |
| `formation_detail` | detail | Formation 상세 + ages/biozones sub-query |
| `biozone_detail` | detail | Biozone 상세 + formation occurrences |

### Correlation Chart (scoda-engine 확장)
- `display: "correlation"` — pre-computed rowspan 기반 테이블 렌더링 (renderCorrelationView in app.js)
- `border_follow`: biozone 셀 top border를 formation rowspan에 연동
- `border_bottom_values`: 특정 biozone 아래에만 border 표시

## Conventions

- Korean names stored in `name_ko` fields alongside romanized `name`
- Age data always records both ICS standard terms and original publication terms when they differ
- Biozone prev/next follows temporal order: prev = older, next = younger
- Formation prev/next follows the same convention within a Group
- Correlation chart layout is manually curated in `data/correlation_chart.json`

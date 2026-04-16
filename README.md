# KStrati

Korean stratigraphic and biozone database, packaged as a [SCODA](https://github.com/jikhanjung/scoda-engine) (Self-Contained Data Artifact).

## Overview

KStrati organizes lithostratigraphic and biostratigraphic data of Korean sedimentary basins into a structured, queryable dataset. Currently covers two supergroups:

### Joseon Supergroup (조선누층군) — Cambrian–Ordovician
- **Taebaek Group** (태백층군) — Hwangho Faunal Province, shallow marine facies (10 formations, 23 biozones)
- **Yeongwol Group** (영월층군) — Jiangnan Faunal Province, deep-water facies (5 formations, 17 biozones)
- Source: Choi (2011)

### Pyeongan Supergroup (평안누층군) — Carboniferous–Triassic
- 13 coalfields/areas across the southern Korean Peninsula
- 66 formation entries with ICS age assignments (no biozones)
- Source: Kim & Lee (2017)

## Features

- Group/Coalfield → Formation hierarchy with prev/next stratigraphic links
- Biozones as independent temporal markers with formation associations (when available)
- ICS chronostratigraphic age assignments (with original publication terms preserved)
- Correlation chart view with provenance-based variants: Joseon (biozone-level) or Pyeongan (stage-level, 13 coalfields)
- Provenance switching via global control

## Quick Start

### Build the database and package

```bash
python scripts/create_database.py
python scripts/build_correlation.py
python scripts/add_scoda_tables.py
python scripts/create_scoda.py
```

### View in ScodaDesktop

```bash
cd ../scoda-engine
python -m scoda_engine.serve --scoda-path ../kstrati/kstrati.scoda --port 8080
```

Open `http://localhost:8080` in a browser.

## Project Structure

```
kstrati/
├── data/
│   ├── joseon_supergroup.json      # Source: Joseon formations, biozones, ages
│   ├── pyeongan_supergroup.json    # Source: Pyeongan formations per coalfield
│   └── correlation_chart.json      # Source: Joseon correlation chart row layout
├── scripts/
│   ├── create_database.py          # JSON → SQLite data tables
│   ├── build_correlation.py        # Correlation charts → DB with rowspan
│   ├── add_scoda_tables.py         # SCODA metadata + manifest + named queries
│   └── create_scoda.py             # Package as .scoda ZIP
├── kstrati.db                      # SQLite database (built artifact)
├── dist/                           # Built .scoda packages
├── devlog/                         # Development log
└── CLAUDE.md                       # Project documentation for AI assistants
```

## Data Sources

- Choi, D.K. (2011) A new view on the early Paleozoic paleogeography and paleoenvironments of the Taebaeksan Basin, Korea. *J. Paleont. Soc. Korea*, 27(1), 1–11.
- Kim, M.G. & Lee, Y.I. (2017) The stratigraphy and correlation of the upper Paleozoic Pyeongan Supergroup of southern Korean Peninsula — A review. *J. Geol. Soc. Korea*, 53, 321–338.
- International Commission on Stratigraphy. International Chronostratigraphic Chart v2024/12.

## License

CC-BY-4.0

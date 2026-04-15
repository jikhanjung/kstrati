# KStrati

Korean stratigraphic and biozone database, packaged as a [SCODA](https://github.com/jikhanjung/scoda-engine) (Self-Contained Data Artifact).

## Overview

KStrati organizes lithostratigraphic and biostratigraphic data of the **Taebaeksan Basin** (Korea) into a structured, queryable dataset. The basin contains two contemporaneous depositional systems:

- **Taebaek Group** (태백층군) — Hwangho Faunal Province, shallow marine facies (10 formations, 23 biozones)
- **Yeongwol Group** (영월층군) — Jiangnan Faunal Province, deep-water facies (5 formations, 17 biozones)

Stratigraphic range: Cambrian Series 2 through Middle Ordovician (Darriwilian).

## Features

- Group-Formation hierarchy with prev/next stratigraphic links
- Biozones as independent temporal markers with formation associations
- ICS chronostratigraphic age assignments (with original publication terms preserved)
- Correlation chart view: side-by-side comparison of both groups aligned by biozone

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
│   ├── taebaeksan_basin.json    # Source: formations, biozones, age assignments
│   └── correlation_chart.json   # Source: correlation chart row layout
├── scripts/
│   ├── create_database.py       # JSON → SQLite data tables
│   ├── build_correlation.py     # Correlation chart → DB with rowspan
│   ├── add_scoda_tables.py      # SCODA metadata + manifest + named queries
│   └── create_scoda.py          # Package as .scoda ZIP
├── kstrati.db                   # SQLite database (built artifact)
├── kstrati.scoda                # SCODA package (built artifact)
├── devlog/                      # Development log
└── CLAUDE.md                    # Project documentation for AI assistants
```

## Data Sources

- Choi, D.K. (2019) *Trilobite Biostratigraphy of the Taebaeksan Basin, Korea*. Springer.
- International Commission on Stratigraphy. International Chronostratigraphic Chart v2024/12.

## License

CC-BY-4.0

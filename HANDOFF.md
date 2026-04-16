# Handoff — KStrati Project Status

Last updated: 2026-04-16

## Current State

태백산분지(조선누층군) + 남한 평안누층군 데이터가 SCODA 패키지로 빌드되어 동작한다. Provenance 전환으로 두 누층군 간 뷰가 자동 교체되며, Correlation Chart는 variant 패턴으로 provenance별 컬럼 구성이 달라진다.

### Completed

- [x] 데이터 모델 설계 (strat_units, biozones, biozone_occurrences, age_assignments, correlation_chart, pyeongan_correlation)
- [x] Source JSON 작성 (joseon_supergroup.json, correlation_chart.json, pyeongan_supergroup.json)
- [x] 빌드 파이프라인 4단계 (create_database → build_correlation → add_scoda_tables → create_scoda)
- [x] SCODA 메타데이터 + 12개 named query + 6개 UI view
- [x] Joseon Supergroup: 2 group × 15 formations, 39 biozones, correlation chart (28 rows)
- [x] Pyeongan Supergroup: 13 coalfields × 66 formations, correlation chart (18 rows)
- [x] Correlation chart variant 패턴: provenance_id에 따라 query + column 구성 자동 전환
- [x] scoda-engine에 resolveViewVariant() 추가
- [x] Provenance 연결: biozone_occurrences, age_assignments에 provenance_id + basis
  - Provenance 1: Choi (2011) — 조선누층군
  - Provenance 2: Kim & Lee (2017) — 평안누층군

### Not Yet Done

- [ ] Provenance를 UI에 노출 (detail view에서 출처·근거 표시)
- [ ] Correlation chart 미세 조정 (Pyeongan Moscovian sub-row 배치 등)
- [ ] 추가 분지/층군 데이터 확장
- [ ] paleocore 의존성 연결 (ICS chronostratigraphy 공유 데이터)
- [ ] MCP tools 정의 (mcp_tools.json)
- [ ] 문서 파일 내 파일명 참조 업데이트 (devlog 등에서 구 파일명 taebaeksan_basin.json 참조 잔존)

## How to Run

```bash
# 1. Rebuild DB + package
python scripts/create_database.py
python scripts/build_correlation.py
python scripts/add_scoda_tables.py
python scripts/create_scoda.py

# 2. Serve
cd ../scoda-engine
python -m scoda_engine.serve --scoda-path ../kstrati/kstrati.scoda --port 8080
```

## Key Files to Know

| File | Role |
|------|------|
| `data/joseon_supergroup.json` | 조선누층군 층서+biozone 원본 데이터 |
| `data/pyeongan_supergroup.json` | 평안누층군 13개 탄전별 층서 원본 데이터 |
| `data/correlation_chart.json` | 조선누층군 Correlation chart 행 배치 |
| `scripts/create_database.py` | DB 생성 + provenance seed + 양쪽 누층군 로드 |
| `scripts/build_correlation.py` | Joseon + Pyeongan correlation chart 빌드 |
| `scripts/add_scoda_tables.py` | Manifest, query, provenance 정의 (variant 패턴 포함) |
| `../scoda-engine/static/js/app.js` | Correlation 렌더러 + resolveViewVariant |

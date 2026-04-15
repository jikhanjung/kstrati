# Handoff — KStrati Project Status

Last updated: 2026-04-15

## Current State

프로젝트 초기 구축 완료. 태백산분지(태백층군 + 영월층군)의 층서-biozone 데이터가 SCODA 패키지로 빌드되어 ScodaDesktop에서 정상 동작한다. Provenance가 개별 데이터 레코드에 연결되어 출처 및 근거 유형을 추적할 수 있다.

### Completed

- [x] 데이터 모델 설계 (strat_units, biozones, biozone_occurrences, age_assignments, correlation_chart)
- [x] Source JSON 작성 (taebaeksan_basin.json, correlation_chart.json)
- [x] 빌드 파이프라인 4단계 (create_database → build_correlation → add_scoda_tables → create_scoda)
- [x] SCODA 메타데이터 + 10개 named query + 6개 UI view
- [x] Correlation chart: scoda-engine에 `display: "correlation"` 렌더러 추가 (커밋 완료: `ab79a47`)
  - rowspan 기반 hierarchical table
  - border_follow (같은 층 내 biozone 간 border 제거)
  - border_bottom_values (특정 biozone 아래 border 표시)
- [x] ScodaDesktop에서 .scoda 로드 및 전체 뷰 동작 확인
- [x] Biozone-Formation 배정 수정 (Shumardia/Kainella/Yosimurasapis → 문곡, Fatocephalus → 와곡)
- [x] Correlation chart 배치 반복 조정 (영흥~삼방산 span, 경계 위치 등)
- [x] Provenance 연결: biozone_occurrences, age_assignments에 provenance_id + basis 컬럼 추가
  - Primary provenance: Choi, D.K. (2011) J. Paleont. Soc. Korea, 27(1), 1–11
  - biozone_occurrences: basis='stated' (논문에서 명시)
  - age_assignments: basis='chart_inferred' (도표에서 유추)
  - basis 값 체계: stated, chart_inferred, gssp_definition, composite

### Not Yet Done

- [ ] Provenance를 UI에 노출 (detail view에서 출처·근거 표시)
- [ ] Correlation chart 미세 조정 가능성 (배치, 경계 등은 사용자 피드백에 따라)
- [ ] 추가 분지/층군 데이터 확장 (현재 태백산분지만)
- [ ] paleocore 의존성 연결 (ICS chronostratigraphy 공유 데이터)
- [ ] MCP tools 정의 (mcp_tools.json)

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
| `data/taebaeksan_basin.json` | 층서+biozone 원본 데이터 (편집 대상) |
| `data/correlation_chart.json` | Correlation chart 행 배치 (편집 대상) |
| `scripts/create_database.py` | DB 생성 + provenance seed + 데이터 로드 |
| `scripts/add_scoda_tables.py` | Manifest, query, provenance 정의 (뷰 변경 시 수정) |
| `../scoda-engine/static/js/app.js` | Correlation 렌더러 (renderCorrelationView) |

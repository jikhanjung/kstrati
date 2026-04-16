# 004 — Pyeongan Supergroup 추가 및 Correlation Chart Variant 패턴

Date: 2026-04-16

## Summary

평안누층군(Pyeongan Supergroup) 데이터를 kstrati에 추가하고, Correlation Chart 뷰에 provenance-based variant 패턴을 도입하여 하나의 뷰에서 조선누층군/평안누층군을 전환할 수 있게 했다.

## Changes

### 1. Data: Pyeongan Supergroup JSON

- `data/pyeongan_supergroup.json` 신규 생성
- 원본: Kim, M.G. & Lee, Y.I. (2017) Table 1 — 남한 평안누층군 대비표
- 13개 탄전/지역: 삼척, 강릉, 정선-평창, 영월, 제천, 단양, 문경, 보은, 보은서부, 완주-금산, 화순, 보성, 해남-강진
- 66개 지층 항목 (탄전별 개별 항목), 80건 age assignment
- `cross_coalfield_correlations`: 표준 지층명(삼척 기준)과 지역별 대비 지층명 매핑

### 2. Data: Joseon Supergroup 파일명 변경

- `data/taebaeksan_basin.json` → `data/joseon_supergroup.json` (rename)
- `scripts/create_database.py` 참조 경로 업데이트

### 3. Database: Pyeongan 데이터 로드

- `scripts/create_database.py`에 `load_pyeongan_data()` 추가
- provenance id=2: Kim & Lee (2017) 등록
- strat_units: rank `"coalfield"` 신규 (탄전/지역 단위)
- 구조: Pyeongan Supergroup → 13 coalfields → formations
- 같은 지층명이 여러 탄전에 등장 → 탄전별 별도 strat_unit 생성, strat_edge_cache로 소속 구분

### 4. Correlation Chart: Pyeongan

- `scripts/build_correlation.py` 전면 개편
  - `build_joseon_correlation()`: 기존 조선누층군 (correlation_chart 테이블)
  - `build_pyeongan_correlation()`: 평안누층군 (pyeongan_correlation 테이블)
- pyeongan_correlation: 18 rows × 13 coalfields
  - 16개 ICS stage (Bashkirian~Anisian) + Moscovian 3개 sub-row
  - Moscovian sub-row: 여러 지층이 같은 stage에 겹칠 때 자동 분배
  - Rowspan 자동 계산으로 연속 동일 지층 병합
- correlation_chart 테이블에 `provenance_id` 컬럼 추가 (Joseon 데이터 필터링용)

### 5. Manifest: Variant 패턴 도입

- 단일 `correlation_chart` 뷰에 `variant_key: "provenance_id"` + `variants` 추가
- Variant 1 (Choi 2011): Joseon — 2 group + biozone 컬럼 구조
- Variant 2 (Kim & Lee 2017): Pyeongan — 3 age 컬럼 + 13 coalfield 컬럼 구조
- provenance global_control 전환 시 같은 뷰에서 query + column 구성이 자동 교체

### 6. scoda-engine: resolveViewVariant()

- `scoda_engine/static/js/app.js`에 `resolveViewVariant()` 함수 추가
- `variant_key`로 지정된 global control 값에 따라 variant 설정을 base view에 shallow merge
- `renderCorrelationView()`에서 variant resolve 후 렌더링

## Design Decisions

### Chronostrat ↔ Lithostrat 관점

Correlation chart의 본질은 **시간 축(Chronostratigraphy)과 암석 단위(Lithostratigraphy)의 대비**다. Biozone은 이 대비의 정밀도를 높여주는 optional 정보이지 필수가 아니다. 따라서 Joseon(biozone 있음)과 Pyeongan(biozone 없음) 모두 같은 correlation chart 뷰 타입으로 렌더링할 수 있다.

### Variant 패턴 vs 별도 뷰

provenance에 따라 컬럼 구성(group 수, biozone 유무)이 달라지므로 하나의 고정 스키마로는 불가. 별도 뷰 2개를 만드는 대신 `variant_key` + `variants` 패턴으로 하나의 뷰가 provenance에 따라 자동 전환되도록 설계. 이 패턴은 다른 뷰 타입에도 재사용 가능.

## File Changes

| File | Action |
|------|--------|
| `data/pyeongan_supergroup.json` | 신규 |
| `data/taebaeksan_basin.json` → `data/joseon_supergroup.json` | rename |
| `scripts/create_database.py` | 수정 (Pyeongan 로더 + provenance 추가) |
| `scripts/build_correlation.py` | 전면 개편 (Joseon + Pyeongan 분리) |
| `scripts/add_scoda_tables.py` | 수정 (variant 패턴, Pyeongan 쿼리 추가) |
| `../scoda-engine/.../app.js` | 수정 (resolveViewVariant 추가) |

## Version

0.1.2 — Pyeongan Supergroup 추가, correlation chart variant 패턴

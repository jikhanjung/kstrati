# 005 — Map Selector Landing Page, Supergroup UI, rank_display

Date: 2026-04-16

## Summary

한반도 지질도 기반 Map Selector 랜딩 페이지를 도입하고, supergroup_id를 primary selector로 승격시켜 provenance_id와 분리했다. rank_display 매핑으로 지층명에 약어(Fm., Gp. 등)를 자동 표시하는 기능을 추가했다.

## Changes

### 1. Map Selector Landing Page

- `data/kstrati_map.json` 신규: 한반도 지도 데이터 + 누층군 마커 정의
  - viewBox 좌표계 (1198x1571, 배경 이미지 픽셀 좌표)
  - 배경 이미지: `KoreanPeninsulaGeolMap.png` (한반도 지질도)
  - 마커: 조선누층군 (830,1000), 평안누층군 (730,970)
  - 마커 색상: 조선 rgb(0,165,223), 평안 rgb(121,189,168)
- paleobase meta-package 패턴 차용: 탭 밖의 전체화면 랜딩
  - 첫 화면: 지도 (탭/컨트롤 숨김)
  - 마커 클릭 → `enterSupergroupView()` → 탭 모드 진입
  - Home(SCODA 로고) 클릭 → `showMapLanding()` → 지도 복귀

### 2. supergroup_id / provenance_id 분리

- `supergroup_id`: primary selector (누층군 선택 전담, string: "joseon", "pyeongan")
- `provenance_id`: secondary selector (누층군 내 논문 출처, integer)
- supergroup 변경 시 provenance 자동 동기화 + 드롭다운 필터링
- correlation chart `variant_key`: `"provenance_id"` → `"supergroup_id"` 변경
- variant 키: `"1"/"2"` → `"joseon"/"pyeongan"`

### 3. rank_display

- manifest에 `rank_display` 매핑 추가:
  - supergroup → "Sgp.", group → "Gp.", formation → "Fm.", member → "Mb."
- Correlation chart: 컬럼에 `suffix: " Fm."` 선언 → viewer가 셀 값에 자동 추가
- Stratigraphy tree: `manifest.rank_display[rank].abbr`를 라벨에 자동 추가

### 4. 버전 및 변수명

- `ASSERTION_VERSION` → `VERSION` (변수명 정리)
- 버전 0.1.2 → 0.2.0

## File Changes

| File | Action |
|------|--------|
| `data/kstrati_map.json` | 신규 |
| `assets/KoreanPeninsulaGeolMap.png` | 신규 (배경 이미지) |
| `scripts/add_scoda_tables.py` | 수정 (supergroup_map, rank_display, variant_key, VERSION) |
| `devlog/20260416_P01_map_selector_interface_design.md` | 신규 (설계 문서) |

## Version

0.2.0 — Map selector landing, supergroup_id 분리, rank_display

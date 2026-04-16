# P01 — KStrati Top-Level Interface Design: Map Selector

Date: 2026-04-16
Status: Plan (미구현)

## Context

KStrati는 현재 provenance_id 드롭다운으로 조선누층군/평안누층군을 전환한다. 향후 대동누층군(쥐라기), 경상누층군(백악기) 등이 추가되면 이 방식은 한계에 부딪힌다. paleobase가 meta_tree + package_bindings로 분류군을 선택하듯, kstrati도 **누층군 선택기**를 도입해야 한다.

채택 방향: **한반도 지도 위에 누층군별 마커를 놓고 클릭으로 선택** (옵션 B).

## Architecture: paleobase 패턴과의 대응

```
paleobase                          kstrati
─────────────────────────────      ──────────────────────────────
meta_tree.json (분류 계층)     →   kstrati_map.json (지도 마커 + 누층군 정의)
package_bindings.json          →   supergroup_modules (내부 모듈 바인딩)
renderMetaPackageUI()          →   renderMapSelectorView() (새 뷰 타입)
개별 .scoda 패키지              →   내부 모듈 (JSON + loader + queries + views)
```

핵심 차이: paleobase는 패키지를 분리하지만, kstrati는 **단일 .scoda 내부에서** 누층군 모듈을 전환한다.

## Design

### 1. 데이터: `data/kstrati_map.json`

누층군 마커 정의 — 지도 위의 위치, 시대, 연결된 내부 모듈 ID.

```json
{
  "schema_version": "1.0",
  "map": {
    "bounds": {"north": 38.6, "south": 33.1, "west": 125.0, "east": 130.0},
    "outline": "korea_peninsula.svg"
  },
  "supergroups": [
    {
      "id": "joseon",
      "name": "Joseon Supergroup",
      "name_ko": "조선누층군",
      "age_range": "Cambrian–Ordovician",
      "age_ma": [485, 541],
      "marker": {"lat": 37.17, "lng": 128.99, "label": "영월-태백"},
      "color": "#4A90D9",
      "provenance_ids": [1],
      "default_view": "correlation_chart"
    },
    {
      "id": "pyeongan",
      "name": "Pyeongan Supergroup",
      "name_ko": "평안누층군",
      "age_range": "Carboniferous–Triassic",
      "age_ma": [201, 359],
      "marker": {"lat": 37.10, "lng": 128.95, "label": "삼척-문경"},
      "color": "#D94A4A",
      "provenance_ids": [2],
      "default_view": "correlation_chart"
    }
  ]
}
```

향후 대동·경상 추가 시 `supergroups` 배열에 항목만 추가하면 된다.

### 2. Manifest 변경

```json
{
  "default_view": "map_selector",
  "supergroup_selector": "kstrati_map",
  "global_controls": [
    {
      "type": "select",
      "param": "supergroup_id",
      "label": "Supergroup",
      "source": "supergroup_selector",
      "default": "joseon"
    },
    {
      "type": "select",
      "param": "provenance_id",
      "label": "Provenance",
      "source_query": "provenance_selector",
      "depends_on": "supergroup_id"
    }
  ],
  "views": {
    "map_selector": {
      "type": "hierarchy",
      "display": "map_selector",
      "title": "Overview",
      "icon": "bi-geo-alt",
      "description": "Korean stratigraphic supergroups",
      "map_source": "kstrati_map"
    },
    "strat_tree": { "...variant_key: supergroup_id..." },
    "correlation_chart": { "...variant_key: supergroup_id..." },
    "formations_table": { "..." },
    "biozones_table": { "..." }
  }
}
```

**핵심 변경:**
- `default_view` → `"map_selector"` (첫 화면이 지도)
- `supergroup_id`가 primary selector, `provenance_id`는 secondary (supergroup에 종속)
- 기존 `variant_key: "provenance_id"` → `variant_key: "supergroup_id"`로 변경
- provenance 드롭다운은 선택된 supergroup에 속한 provenance만 필터링

### 3. 뷰 타입: `map_selector`

scoda-engine에 새 view display type 추가.

**렌더링:**
- 한반도 윤곽 SVG (assets/korea_outline.svg) — 간결한 path, 제주도 포함
- 각 누층군 마커: 원형 + 이름 라벨
  - 위: 누층군 이름 (한글)
  - 아래: 시대 범위 (e.g., "Cambrian–Ordovician")
  - 색상: supergroup별 구분색
- 마커 hover: 약간 확대 + 툴팁 (provenance 출처 등)
- 마커 click: `supergroup_id` 설정 → 해당 누층군의 `default_view`로 전환

**HTML 컨테이너:**
```html
<div class="view-container" id="view-map" style="display: none;">
    <div class="map-selector-content">
        <div class="map-selector-header" id="map-selector-header"></div>
        <div class="map-selector-body" id="map-selector-body"></div>
    </div>
</div>
```

**switchToView 추가:**
```javascript
} else if (view.display === 'map_selector') {
    document.getElementById('view-map').style.display = '';
    renderMapSelectorView(viewKey);
}
```

### 4. supergroup_id ↔ provenance_id 관계

| 현재 | 변경 후 |
|------|---------|
| provenance_id가 누층군 선택 겸용 | supergroup_id가 누층군 선택 전담 |
| provenance_id=1 → 조선 | supergroup_id="joseon" → provenance_id 필터링 |
| provenance_id=2 → 평안 | supergroup_id="pyeongan" → provenance_id 필터링 |
| variant_key: "provenance_id" | variant_key: "supergroup_id" |

supergroup 선택 시 해당 supergroup의 `provenance_ids`에 속한 provenance만 드롭다운에 표시. 하나의 누층군에 여러 provenance가 붙을 수 있음 (예: 조선누층군을 다룬 다른 논문 추가 시).

### 5. 한반도 SVG

`assets/korea_outline.svg` — 간결한 한반도 윤곽선.
- 남한 + 북한 경계 구분 (남한만 활성)
- 주요 도시/지역명은 생략 (마커가 위치를 대신)
- viewBox 좌표를 위경도에 매핑하는 변환 함수 사용
- 또는 간단하게: 고정 SVG에 마커 좌표를 pixel 단위로 직접 지정 (위경도 변환 없이)

### 6. 구현 순서 (단계적)

**Phase 1 — 데이터 구조 준비** (kstrati 쪽)
1. `data/kstrati_map.json` 생성
2. manifest에 `map_selector` 뷰 + `supergroup_id` global control 추가
3. 기존 `variant_key`를 `provenance_id` → `supergroup_id`로 전환
4. `provenance_selector` 쿼리에 supergroup 필터 추가
5. `add_scoda_tables.py` 업데이트

**Phase 2 — Viewer 구현** (scoda-engine 쪽)
1. `index.html`에 `#view-map` 컨테이너 추가
2. `app.js`에 `renderMapSelectorView()` 구현 (SVG + 마커 렌더링)
3. `switchToView()`에 `map_selector` dispatch 추가
4. `supergroup_id` global control의 변경 시 provenance 드롭다운 업데이트 로직
5. `style.css`에 map selector 스타일 추가

**Phase 3 — SVG 자산**
1. 한반도 윤곽 SVG 제작 또는 조달
2. `assets/` 또는 `scoda_engine/static/` 에 배치

### 7. 파일 변경 목록

**kstrati:**
- `data/kstrati_map.json` — 신규
- `scripts/add_scoda_tables.py` — manifest 수정 (map_selector 뷰, supergroup_id control, variant_key 변경)
- `scripts/create_scoda.py` — kstrati_map.json을 .scoda에 포함 (assets/ 또는 별도)

**scoda-engine:**
- `scoda_engine/templates/index.html` — `#view-map` 컨테이너 추가
- `scoda_engine/static/js/app.js` — `renderMapSelectorView()`, switchToView dispatch, supergroup-dependent provenance filtering
- `scoda_engine/static/css/style.css` — map selector 스타일
- `scoda_engine/static/assets/korea_outline.svg` — 한반도 SVG (또는 .scoda 내 assets/)

### 8. 검증

1. `python scripts/create_database.py && python scripts/build_correlation.py && python scripts/add_scoda_tables.py && python scripts/create_scoda.py`
2. scoda-engine serve 후 브라우저에서:
   - 첫 화면: 한반도 지도 + 2개 누층군 마커
   - 조선누층군 마커 클릭 → Correlation Chart (Joseon variant)
   - 평안누층군 마커 클릭 → Correlation Chart (Pyeongan variant)
   - supergroup_id 드롭다운으로도 전환 가능
   - provenance 드롭다운은 선택된 supergroup에 속한 것만 표시

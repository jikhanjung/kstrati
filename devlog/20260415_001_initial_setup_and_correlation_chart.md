# 2026-04-15 | Initial Setup & Correlation Chart

## 프로젝트 초기화

- kstrati 프로젝트 생성: 한국 퇴적층(태백산분지)의 층서 및 biozone 데이터를 SCODA 패키지로 구성
- CLAUDE.md 작성: SCODA 개요, 데이터 모델, 테이블 설계, 빌드 파이프라인 정리
- scoda-engine, trilobase 참조하여 구조 설계

## 데이터 모델 설계

### 핵심 설계 결정: Biozone은 독립 엔티티
- Group → Formation: 명확한 부모-자식 계층 (parent_id)
- Biozone: Formation의 자식이 아닌 독립 엔티티로 모델링
- Formation-Biozone 관계: `biozone_occurrences` junction table로 다대다 연관
- 동일 Biozone이 양쪽 Group에서 발견되면 cross-group correlation marker (예: Kayseraspis)

### 테이블 구조
- `strat_units`: Group/Formation 계층 (parent_id, prev_id, next_id, sort_order)
- `biozones`: 독립 시간 지표 (prev_id, next_id chain)
- `biozone_occurrences`: Formation-Biozone 다대다
- `age_assignments`: ICS 연대 매핑 (original term 병기)
- `correlation_chart`: pre-computed correlation chart 행 데이터

## 소스 데이터

### data/taebaeksan_basin.json
- 태백층군 10개 Formation (두위봉~장산), 23개 Biozone
- 영월층군 5개 Formation (영흥~삼방산), 17개 Biozone (Kayseraspis 공유)
- ICS 연대 매핑 포함 (Arenigian → Floian+Dapingian 등)

### data/correlation_chart.json
- 28행의 correlation chart 배치 데이터
- 각 행: [period, stage, taebaek_fm, taebaek_bz, yeongwol_fm, yeongwol_bz]
- build_correlation.py가 읽어서 rowspan 계산 후 DB에 저장

### Biozone-Formation 배정 수정 (원본 차트 대비)
- Shumardia pellizzarii, Kainella euryrachis, Yosimurasapis vulgaris → 문곡 (영흥에서 이동)
- Fatocephalus hunjiangensis → 와곡 (문곡에서 이동)

## 빌드 파이프라인

```
data/taebaeksan_basin.json ──→ scripts/create_database.py ──→ kstrati.db (4 data tables)
data/correlation_chart.json ─→ scripts/build_correlation.py ─→ kstrati.db (+ correlation_chart)
                                scripts/add_scoda_tables.py ──→ kstrati.db (+ 6 SCODA metadata)
                                scripts/create_scoda.py ──────→ kstrati.scoda (ZIP package)
```

## SCODA 패키지 구성

### 메타데이터 테이블
- artifact_metadata: kstrati v0.1.0, CC-BY-4.0
- provenance: Choi (2019), ICS Chart v2024/12
- schema_descriptions: 31개 테이블/컬럼 설명
- ui_display_intent: 3개
- ui_queries: 10개 named query
- ui_manifest: 6개 view

### UI Views
1. **Stratigraphy** (hierarchy/tree): Group→Formation 트리, leaf에서 biozone 목록
2. **Correlation Chart** (hierarchy/correlation): 양쪽 Group 나란히 표시하는 correlation table
3. **Formations** (table): 전체 Formation 목록
4. **Biozones** (table): 전체 Biozone 목록
5. **Formation Detail** (detail): Formation 상세 + ages/biozones sub-query
6. **Biozone Detail** (detail): Biozone 상세 + formation occurrences

## scoda-engine 확장

### 새 display type: `correlation`
- `renderCorrelationView()` 함수 추가 (app.js)
- pre-computed rowspan 기반 HTML 테이블 렌더링
- `column_groups`: 상단 그룹 헤더 (AGE | Taebaek Group | Yeongwol Group)
- `border_follow`: biozone 셀의 top border를 formation rowspan에 연동 (같은 층 내 biozone 간 border 제거)
- `border_bottom_values`: 특정 biozone 아래에만 border 표시 (Fenghuangella, Glyptagnostus reticulatus)

### CSS (style.css)
- `.corr-period`: 세로 쓰기 (ORDOVICIAN, CAMBRIAN)
- `.corr-stage`, `.corr-fm`, `.corr-bz`: 각 컬럼별 스타일링
- `border-top: hidden` inline style로 collapsed table border 제어

## Correlation Chart 배치 조정 이력

| 항목 | 최종 배치 |
|------|-----------|
| 영흥 Yeongheung | 두위봉~Kayseraspis (4행) |
| 문곡 Mungok | Shumardia~Yosimurasapis (3행) |
| 와곡 Wagok | Fatocephalus~Quadraticephalus (3행, 동점+화절 걸침) |
| 마차리 Machari | Pseudoyuepingia~Tonkinella (12행, 화절 중간~대기) |
| 삼방산 Sambangsan | Megagraulos~Metagraulos (3행, 대기+묘봉 걸침) |
| Furongian/Series 3 경계 | Fenghuangella↔Liostracina / Glyp.reticulatus↔Glyp.stolidotus 사이 |

# 2026-04-15 | Provenance 연결 구조 추가

## 배경

기존 `provenance` 테이블은 패키지 전체에 대한 출처 목록만 제공했고, 개별 데이터 레코드와 연결되지 않았다. 향후 여러 논문의 데이터를 통합할 때 "이 biozone 배정은 어느 논문 기준인가"를 구분할 수 없는 문제가 있었다.

### 층서 데이터의 특수성

trilobase의 taxonomy에서는 "taxon A가 parent B에 속한다"가 하나의 discrete assertion이고 출처가 명확하다. 반면 stratigraphy에서는 assertion의 성격이 다양하다:

| 관계 유형 | 확실성 | 예시 |
|-----------|--------|------|
| Formation 내 Biozone 산출 | 비교적 명확 | "두무골에서 Kayseraspis 산출" |
| Biozone 간 cross-correlation | 논문 명시 | Kayseraspis가 두무골·영흥 양쪽에서 산출 |
| Formation↔ICS Stage 대비 | 해석적/유추 | 논문 도표에서 읽어낸 것 |
| Correlation chart 배치 | 시각적 해석 | 상대적 두께·기간 추정 |

전면적인 assertion 프레임워크 대신, 이미 assertion 역할을 하고 있는 기존 테이블에 `provenance_id`와 `basis` 컬럼을 추가하는 실용적 접근을 택했다.

## 변경 내용

### 1. Primary provenance 수정

기존: Choi, D.K. (2019) Springer 책
변경: Choi, D.K. (2011) 태백산분지의 전기 고생대 고지리, 고환경에 관한 새로운 견해. J. Paleont. Soc. Korea, 27(1), 1–11.

### 2. 스키마 변경 — `biozone_occurrences`

```sql
+ provenance_id INTEGER REFERENCES provenance(id)
+ basis         TEXT NOT NULL DEFAULT 'stated'
```

"이 지층에서 이 biozone이 산출된다"는 논문에서 명시적으로 기술된 사실이므로 기본 basis는 `stated`.

### 3. 스키마 변경 — `age_assignments`

```sql
+ provenance_id INTEGER REFERENCES provenance(id)
+ basis         TEXT NOT NULL DEFAULT 'chart_inferred'
```

Formation↔ICS Stage 매핑은 대부분 논문의 대비표(도표)에서 읽어낸 것이므로 기본 basis는 `chart_inferred`.

### 4. `basis` 값 체계

| basis | 의미 |
|-------|------|
| `stated` | 논문에서 명시적으로 기술 |
| `chart_inferred` | 논문의 대비표(도표)에서 읽어낸 것 |
| `gssp_definition` | GSSP 경계 정의에서 따라오는 것 |
| `composite` | 여러 출처를 종합한 해석 |

### 5. 빌드 파이프라인 변경

- `create_database.py`: provenance 테이블 생성 + seed (id=1) 추가. FK 참조를 위해 데이터 삽입 전에 provenance 행이 필요.
- `add_scoda_tables.py`: provenance citation 업데이트, schema_descriptions에 새 컬럼 설명 추가.

## 현재 데이터 상태

| 테이블 | 건수 | provenance_id | basis |
|--------|------|---------------|-------|
| `biozone_occurrences` | 40 | 1 (Choi 2011) | `stated` |
| `age_assignments` | 25 | 1 (Choi 2011) | `chart_inferred` |

## 향후 확장 시

- 새 논문 데이터 추가: provenance 행 추가 → 개별 occurrence/assignment에 해당 provenance_id 지정
- 같은 관계에 대한 상충 해석: 다른 provenance_id로 병렬 기록 가능
- `strat_units` 계층 자체는 안정적이라 개별 provenance 불필요
- `correlation_chart`는 display용 파생 테이블이므로 provenance 불필요

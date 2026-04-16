# 2026-04-16 | Provenance 드롭다운, strat_edge_cache, 버전 관리, CI/CD

## 배경

trilobase에서 taxonomy profile을 드롭다운으로 전환하는 패턴(global_controls)을 kstrati의 provenance에 적용하고, 층서 계층 자체도 provenance에 따라 달라질 수 있도록 구조를 개편했다.

## 변경 사항

### 1. Provenance 드롭다운 (global_controls)

trilobase의 `classification_profiles_selector` + `global_controls` 패턴을 그대로 적용.

- manifest에 `global_controls` 추가: `provenance_selector` 쿼리로 드롭다운 옵션 채움
- `provenance` 테이블에 `short_name` 컬럼 추가 (드롭다운 표시용 짧은 이름)
- provenance 의존 쿼리 6개에 `COALESCE(:provenance_id, ...)` 조건 추가
- provenance 미사용 쿼리 3개(`provenance_selector`, `biozone_detail`, `correlation_chart`)는 `WHERE COALESCE(:provenance_id, 1) > 0`으로 파라미터 소비 — global_controls가 모든 fetchQuery에 파라미터를 병합하므로, SQL에서 `:provenance_id`를 참조하지 않으면 SQLite binding error 발생

현재 provenance는 Choi (2011) 1건만 존재. ICS Chart, build pipeline provenance는 제거 (추후 필요 시 재추가).

### 2. strat_edge_cache (provenance 의존 층서 계층)

층서 계층(Formation → Group → Supergroup)도 provenance에 따라 달라질 수 있다는 판단.

**이전 구조:**
```
strat_units: id, name, rank, parent_id, prev_id, next_id, sort_order, ...
```

**변경 후:**
```
strat_units:      id, name, name_ko, rank, alt_name, ... (단위 자체 속성만)
strat_edge_cache: provenance_id, child_id, parent_id, prev_id, next_id, sort_order
                  PRIMARY KEY (provenance_id, child_id)
```

trilobase의 `classification_edge_cache`와 동일한 패턴. 모든 hierarchy/detail 쿼리가 `strat_edge_cache e ON e.child_id = u.id AND e.provenance_id = COALESCE(:provenance_id, 1)`로 JOIN.

### 3. Joseon Supergroup 추가

태백층군(Group)과 영월층군(Group)의 상위에 조선누층군(Supergroup) 추가.

```
Joseon Supergroup (조선누층군)
├── Taebaek Group (태백층군)
│   ├── Duwibong, Jigunsan, ...
└── Yeongwol Group (영월층군)
    ├── Yeongheung, Mungok, ...
```

- `data/taebaeksan_basin.json`에 `"supergroup"` 필드 추가
- `create_database.py`가 supergroup → group → formation 3단 계층을 `strat_edge_cache`에 기록
- strat_units: 17 → 18행, strat_edge_cache: 17 → 18행

### 4. 버전 관리 (trilobase 패턴)

- `add_scoda_tables.py`에 `ASSERTION_VERSION = "0.1.1"` 상수 + `--version` CLI 인자
- `create_scoda.py`가 DB의 `artifact_metadata.version`을 읽어 `dist/kstrati-{version}.scoda` + `dist/kstrati-{version}.manifest.json` 생성
- 출력 디렉토리가 프로젝트 루트에서 `dist/`로 변경

### 5. CI/CD (GitHub Actions)

trilobase 워크플로우 패턴 적용:

| Workflow | Trigger | 역할 |
|----------|---------|------|
| `ci.yml` | push/PR to main | 빌드 + 패키지 검증 |
| `release.yml` | tag push `v*.*.*` | 자동 릴리스 |
| `manual-release.yml` | workflow_dispatch | 수동 릴리스 |

모두 scoda-engine을 checkout → editable install → 4단계 빌드 → .scoda + .manifest.json 생성.

## 기술 메모

### global_controls 파라미터 소비 문제

scoda-engine의 `fetchQuery()`는 `globalControls`를 모든 쿼리 파라미터에 병합한다. 백엔드 `_execute_query()`는 `cursor.execute(sql, params)`로 실행하는데, Python sqlite3는 dict에 있지만 SQL에서 참조하지 않는 named parameter에 대해 에러를 발생시킨다.

처음에는 `:provenance_id AS _prov`로 SELECT에 더미 컬럼을 추가했으나, correlation chart 렌더러가 이전에 빈 화면으로 나오는 문제가 있었다 (원인은 ScodaDesktop의 캐시/로딩 타이밍으로 추정). `WHERE COALESCE(:provenance_id, 1) > 0`으로 변경하여 해결.

### Correlation chart 빈 화면 디버깅

ScodaDesktop에서 correlation chart가 빈 화면으로 표시되었으나 에러 없음. console.log를 switchToView와 renderCorrelationView에 추가하여 호출 흐름 확인 후 정상 동작 확인. 최종 원인은 ScodaDesktop 재시작 후 캐시가 갱신되면서 해결된 것으로 보임.

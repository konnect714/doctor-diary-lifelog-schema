# Changelog

All notable changes to this project will be documented in this file.

포맷은 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)를 따르고, 버전 관리는 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)을 사용합니다.

## [1.1.0] - 2026-04-16

### Added — 실데이터 추출 최적화 & 최신 논문 반영

- **스키마 개선 (7개 파일)**
  - `schema_cgm.json`: GluFormer 460-bin 호환 `glucose_token_extended` 필드 추가, `missing_reason` enum 5종 확장 (sensor_battery_low, device_error, connectivity_loss, sensor_removed_temporary, sensor_replacement), 데이터 품질 필드 추가 (cgm_data_completeness, imputation_applied, imputation_method)
  - `schema_diet.json`: event_end null 처리 규칙 공식화, 식후 혈당 반응 필드 추가 (postprandial_peak_mgdl, time_to_peak_minutes, time_to_baseline_minutes)
  - `schema_exercise.json`: HRV 및 운동 후 인슐린 민감도 필드 추가 (heart_rate_variability_rmssd, post_exercise_sensitivity_hours)
  - `schema_checkup.json`: cohort_type (adult/pediatric/pregnant/elderly), staleness_days, max_validity_days 추가
  - `schema_annot_*.json` (3종): event_id/cgm_window_id 패턴 검증 추가

- **신규 스크립트**
  - `scripts/extract_from_app.py` — IT실용 앱 DB → JSON/JSONL 추출 도우미 (HMAC-SHA256 pseudonymize, KST 정규화, sin/cos 계산, 토큰화, manifest 생성)
  - `scripts/met_mapping.py` — Compendium 2011 기반 activity_type → MET 매핑 테이블 (17종)

- **검증 강화**
  - `validate.py`: 전체 영양소 필드 _missing_fields 일관성 검사, 운동 intensity↔MET 일관성, sin/cos 허용 오차 float32 대응 (1e-4 → 1e-3), event_end null 경고 분리
  - `align_to_grid.py`: glucose_token -1 → NaN 수정, 자정 넘김 이벤트 처리, carb_cum_2h 정확 교집합 계산

- **CI 강화** (`.github/workflows/validate.yml`)
  - JSON 문법 검증, 스키마 크로스 레퍼런스, ruff 린트, enum 중복 체크 추가

- **테스트 확장** (`tests/test_validate_extended.sh`)
  - 자정 넘김, float32 정밀도, 빈 JSONL, 대량 배치(1000건), enum 중복 테스트

- **논문 업데이트** (`references/papers.md`, `references/cgm_grid.md`)
  - AttenGluco (arXiv 2025) — 멀티모달 cross-attention
  - WEAR-ME / Insulin Resistance from Wearables (Nature 2026)
  - CGM Missing Data Imputation Benchmarks (medRxiv 2025)
  - GluFormer 460-bin 토큰화 방식 문서화

### Fixed

- 샘플 데이터 event_id 패턴을 표준화 (`meal_8a7b6c5d` → `meal_u_abc123_20260416_073000`)
- diet_sample cholesterol_mg null → _missing_fields에 등록
- validate.py event_end null WARNING이 FAIL로 처리되던 버그 수정

### 알려진 제약 (일부 해소)

- ~~소아·임산부 cohort_type 필드 없음~~ → checkup에 cohort_type 추가됨
- Pydantic 모델은 미포함 (JSON Schema만 제공)
- Annotation UI는 별도 저장소에서 개발 예정
- user_id_hash HMAC-SHA256 형식 표준화는 IT실 확정 후 패턴 업데이트 예정

## [1.0.0] - 2026-04-16

### Added — 초기 버전

- **3층 구조 설계 원칙** 문서화
  - Layer 1: CGM 5분 고정 그리드 (GluFormer, CGMformer 표준)
  - Layer 2: 식단·운동 이벤트 (원본 보존 + 학습 시 그리드 투영)
  - Layer 3: 건강검진 정적 컨텍스트

- **JSON Schema (Draft 2020-12) 7종**
  - `schema_cgm.json` — CGM 5분 측정 레코드
  - `schema_diet.json` — 식단 이벤트
  - `schema_exercise.json` — 운동 이벤트
  - `schema_checkup.json` — 건강검진 정적 컨텍스트
  - `schema_annot_meal.json` — 식사 의학 annotation
  - `schema_annot_cgm_event.json` — CGM 임상 이벤트 annotation
  - `schema_annot_quality.json` — 데이터 품질 annotation

- **샘플 데이터** (`sample_data.json`, `sample_annotations.json`)
  - 모든 스키마별 합성 예시 레코드 총 8개

- **검증 및 정렬 스크립트**
  - `scripts/validate.py` — JSON Schema 검증 + 의미론적 일관성 검사
    - missing_mask와 값 필드 일관성
    - sin/cos ↔ minute_of_day 일관성
    - glucose_token ↔ glucose_mgdl 일관성
    - exercise duration ↔ start/end 일관성
  - `scripts/align_to_grid.py` — 이벤트를 5분 그리드 15채널로 투영

- **상세 참조 문서** 6종 (`references/`)
  - `papers.md` — GluFormer, CGMformer, CGM-LSM, WBM, LSM, EHR+Wearable FM 논문 매핑표
  - `cgm_grid.md` — CGM 5분 그리드, 토큰화, sin/cos 인코딩
  - `event_schema.md` — 식단·운동 이벤트 필드, MET 코드, 그리드 투영 방식
  - `static_context.md` — 건강검진 ICD-10/ATC 코딩, staleness 처리
  - `annotation_guide.md` — 서울대 annotation 작업 가이드
  - `org_interface.md` — IT실↔KAIST↔서울대 인터페이스 계약

- **협업 인프라**
  - `README.md` — 프로젝트 소개 및 조직별 가이드
  - `CONTRIBUTING.md` — 협업 규칙 및 스키마 버전 관리 정책
  - `LICENSE` — Apache-2.0
  - `.gitignore` — 데이터·시크릿 실수 커밋 방지

### 알려진 제약

- 실제 닥터다이어리 내부 DB 필드와의 매핑 표는 아직 미작성 (IT실 작업 예정)
- Pydantic 모델은 미포함 (JSON Schema만 제공)
- Annotation UI는 별도 저장소에서 개발 예정
- 모든 스키마는 **성인 대상** 가정. 소아·임산부 사용 시 cohort_type 필드 추가 필요.

[1.1.0]: https://github.com/konnect714/doctor-diary-lifelog-schema/releases/tag/v1.1.0
[1.0.0]: https://github.com/konnect714/doctor-diary-lifelog-schema/releases/tag/v1.0.0

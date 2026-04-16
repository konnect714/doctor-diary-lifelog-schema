# Changelog

All notable changes to this project will be documented in this file.

포맷은 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)를 따르고, 버전 관리는 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)을 사용합니다.

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

[1.0.0]: https://github.com/YOUR-ORG/doctor-diary-lifelog-schema/releases/tag/v1.0.0

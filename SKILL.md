---
name: doctor-diary-lifelog-schema
description: Design and document data schemas for collecting Doctor Diary (닥터다이어리) lifelog data — CGM, diet, exercise, and health checkup records — for training time-series foundation models (CNN + Transformer). Use this skill whenever the user mentions 닥터다이어리, Doctor Diary, lifelog 데이터 스키마, CGM foundation model 학습 데이터, 식단/운동 기록 JSON 정렬, 건강검진 정적 컨텍스트, or any schema design involving multimodal glucose + lifestyle + clinical data for ML. Also trigger when users from 닥터다이어리 IT실, KAIST AI 대학원, or 서울대 의과학실 ask about data handoff formats, annotation schemas, or the IT실 → 대학원 → 의과학실 pipeline, even if they don't explicitly say "스키마". Produces JSON Schema files, Pydantic models, human-readable documentation, sample data, validation scripts, and inter-organization interface contracts grounded in published foundation-model literature (GluFormer, CGMformer, CGM-LSM, WBM, LSM).
---

# Doctor Diary Lifelog Schema

이 스킬은 닥터다이어리 앱의 lifelog 데이터를 시계열 foundation model (CNN + Transformer) 학습용으로 수집·정렬하기 위한 **데이터 스키마 설계 및 문서화**를 돕습니다.

협업 주체는 세 조직입니다:
- **닥터다이어리 IT실**: 원본 데이터 추출 및 내보내기
- **KAIST AI 대학원**: foundation model 사전학습/파인튜닝
- **서울대 의과학실**: annotation 및 의학적 검증

## 핵심 설계 원칙 — 3층 구조

논문 근거(`references/papers.md` 참고)를 바탕으로, 이질적 주기성을 가진 4종 데이터를 하나의 시계열에 억지로 섞지 **않습니다**. 대신 다음 3개 층으로 분리합니다:

### Layer 1. CGM 고정 그리드 (기본 축)
- **5분 간격 고정 그리드**, 하루 288 스텝. (GluFormer·CGMformer 표준)
- 혈당값은 원본 연속값 + 이산 토큰(40~300 mg/dL, 1 mg/dL 단위 bin) **둘 다** 저장.
- 시간 정보는 `sin_time`, `cos_time` (24시간 주기 encoding) 추가.
- 결측은 값을 `null`로 두고 `missing_mask` 필드로 명시.

### Layer 2. 이벤트 채널 (식단, 운동)
- 식단과 운동은 **원본 이벤트 형태**로 보존 (타임스탬프, 지속시간, 메타데이터).
- 학습 단계에서 CGM 5분 그리드에 **채널로 투영** (scripts/align_to_grid.py).
- 이벤트 → 그리드 변환은 학습 스크립트의 몫이고, 원본은 이벤트 JSON으로 유지.

### Layer 3. 정적 컨텍스트 (건강검진)
- 시계열에 섞지 않고 **별도 테이블**로 분리.
- 학습 시 CGM 윈도우 시점에 유효한 가장 최근 검진값을 조회해 조건 임베딩으로 주입.

## 산출물

이 스킬이 트리거되면 다음 중 요청에 맞는 것을 생성합니다:

1. **JSON Schema 파일** (`assets/schema_*.json`) — 기계 검증 가능한 형식 정의
2. **Pydantic 모델** — Python 타입 힌트 + 런타임 검증
3. **사람이 읽는 문서** — 각 필드 설명, 단위, 결측 규칙, 의학적 근거
4. **샘플 데이터** (`assets/sample_*.json`) — 스키마 예시
5. **검증 스크립트** (`scripts/validate.py`) — 제출 데이터 검증
6. **정렬 스크립트** (`scripts/align_to_grid.py`) — 이벤트 → 5분 그리드 투영
7. **조직 간 인터페이스 계약서** — IT실 출력 / KAIST 입력 / 의과학실 annotation 포맷 명세

## 워크플로

사용자 요청을 받으면:

1. **의도 파악**: 어떤 산출물을 원하는가? (전체 스키마 세트 / 특정 모달리티 / 조직 간 계약서 / annotation 가이드)
2. **관련 reference 읽기**: `references/` 폴더의 해당 파일을 먼저 읽어 설계 원칙 확인
3. **기존 스키마 참조**: `assets/` 폴더의 기존 schema_*.json이 있으면 참고
4. **산출물 생성**: 필요한 파일을 `/mnt/user-data/outputs/`에 저장
5. **근거 제시**: 주요 설계 결정마다 관련 논문 근거를 짧게 인용

## Reference 파일

각 모달리티와 원칙에 대한 상세 내용은 다음 참고 문서에 있습니다. **해당 작업에 관련된 파일만 읽으세요** (progressive disclosure):

- `references/papers.md` — 근거가 되는 foundation model 논문들 (GluFormer, CGMformer, CGM-LSM, WBM, LSM, EHR+wearable) 요약
- `references/cgm_grid.md` — CGM 5분 그리드, 토큰화 방식, sin/cos 시간 인코딩 상세
- `references/event_schema.md` — 식단/운동 이벤트 표준 필드, enum 값 (meal_type, MET 코드), 결측 처리
- `references/static_context.md` — 건강검진 필드, ICD-10/ATC 코딩, 최근 검진값 조회 규칙
- `references/annotation_guide.md` — 서울대 의과학실 annotation 라벨 정의와 작업 가이드
- `references/org_interface.md` — IT실 → KAIST → 의과학실 데이터 흐름과 각 단계 포맷 계약

## Assets

- `assets/schema_cgm.json` — CGM JSON Schema
- `assets/schema_diet.json` — 식단 이벤트 JSON Schema
- `assets/schema_exercise.json` — 운동 이벤트 JSON Schema
- `assets/schema_checkup.json` — 건강검진 JSON Schema
- `assets/schema_annot_meal.json` — 식사 의학 annotation 스키마
- `assets/schema_annot_cgm_event.json` — CGM 임상 이벤트 annotation 스키마
- `assets/schema_annot_quality.json` — 데이터 품질 annotation 스키마
- `assets/sample_data.json` — 원본 데이터 예시 (cgm, diet, exercise, checkup)
- `assets/sample_annotations.json` — annotation 예시

## Scripts

- `scripts/validate.py` — 제출 데이터가 스키마를 따르는지 검증 (jsonschema 기반). 의미론적 검증(missing_mask 일관성, sin/cos ↔ minute_of_day, 토큰↔혈당 일관성)도 포함.
- `scripts/align_to_grid.py` — 이벤트를 CGM 5분 그리드에 채널로 투영. 출력은 NumPy `.npz`로 15개 채널(CGM 6 + diet 4 + exercise 4 + timestamps 1).

## 빠른 사용 예

```bash
# 샘플 데이터 검증
python scripts/validate.py --sample

# 실제 데이터 검증
python scripts/validate.py mydata.jsonl --type cgm

# 이벤트 → 그리드 정렬
python scripts/align_to_grid.py \
    --cgm data/cgm.jsonl \
    --diet data/diet.jsonl \
    --exercise data/exercise.jsonl \
    --start "2026-04-16T00:00:00+09:00" \
    --end "2026-04-17T00:00:00+09:00" \
    --out window_20260416.npz
```

## 의료 데이터 취급 원칙

닥터다이어리 데이터는 건강 정보입니다. 스키마 설계 시 항상:
- **PII/PHI 필드는 pseudonymize된 ID만 포함** (이름·주민번호·전화번호는 스키마에서 제외)
- **민감 필드는 명시적으로 표기** (예: comorbidities, medications는 접근 제어 메타데이터 포함)
- **timezone은 항상 명시** (KST 기준, ISO 8601 with offset)
- **단위는 필드명 또는 스키마 메타에 명시** (예: `glucose_mgdl`, `weight_kg`)

# 조직 간 인터페이스 계약서

닥터다이어리 IT실 → KAIST AI 대학원 → 서울대 의과학실의 데이터 흐름과 각 단계별 포맷 명세.

## 전체 흐름

```
[닥터다이어리 앱 DB]
        ↓ (추출)
[IT실: Layer 1 원본 JSON]
        ↓ (검증 + pseudonymize)
        ├──────────────────────┐
        ↓                       ↓
[KAIST: Layer 2 학습용 텐서]  [서울대: annotation 대기열]
        ↓                       ↓
[사전학습 모델]          [annotation 완료 샘플]
        ↑                       ↓
        └───── 파인튜닝 ────────┘
```

## Layer 1: IT실 출력 포맷

**목적**: 원본에 가까운 이벤트 레벨 보존. 이후 가공의 기준점.

### 파일 구성

사용자별, 월별로 분리한 JSONL 파일:

```
exports/
  u_xxx/
    2026-01/
      cgm.jsonl
      diet.jsonl
      exercise.jsonl
    2026-02/
      ...
    checkups.jsonl    # 검진은 월별 분리 불필요
    user_profile.json
```

각 jsonl 라인은 `schema_*.json` 스키마를 따름.

### 전달 방식

- **암호화 전송**: AES-256 전송 중 암호화 + 수신측 대기 버킷에서 복호화
- **무결성**: 각 파일에 SHA-256 해시 동봉 (`manifest.json`)
- **전달 주기**: 월 1회 증분 (delta) + 분기별 전체 (full) 검증

### 전달 전 IT실 책임

1. **PII 완전 제거**: 실명, 전화번호, 이메일, 주소 — 스키마에 아예 필드 없음
2. **pseudonymize**: `user_id` → `user_id_hash` (HMAC-SHA256 with secret salt)
3. **스키마 검증**: `scripts/validate.py` 전체 통과 필수
4. **manifest 생성**: 레코드 개수, 시간 범위, 해시

### manifest.json 예시

```json
{
  "export_id": "export_20260301_u_xxx",
  "user_id_hash": "u_xxx",
  "export_date": "2026-03-01T00:00:00+09:00",
  "coverage": {
    "start": "2026-02-01T00:00:00+09:00",
    "end": "2026-02-28T23:59:59+09:00"
  },
  "files": [
    {
      "path": "2026-02/cgm.jsonl",
      "records": 8064,
      "sha256": "abc123...",
      "schema_version": "1.0.0"
    }
  ],
  "schema_version": "1.0.0",
  "it_team_sign": "signed_by_it_team_key"
}
```

## Layer 2: KAIST 학습용 포맷

**목적**: Layer 1을 읽어 foundation model 사전학습에 바로 투입 가능한 텐서.

### 변환 책임

- KAIST 팀이 Layer 1을 읽어 Layer 2를 생성. **IT실은 Layer 2를 만들지 않음**.
- 변환 스크립트는 `scripts/align_to_grid.py` 기반으로 KAIST가 커스터마이즈.

### Layer 2 파일 포맷

HDF5 또는 Zarr (대용량 과학 계산용):

```
dataset.h5
  /u_xxx/
    /window_20260201_000000/
      cgm_glucose        # (288,) float32, mg/dL
      cgm_glucose_token  # (288,) int16, 0~259
      cgm_mask           # (288,) bool, true = missing
      time_sin           # (288,) float32
      time_cos           # (288,) float32
      day_of_week        # () int8
      
      diet_active        # (288,) bool
      diet_minutes_since # (288,) float32, minutes since last meal
      diet_carb_cum_2h   # (288,) float32, cumulative carb past 2h
      diet_kcal_active   # (288,) float32
      
      exercise_active    # (288,) bool
      exercise_met       # (288,) float32
      exercise_met_min_cum_1h    # (288,) float32
      exercise_minutes_since_end # (288,) float32
      
      # 정적 컨텍스트 (window 전체에 동일 값)
      static_age         # () float32
      static_sex         # () int8
      static_bmi         # () float32
      static_hba1c       # () float32
      static_diabetes_type # () int8
      static_medications_multihot # (50,) bool
      static_staleness_days # () float32
      static_missing_mask # (10,) bool  # 정적 필드별 결측 여부
```

### Window 생성 규칙

- **기본 window**: 24시간 (288 스텝) sliding, stride = 1시간 (12 스텝)
- **식사 중심 window**: 식사 이벤트 기준 이전 90분 ~ 이후 90분 (Virtual CGM 방식)
- **야간 window**: 22시~06시 (야간 저혈당 학습용)

Window 설계는 파인튜닝 작업별로 다를 수 있으므로 **Layer 2 변환 스크립트를 작업별로 분기**.

## Layer 3: 서울대 annotation 파이프라인

### Annotation 대기열

서울대는 Layer 1 원본을 받되, **시각화 가능한 형태로 정리된 UI**를 통해 annotation 수행. 원본 파일 직접 다루지 않음.

### 제출 포맷

서울대가 annotation 완료 후 KAIST에 전달하는 파일:

```
annotations/
  snu_annotator_007/
    2026-04-20/
      meal_labels.jsonl       # schema_annot_meal
      cgm_event_labels.jsonl  # schema_annot_cgm_event
      quality_labels.jsonl    # schema_annot_quality
      manifest.json
```

각 annotation 레코드는 원본 event_id를 참조하므로 KAIST에서 join 가능.

### Annotator 메타데이터

```json
{
  "annotator_id": "snu_med_007",
  "annotator_role": "resident_endocrinology",
  "calibration_score": 0.82,
  "completed_count": 1247
}
```

- `calibration_score`: 초기 calibration 샘플에서의 inter-annotator agreement
- 모델 학습 시 annotator별 라벨에 weight로 활용 가능

## 스키마 버전 관리

### Semantic Versioning

- `1.0.0` → `1.0.1`: 버그 수정, enum 값 추가 (하위 호환)
- `1.0.0` → `1.1.0`: 선택 필드 추가
- `1.0.0` → `2.0.0`: 필드 제거, 필수 필드 변경 (breaking)

### 변경 관리

- 모든 schema 파일 헤더에 `"schema_version"` 포함
- 버전 변경 시 **3개 조직 모두 합의** 후 적용
- Breaking 변경은 전환 기간 최소 1개월, 두 버전 병행 지원

## 협의가 필요한 사항

이 문서를 읽은 후 다음을 3개 조직이 합의해야 함:

1. **user_id_hash 생성 방식**: HMAC 키는 누가 관리? (IT실만 보유 권장)
2. **전달 주기와 총 전달량**: 초기 pilot은 몇 명? 몇 개월치?
3. **만료 및 삭제 정책**: 학습 종료 후 데이터 보유 기간
4. **IRB 관할**: 공동 IRB? 각 기관 IRB?
5. **결과물 저작권 및 공동 연구 계약**

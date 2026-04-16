# 서울대 의과학실 Annotation 가이드

서울대 의과학실의 annotation 작업은 foundation model이 학습할 **정답 라벨 또는 보조 신호**를 만드는 작업입니다. 비지도 사전학습(self-supervised)에는 필요 없지만, **다운스트림 작업 파인튜닝**과 **품질 검증**에 필수입니다.

## Annotation 대상 3가지

### 1. 식사 이벤트 의학적 분류 (meal_medical_label)

각 식사 이벤트에 대해:

```json
{
  "event_id": "meal_abc123",
  "annotator_id": "snu_med_007",
  "annotated_at": "2026-04-18T14:30:00+09:00",
  "meal_medical_label": {
    "glycemic_impact": "high",
    "carb_quality": "refined",
    "meal_balance": "unbalanced",
    "adherence_to_diet": "non_adherent",
    "clinical_notes": "정제 탄수화물 위주, 섬유소 부족. 식후 혈당 급상승 예상."
  }
}
```

- **glycemic_impact** enum: `minimal` / `moderate` / `high` / `very_high`
- **carb_quality** enum: `complex_high_fiber` / `mixed` / `refined` / `sugary`
- **meal_balance** enum: `balanced` / `carb_heavy` / `protein_heavy` / `fat_heavy` / `unbalanced`
- **adherence_to_diet**: 당뇨 환자 권장 식이 기준 준수 여부

### 2. CGM 이벤트 라벨링 (cgm_event_label)

특정 CGM 구간에 대해 의학적 이벤트 라벨:

```json
{
  "cgm_window_id": "cgm_u_xxx_20260416_070000",
  "start_timestamp": "2026-04-16T07:00:00+09:00",
  "end_timestamp": "2026-04-16T11:00:00+09:00",
  "events": [
    {
      "event_type": "postprandial_spike",
      "start": "2026-04-16T08:15:00+09:00",
      "peak": "2026-04-16T09:00:00+09:00",
      "peak_glucose_mgdl": 245,
      "severity": "severe",
      "likely_cause": "meal_abc123",
      "clinical_notes": "정상 범위 초과 기간 65분"
    }
  ]
}
```

- **event_type** enum:
  - `postprandial_spike`: 식후 혈당 급상승
  - `hypoglycemia`: 저혈당 (<70 mg/dL)
  - `nocturnal_hypo`: 야간 저혈당
  - `dawn_phenomenon`: 새벽 현상 (공복 혈당 상승)
  - `somogyi_effect`: 소모기 효과
  - `exercise_induced_drop`: 운동 유도 혈당 저하
  - `stress_spike`: 스트레스/질병 유도 상승
  - `sensor_artifact`: 센서 오측정 의심
  - `normal_stable`: 정상 안정 구간

- **severity** enum: `mild` / `moderate` / `severe` / `critical`

- **likely_cause**: 다른 이벤트 ID를 참조 (식단/운동/약물 이벤트 중 연관된 것)

### 3. 데이터 품질 Annotation (data_quality)

```json
{
  "user_id_hash": "u_xxx",
  "date_range": ["2026-04-10", "2026-04-16"],
  "quality_label": {
    "overall": "good",
    "cgm_coverage": 0.92,
    "diet_logging_completeness": "partial",
    "exercise_logging_completeness": "good",
    "suspicious_patterns": ["sensor_pressure_artifact_20260412_0300"],
    "recommendation": "usable_for_training"
  }
}
```

- **overall** enum: `excellent` / `good` / `fair` / `poor` / `unusable`
- **cgm_coverage**: 0~1 (전체 시간 중 유효 측정 비율)
- **diet_logging_completeness** enum: `complete` / `good` / `partial` / `sparse` / `missing`
- **recommendation** enum: `usable_for_training` / `qa_only` / `exclude`

## Annotation 작업 프로세스

### 단계 1: 사전 선별

IT실에서 다음 조건을 만족하는 사용자-기간 세그먼트만 annotation으로 전달:
- CGM 연속 착용 ≥ 7일
- 식단 기록 최소 1일 3회 이상 (첫 3일 동안)
- 운동 기록 선택사항

### 단계 2: Annotation Tool

각 annotator는:
- CGM 그래프 (시간축, 혈당축, 이벤트 마커 표시)
- 식단/운동 타임라인 (같은 시간축 오버레이)
- 건강검진 정적 컨텍스트 (상단 박스)
- 라벨 입력 UI (위 3가지 스키마)

### 단계 3: 품질 관리

**Inter-annotator agreement**를 측정:
- 같은 샘플에 최소 2명 annotator 배정 (10% 샘플)
- Cohen's kappa 계산
- 목표: κ ≥ 0.70 (substantial agreement)
- κ < 0.70인 라벨 카테고리는 가이드라인 재정비

## Annotation Schema JSON

위 3가지 annotation은 각각 별도 JSON Schema 파일로 저장:
- `assets/schema_annot_meal.json`
- `assets/schema_annot_cgm_event.json`
- `assets/schema_annot_quality.json`

각 파일은 `$ref`로 원본 event/cgm 레코드를 참조.

## 민감도 고려

Annotation 자체가 의학적 판단이므로:
- **annotator는 의학 전공자(또는 의료진)** 로 제한
- **annotation 기록에 annotator_id 포함** (감사 및 품질 추적용)
- **IRB 승인 필수** (서울대 IRB 또는 공동 IRB)
- **annotation 결과물도 민감정보로 취급** (암호화, 접근 제어)

## 우선순위

Foundation model 사전학습에는 annotation이 필수는 **아닙니다**. 다음 단계에서 annotation 투입:

1. **사전학습**: annotation 없이 self-supervised (masked reconstruction, next-token prediction)
2. **소규모 파일럿 평가**: annotation 샘플 100~500건으로 다운스트림 성능 확인
3. **본격 파인튜닝**: annotation 수천 건 확보 후 특정 다운스트림 작업 학습
4. **장기 벤치마크 구축**: annotation을 공식 평가셋으로 고정

초기에는 annotation 부담을 줄이기 위해 **이벤트 분류(#2)와 품질 라벨(#3)만** 우선하고, 식사 의학적 분류(#1)는 모델이 자동 예측하도록 학습 후 검증하는 순서도 고려.

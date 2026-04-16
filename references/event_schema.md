# 식단 및 운동 이벤트 스키마

식단과 운동은 불규칙한 **이벤트**입니다. CGM 그리드에 섞지 않고, 원본 이벤트 형태로 보존한 뒤 학습 단계에서 그리드에 투영합니다.

## 식단 이벤트

### 필드 구조

```json
{
  "event_id": "meal_abc123",
  "user_id_hash": "u_xxx",
  "event_start": "2026-04-16T07:30:00+09:00",
  "event_end": null,
  "meal_type": "breakfast",
  "nutrients": {
    "kcal": 520,
    "carb_g": 75.0,
    "sugar_g": 12.0,
    "protein_g": 22.0,
    "fat_g": 15.0,
    "fiber_g": 6.0,
    "sodium_mg": 450
  },
  "foods": [
    {
      "food_id": "kr_food_0451",
      "food_name": "백미밥",
      "portion_g": 210,
      "source": "database"
    }
  ],
  "free_text_description": "아침 집밥, 된장국과 계란말이",
  "photo_id": "photo_789",
  "input_method": "manual",
  "confidence": 0.9
}
```

### 주요 필드 설명

- **event_end**: 정확한 식사 종료 시각을 모르면 `null`. 학습 시에는 식사 시작 후 기본 15분으로 가정하거나, 다음 혈당 변곡점까지로 확장 가능.
- **meal_type** enum: `breakfast` / `lunch` / `dinner` / `snack` / `late_night` / `unknown`
- **foods**: 개별 음식 리스트. 닥터다이어리 내부 food DB와 연결 가능하면 `food_id` 포함.
- **input_method** enum: `manual`(사용자 직접 입력) / `photo_ai`(사진 AI 인식) / `barcode` / `voice` / `import`(다른 앱에서 가져옴)
- **confidence**: 영양성분 추정의 신뢰도 (0~1). AI 인식일수록 낮고, 바코드는 0.95+. 학습 시 노이즈 weight로 활용.

### Nutrients 필드

필수 필드는 `kcal`, `carb_g`. 당뇨 관리 맥락에서 **carb_g가 혈당에 가장 영향**이 크므로 결측 시 이벤트를 `quality_flag = "low_quality"`로 표시.

선택 필드:
- `sugar_g`: 단순당 (당지수 예측에 유용)
- `fiber_g`: 식후 혈당 스파이크 완화 인자
- `glycemic_index`, `glycemic_load`: DB에서 조회 가능하면 추가
- `sodium_mg`, `cholesterol_mg`: 장기 건강 지표 예측용

### 결측 처리

```json
{
  "nutrients": {
    "kcal": 520,
    "carb_g": null,
    "_missing_fields": ["carb_g", "fiber_g"]
  }
}
```

`_missing_fields`는 메타 배열로 어떤 필드가 결측인지 명시.

## 운동 이벤트

### 필드 구조

```json
{
  "event_id": "ex_xyz789",
  "user_id_hash": "u_xxx",
  "event_start": "2026-04-16T18:00:00+09:00",
  "event_end": "2026-04-16T18:45:00+09:00",
  "duration_min": 45,
  "activity_type": "walking",
  "met_code": "17170",
  "met_value": 3.5,
  "intensity": "moderate",
  "metrics": {
    "steps": 4500,
    "distance_m": 3200,
    "kcal_burned": 180,
    "hr_avg_bpm": 115,
    "hr_max_bpm": 135,
    "elevation_gain_m": 12
  },
  "input_method": "wearable_sync",
  "device_source": "apple_health",
  "confidence": 0.95
}
```

### 주요 필드 설명

- **met_code**: Compendium of Physical Activities 2011 코드 (문자열). 예: `17170`=보통 속도 걷기, `12020`=자전거 타기 (보통).
- **met_value**: MET 수치. 결측 시 `activity_type`에서 매핑 테이블로 역산.
- **intensity** enum: `light`(<3 MET) / `moderate`(3~6 MET) / `vigorous`(≥6 MET)
- **input_method** enum: `manual` / `wearable_sync`(Apple Watch, Galaxy Watch 등) / `gps_tracked` / `import`
- **device_source**: 원본 기기 정보. pseudonymized.

### activity_type 주요 enum

닥터다이어리 사용자에 흔한 활동 위주:

```
walking, running, cycling, hiking, swimming,
yoga, pilates, weight_training, elliptical,
climbing, dancing, golf, tennis, badminton,
home_workout, daily_activity, other
```

### Metrics 필드 선택성

모든 기기가 동일한 메트릭을 제공하지 않습니다:
- **스마트폰만 있는 사용자**: `steps`, `distance_m`만 가능
- **스마트워치 사용자**: 위 + `hr_avg_bpm`, `hr_max_bpm`, `kcal_burned`
- **GPS 기록**: + `elevation_gain_m`, `pace_min_per_km`

없는 필드는 `null`. `_missing_fields` 배열로 명시.

## CGM 그리드로의 투영 방식

### 식단 투영

각 5분 스텝마다:

```python
# 해당 스텝 시점에 진행 중인 식사 이벤트가 있으면
meal_channel = {
  "is_meal_active": 1 or 0,
  "minutes_since_meal_start": int,  # 식후 경과 시간 (혈당 반응 예측의 핵심)
  "carb_g_cumulative": float,        # 직전 2시간 누적 탄수화물
  "meal_kcal_active": float          # 현재 소화중인 식사 kcal
}
```

핵심은 **`minutes_since_meal_start`**. 식후 30분, 60분, 120분 시점이 혈당 스파이크의 핵심 변곡점이므로 모델이 이 변수를 통해 식후 단계를 인지할 수 있습니다.

### 운동 투영

```python
exercise_channel = {
  "is_exercise_active": 1 or 0,
  "met_value_current": float,        # 현재 진행 중 운동의 MET
  "met_minutes_cumulative_1h": float, # 직전 1시간 MET-분 누적
  "minutes_since_exercise_end": int   # 운동 종료 후 경과 시간
}
```

운동은 **끝난 후에도 수 시간 혈당을 낮춥니다** (insulin sensitivity 향상). `minutes_since_exercise_end`가 이 지연 효과를 포착.

## 이벤트 간 충돌 처리

동시에 진행되는 이벤트 (예: 식사하면서 걷기 — 흔치 않지만 가능):
- 각 이벤트는 **독립 레코드**로 저장
- 투영 시에는 **각 채널에 모두 반영** (식단 채널 + 운동 채널 동시 활성)
- 같은 meal_type이 겹치면 event_id로 중복 확인

## 사용자 기록 행동 패턴 고려

실제 사용자는 **식사 직후가 아니라 나중에 몰아서** 기록하는 경우가 많습니다:
- `recorded_at` 필드 추가 (`event_start`는 사용자가 주장하는 식사 시각, `recorded_at`은 실제 입력 시각)
- 두 값이 크게 차이 나면 `confidence` 하향
- 모델 학습 시에는 `event_start` 사용, 품질 가중치로 `confidence` 활용

# CGM 5분 그리드 설계 상세

## 왜 5분 간격인가

대부분 상용 CGM 센서(Dexcom, FreeStyle Libre, Medtronic)는 **5분마다 혈당값을 출력**합니다. GluFormer와 CGMformer 모두 5분을 기준 그리드로 삼아 하루 288 스텝 시퀀스를 구성합니다. 닥터다이어리가 어떤 CGM 기기를 지원하든, 5분 간격으로 리샘플링한 후 저장하는 것이 표준화에 유리합니다.

## 토큰화 전략

### 원본 연속값 보존 + 토큰 파생

스키마는 **원본 연속값을 잃지 않도록** `glucose_mgdl`(float)을 주 필드로 두고, 학습 시 사용할 `glucose_token`(int, 0~259)을 파생 필드로 저장합니다.

```
token_id = clip(round(glucose_mgdl) - 40, 0, 259)
```

- 40 미만: 토큰 0 (극심한 저혈당)
- 40~299: 토큰 0~259 (1 mg/dL 단위)
- 300 이상: 토큰 259 (극심한 고혈당)

범위 외 값은 `out_of_range_flag`로 별도 표시.

### 왜 이산 토큰인가

- autoregressive LM 스타일 학습에 직접 사용 가능 (categorical cross-entropy)
- CGM 측정 오차(±10% MARD 수준)에 대한 견고성
- GluFormer, CGMformer, Chronos가 모두 채택

## 시간 인코딩

### 절대 시간과 주기 시간 모두 저장

```
timestamp       : ISO 8601 (2026-04-16T09:00:00+09:00)
minute_of_day   : 0~1439 (분 단위 하루 내 위치)
sin_time        : sin(2π · minute_of_day / 1440)
cos_time        : cos(2π · minute_of_day / 1440)
day_of_week     : 0~6 (월요일=0)
```

- `timestamp`: 기록 보존과 감사(audit) 용도
- `minute_of_day` + `sin_time`/`cos_time`: 모델 입력 (일주기 리듬 학습)
- `day_of_week`: 주간 리듬 (주말 식이·활동 패턴)

## 결측 처리

### 명시적 마스크

```json
{
  "timestamp": "2026-04-16T09:00:00+09:00",
  "glucose_mgdl": null,
  "glucose_token": null,
  "missing_mask": 1,
  "missing_reason": "sensor_gap"
}
```

`missing_mask`:
- `0`: 유효한 측정값
- `1`: 결측 (sensor_gap, sensor_warmup, calibration, manual_removal 등)

`missing_reason` enum:
- `sensor_gap`: 센서와 리시버 연결 끊김
- `sensor_warmup`: 센서 부착 직후 워밍업(1~2시간)
- `calibration`: 혈당계 보정 중
- `manual_removal`: 사용자가 수기로 제거
- `out_of_range`: 측정 범위 초과 (보통 40 미만 또는 400 초과)
- `unknown`

### 보간은 학습 단계에서

스키마 단계에서는 **절대 보간하지 않음**. 원본을 그대로 저장하고, 학습 스크립트에서 각 방법(linear, spline, mask-aware attention)을 실험.

## Quality Flag

CGM 센서는 측정 신뢰도 정보를 제공합니다:

```
quality_flag:
  - "normal"
  - "pressure_induced_drop"  # 수면 중 센서 압박으로 인한 일시적 저혈당 오측정
  - "rapid_change"           # 빠른 변화 시 정확도 저하
  - "sensor_degraded"        # 센서 수명 말기
  - "unknown"
```

## 24시간 Context Window

CGM-LSM이 채택한 **직전 24시간 → 다음 2시간** 예측 구조가 기본값입니다. 학습 샘플 단위:

```
input  : 288 스텝 (24시간, 5분 간격)
output : 24 스텝 (2시간, 5분 간격)
```

더 긴 context(예: 72시간)는 메모리 허용 시 실험. GluFormer는 autoregressive 구조라 길이 제약이 약함.

## 샘플링 시 주의사항

- **센서 교체 시점**: 새 센서 부착 후 첫 1~2시간은 워밍업으로 부정확 → `quality_flag = "sensor_degraded"` 또는 제외
- **공장 보정(factory-calibrated) vs 사용자 보정**: 기기별로 다름. 필드에 `calibration_type` 메타 저장
- **시차**: 해외 여행 시 KST 유지할지 현지 시간 사용할지 — 스키마는 **항상 offset 포함 ISO 8601**로 절대 시점 기록 + 별도 `local_timezone` 필드

## 기기 정보 메타데이터

CGM 기기별 특성을 모델이 구분할 수 있도록:

```json
{
  "device_model": "dexcom_g6",  // enum
  "device_serial_hash": "abc123",  // PII 아님, pseudonymized
  "sensor_session_id": "sess_456",  // 같은 센서 착용 기간 식별
  "sensor_day": 3  // 센서 착용 몇 일째인지 (정확도 변화 학습용)
}
```

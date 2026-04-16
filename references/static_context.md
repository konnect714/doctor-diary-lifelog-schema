# 건강검진 (정적 컨텍스트) 스키마

건강검진 데이터는 **시계열이 아닌 정적 컨텍스트**로 취급합니다. 연 1회 측정되며 CGM 시점에 비해 매우 드물게 업데이트되므로, 시계열에 섞지 않고 별도 테이블로 관리합니다.

학습 시: CGM 윈도우 시점 T에 대해 `T 이전의 가장 최근 검진 레코드`를 조회해 **조건 임베딩**으로 모델에 주입합니다.

## 필드 구조

```json
{
  "checkup_id": "ckup_20251015_u_xxx",
  "user_id_hash": "u_xxx",
  "exam_date": "2025-10-15",
  "exam_type": "national_health_screening",
  "demographics": {
    "age_years": 52,
    "sex": "male",
    "height_cm": 172.5,
    "weight_kg": 78.2,
    "bmi": 26.3,
    "waist_cm": 92.0
  },
  "vitals": {
    "sbp_mmhg": 134,
    "dbp_mmhg": 86,
    "resting_hr_bpm": 72
  },
  "blood_glucose": {
    "fasting_glucose_mgdl": 128,
    "hba1c_percent": 6.8,
    "postprandial_2h_mgdl": null,
    "ogtt_available": false
  },
  "lipid_panel": {
    "total_cholesterol_mgdl": 210,
    "hdl_mgdl": 48,
    "ldl_mgdl": 132,
    "triglycerides_mgdl": 180
  },
  "liver_kidney": {
    "ast_ul": 28,
    "alt_ul": 32,
    "ggt_ul": 45,
    "creatinine_mgdl": 0.95,
    "egfr": 88,
    "bun_mgdl": 15
  },
  "diabetes_status": {
    "diabetes_type": "type2",
    "years_since_diagnosis": 4,
    "current_medications": ["A10BA02", "A10BK01"],
    "insulin_therapy": false
  },
  "comorbidities": ["I10", "E78.5"],
  "family_history": {
    "diabetes": true,
    "cardiovascular": true,
    "details_hash": "fh_abc"
  },
  "smoking": "former",
  "alcohol_weekly_units": 7,
  "data_source": "imported_from_checkup_report",
  "sensitive_access_required": true
}
```

## 필드 설명

### exam_type enum

- `national_health_screening`: 국가건강검진
- `company_checkup`: 직장 건강검진
- `comprehensive_premium`: 종합검진
- `diabetes_followup`: 당뇨 추적 검사 (3~6개월 주기)
- `self_reported`: 사용자 입력 (공식 문서 없음)

### diabetes_type enum

- `none`: 비당뇨
- `prediabetes`: 공복혈당장애 / 내당능장애
- `type1`
- `type2`
- `gestational`
- `mody`: 청년 발병 성인형 당뇨
- `other`
- `unknown`

### medications 코딩

**ATC (Anatomical Therapeutic Chemical) 코드** 사용:
- `A10A*`: 인슐린 및 유사체
- `A10BA02`: 메트포르민
- `A10BB*`: 설포닐우레아
- `A10BH*`: DPP-4 억제제
- `A10BJ*`: GLP-1 수용체 작용제
- `A10BK*`: SGLT2 억제제
- `C*`: 심혈관계 약물 (고혈압, 이상지질혈증 등)

닥터다이어리가 자체 약물 코드를 쓴다면 매핑 테이블 필요.

### comorbidities 코딩

**ICD-10 코드** 배열. 주요 당뇨 연관:
- `E10`: Type 1 diabetes
- `E11`: Type 2 diabetes
- `E78.5`: Hyperlipidemia
- `I10`: Essential hypertension
- `N18`: Chronic kidney disease
- `E66`: Obesity

## 결측 처리

건강검진은 항목별 결측이 매우 흔합니다:
- 국가건강검진은 HbA1c 미포함일 수 있음
- OGTT(경구당부하검사)는 드뭄
- 여성 사용자는 waist_cm 결측이 더 흔함 (문화적)

**결측은 `null`**, 각 섹션마다 `_missing_fields` 메타 배열로 명시.

## 최근 검진값 조회 규칙

CGM 윈도우 시점 T에 대해:

```python
def get_active_checkup(user_id, T):
    candidates = checkups.filter(
        user_id_hash=user_id,
        exam_date <= T.date()
    ).order_by("-exam_date")
    
    if not candidates:
        return None  # 검진 데이터 없음 → null 임베딩 사용
    
    latest = candidates.first()
    
    # 너무 오래된 검진은 신뢰도 하향
    days_old = (T.date() - latest.exam_date).days
    staleness = min(days_old / 365, 2.0)  # 2년 이상이면 상한
    
    return latest, staleness
```

**staleness 변수**는 모델 입력에 포함. 검진 후 경과 시간이 길수록 현재 상태와 괴리 가능성이 높음.

## 민감도 및 접근 제어

`sensitive_access_required: true`로 표시된 필드는:
- 서울대 annotation 작업자는 접근 가능 (의학적 맥락 해석 필요)
- KAIST 학습 파이프라인은 **hash된 임베딩만** 접근 (원본 미노출)
- 닥터다이어리 IT실은 원본 보관 (법적 보관 의무)

특히 민감:
- `diabetes_status.current_medications`
- `comorbidities`
- `family_history.details_hash`

이 필드들은 differential privacy나 k-anonymity 처리 후 학습에 사용 권장.

## 시간 변동 필드 처리

일부 필드는 검진 사이에 변할 수 있음:
- `current_medications`: 의사 처방 변경 시 업데이트
- `weight_kg`, `bmi`: 사용자가 앱 내에서 갱신 가능

이 경우 **이력 테이블 별도 운영**:

```json
{
  "user_id_hash": "u_xxx",
  "field": "current_medications",
  "updated_at": "2026-01-20T10:00:00+09:00",
  "value": ["A10BA02", "A10BK01", "A10BJ05"],
  "source": "self_reported"
}
```

학습 시 T 시점에 유효한 가장 최근 값 사용.

## 인구학적 변수 처리

`age_years`, `sex`는 가장 기본적인 인구학 변수로 거의 모든 downstream 작업에 유효합니다. 두 변수는 **검진 없어도 회원가입 정보**에서 가져올 수 있으므로, 검진 레코드와 **별도의 `user_profile` 테이블**로 분리 저장 권장:

```json
// user_profile (검진과 별개, 항상 존재)
{
  "user_id_hash": "u_xxx",
  "birth_year": 1973,
  "sex": "male",
  "registration_date": "2024-03-15",
  "cohort_type": "adult"  // adult, pregnant, pediatric 등
}
```

GluFormer가 비당뇨 성인 중심으로 학습되어 일반화에 성공한 사례를 참고할 때, **cohort_type을 명시**해두면 나중에 서브셋 분석이 쉬움.

# Glossary

닥터다이어리 lifelog schema 프로젝트의 전체 용어집.

## Acronyms
| Term | Meaning | Context |
|------|---------|---------|
| CGM | Continuous Glucose Monitoring | 5분 간격 혈당 측정 |
| FM | Foundation Model | GluFormer, CGMformer, CGM-LSM 등 |
| MET | Metabolic Equivalent of Task | Compendium 2011 기반 |
| HbA1c | 당화혈색소 | 2-3개월 평균 혈당 |
| HMAC | Hash-based Message Authentication Code | user_id pseudonymize |
| KST | Korea Standard Time | UTC+09:00 |
| PII | Personally Identifiable Information | 스키마에서 제거 대상 |
| PHI | Protected Health Information | 민감 의료 정보 |
| ICD-10 | International Classification of Diseases | comorbidities 코딩 |
| ATC | Anatomical Therapeutic Chemical | 약물 코딩 (A10BA02=메트포르민) |
| TIR | Time in Range | 70-180 mg/dL 유지 비율 |
| TAR | Time Above Range | >180 mg/dL |
| TBR | Time Below Range | <70 mg/dL |
| OGTT | Oral Glucose Tolerance Test | 경구 포도당 부하 검사 |
| JSONL | JSON Lines | 레코드당 1줄 |
| CI | Continuous Integration | GitHub Actions |

## Internal Terms
| Term | Meaning |
|------|---------|
| 3층 구조 | Layer 1 (CGM) + Layer 2 (이벤트) + Layer 3 (정적 컨텍스트) |
| 260-bin | CGM 기본 토큰화: clip(round(glucose)-40, 0, 259) |
| 460-bin | GluFormer 확장 토큰화: 40-500 mg/dL |
| 그리드 정렬 | 이벤트 → 5분 CGM 그리드 채널 투영 (align_to_grid.py) |
| 정적 컨텍스트 | 건강검진 데이터, 시계열과 분리 저장 |
| staleness | 검진 후 경과 일수 (2년 상한) |
| pseudonymize | HMAC-SHA256로 사용자 ID 비식별화 |
| manifest | 데이터 전달 시 파일 목록 + SHA-256 해시 |
| smoke test | 기본 동작 확인 테스트 (test_align.sh) |

## Schema Types
| Type | File | Description |
|------|------|-------------|
| cgm | schema_cgm.json | CGM 5분 측정 레코드 (28필드) |
| diet | schema_diet.json | 식단 이벤트 (16필드) |
| exercise | schema_exercise.json | 운동 이벤트 (14필드) |
| checkup | schema_checkup.json | 건강검진 정적 컨텍스트 (38필드) |
| annot_meal | schema_annot_meal.json | 식사 의학 annotation |
| annot_cgm_event | schema_annot_cgm_event.json | CGM 임상 이벤트 annotation |
| annot_quality | schema_annot_quality.json | 데이터 품질 annotation |

## Key Papers
| Shorthand | Full Title | Venue | Year |
|-----------|-----------|-------|------|
| GluFormer | A foundation model for CGM data | Nature | 2026 |
| CGMformer | BERT-style masked pretraining for CGM | PMC | 2025 |
| CGM-LSM | Large Sensor Model for CGM | npj Health Systems | 2025 |
| Virtual CGM | Life-log based glucose inference | Sci Rep | 2025 |
| WBM | Wearable Behavioral Model | Apple | 2025 |
| LSM | Large Sensor Model (general) | ICLR | 2025 |
| AttenGluco | Multimodal Transformer for CGM | arXiv | 2025 |
| WEAR-ME | Insulin resistance from wearables | Nature | 2026 |

## Organizations
| Shorthand | Full Name | Role |
|-----------|-----------|------|
| IT실 | 닥터다이어리 IT실 | 원본 데이터 추출 (Layer 1) |
| KAIST | KAIST AI 대학원 | FM 학습 (Layer 2) |
| 서울대 | 서울대 의과학실 | Annotation (Layer 3) |

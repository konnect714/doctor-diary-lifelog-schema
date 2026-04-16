# Memory

## Me
DJ (konnect714), Doctor Diary lifelog schema 프로젝트 관리자. 닥터다이어리 앱 데이터를 foundation model 학습용으로 정제하는 스키마 설계·최적화를 담당.

## People
| Who | Role |
|-----|------|
| **DJ** | 프로젝트 오너, konnect714@gmail.com |
| **IT실** | 닥터다이어리 IT실 — 원본 데이터 추출 (Layer 1) |
| **KAIST** | KAIST AI 대학원 — FM 사전학습/파인튜닝 (Layer 2) |
| **서울대** | 서울대 의과학실 — Annotation & 의학 검증 (Layer 3) |
→ Full list: memory/people/

## Terms
| Term | Meaning |
|------|---------|
| CGM | Continuous Glucose Monitoring, 5분 그리드 |
| FM | Foundation Model (GluFormer, CGMformer 등) |
| 3층 구조 | CGM 그리드 / 이벤트 채널 / 정적 컨텍스트 |
| 260-bin | 기본 토큰화: 40-299 mg/dL → 0-259 |
| 460-bin | GluFormer 호환: 40-500 mg/dL → 0-459 |
| MET | Metabolic Equivalent of Task |
| HMAC | 사용자 ID pseudonymize 방식 |
| KST | Korea Standard Time (+09:00) |
→ Full glossary: memory/glossary.md

## Projects
| Name | What | Status |
|------|------|--------|
| **lifelog-schema** | 닥터다이어리 데이터 스키마 v1.1.0 | Active |
| **데이터 추출** | IT실 앱 DB → JSONL 파이프라인 | 준비 중 |
| **FM 학습** | KAIST CGM foundation model | 계획 |
| **Annotation** | 서울대 임상 이벤트 라벨링 | 계획 |
→ Details: memory/projects/

## Tech Stack
| Tool | Purpose |
|------|---------|
| GitHub | konnect714/doctor-diary-lifelog-schema |
| JSON Schema | Draft 2020-12 |
| Python | validate.py, align_to_grid.py, extract_from_app.py |
| NumPy | 학습 텐서 (.npz) |

## Preferences
- 한국어 우선, 코드 주석은 한/영 혼용
- 논문 근거 있는 설계 선호
- 자동화 + 에이전트 기반 워크플로 선호
- 실행 멈추지 말고 계속 진행

## Schema Version History
| Version | Date | Key Changes |
|---------|------|-------------|
| 1.0.0 | 2026-04-16 | 초기 버전 — 7개 스키마, 샘플, 검증 |
| 1.1.0 | 2026-04-16 | GluFormer 460-bin, 품질 메트릭, 추출 스크립트, CI 강화 |

## Key Findings (Latest)
- GluFormer (Nature 2026): 460 토큰, 10,812명, HbA1c 대비 우수
- CGM-LSM (2025): GPT-2 디코더, RMSE 48% 감소
- AttenGluco (2025): cross-attention 멀티모달 융합
- 데이터 완성도 80% 이상 필요 (CGM Missing Data 연구)

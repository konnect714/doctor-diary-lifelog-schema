# Doctor Diary Lifelog Schema

닥터다이어리 앱의 lifelog 데이터를 시계열 foundation model (CNN + Transformer) 학습용으로 수집·정렬하기 위한 **데이터 스키마 정의 및 도구** 저장소입니다.

## 협업 조직

| 조직 | 역할 |
|------|------|
| 닥터다이어리 IT실 | 원본 데이터 추출 및 내보내기 (Layer 1) |
| KAIST AI 대학원 | Foundation model 사전학습·파인튜닝 (Layer 2) |
| 서울대 의과학실 | Annotation 및 의학적 검증 (Layer 3) |

## 핵심 설계: 3층 구조

이질적 주기성(5분 CGM / 이벤트성 식단·운동 / 연 1회 검진)을 하나의 시계열에 섞지 않고 분리합니다. 설계 근거는 `references/papers.md`의 논문 매핑표 참조.

- **Layer 1** — CGM 5분 고정 그리드 (하루 288 스텝). GluFormer·CGMformer 표준.
- **Layer 2** — 식단·운동은 원본 이벤트로 저장, 학습 시 CGM 그리드에 채널로 투영.
- **Layer 3** — 건강검진은 정적 컨텍스트로 분리, 학습 윈도우에 조건 임베딩으로 주입.

## 저장소 구조

```
doctor-diary-lifelog-schema/
├── SKILL.md                      # Claude 스킬 정의 (트리거 + 원칙)
├── README.md                     # 이 파일
├── LICENSE                       # Apache-2.0
├── CONTRIBUTING.md               # 3개 조직 협업 규칙
├── CHANGELOG.md                  # 스키마 버전 이력
├── assets/
│   ├── schema_cgm.json           # JSON Schema (Draft 2020-12)
│   ├── schema_diet.json
│   ├── schema_exercise.json
│   ├── schema_checkup.json
│   ├── schema_annot_meal.json
│   ├── schema_annot_cgm_event.json
│   ├── schema_annot_quality.json
│   ├── sample_data.json
│   └── sample_annotations.json
├── references/
│   ├── papers.md                 # 논문 근거 매핑표
│   ├── cgm_grid.md               # CGM 5분 그리드 상세
│   ├── event_schema.md           # 식단·운동 이벤트 스키마 상세
│   ├── static_context.md         # 건강검진 정적 컨텍스트 상세
│   ├── annotation_guide.md       # 서울대 annotation 작업 가이드
│   └── org_interface.md          # IT실↔KAIST↔서울대 인터페이스 계약
├── scripts/
│   ├── validate.py               # 스키마 + 의미론적 검증
│   └── align_to_grid.py          # 이벤트 → 5분 그리드 투영
└── tests/
    └── test_samples.sh           # CI용 테스트 스크립트
```

## 빠른 시작

### 설치

```bash
git clone <this-repo-url>
cd doctor-diary-lifelog-schema
pip install -r requirements.txt
```

### 샘플 데이터 검증

```bash
python scripts/validate.py --sample
```

기대 출력: 8개 샘플 모두 `[PASS]`.

### 실제 데이터 검증

```bash
python scripts/validate.py mydata.jsonl --type cgm
python scripts/validate.py meals.jsonl --type diet
python scripts/validate.py exercise.jsonl --type exercise
python scripts/validate.py checkups.jsonl --type checkup
```

### 이벤트 → 5분 그리드 정렬

```bash
python scripts/align_to_grid.py \
    --cgm data/cgm.jsonl \
    --diet data/diet.jsonl \
    --exercise data/exercise.jsonl \
    --start "2026-04-16T00:00:00+09:00" \
    --end "2026-04-17T00:00:00+09:00" \
    --out window_20260416.npz
```

출력: 288 스텝 × 15 채널 NumPy 배열 (`.npz`).

## 조직별 가이드

### 🏢 닥터다이어리 IT실 담당자

**당신이 해야 할 일**: 앱 DB → Layer 1 JSON 파일 생성 및 KAIST·서울대 전달.

1. `assets/schema_*.json` 각 파일의 필드 정의를 검토. 내부 DB 필드와의 매핑 표 작성.
2. 추출 파이프라인 작성 시:
   - PII(이름·전화번호·주소·이메일)는 **절대 포함하지 않음**
   - `user_id`는 HMAC-SHA256으로 pseudonymize → `user_id_hash`
   - `timestamp`는 항상 KST offset(`+09:00`) 포함 ISO 8601
3. 추출 후 `scripts/validate.py --type <kind>`로 **반드시 사전 검증**
4. 상세 포맷·전달 방식은 `references/org_interface.md` 참조

### 🎓 KAIST AI 대학원 담당자

**당신이 해야 할 일**: Layer 1 JSON → Layer 2 학습 텐서 변환, 모델 개발.

1. `references/papers.md`에서 설계 근거가 된 foundation model 논문들 확인
2. `scripts/align_to_grid.py`를 참고해 본인의 학습 window 전략으로 커스터마이즈
3. 모델 입력 채널 설계: CGM 6 + 식단 4 + 운동 4 = 시계열 14채널 + 정적 컨텍스트
4. 아키텍처 제안(논문 근거):
   - CGM 단기 패턴 → CNN (receptive field 작지만 효율적)
   - 장기 context·식단/운동 결합 → Transformer
   - 정적 검진 → 조건 임베딩으로 주입

### 🏥 서울대 의과학실 담당자

**당신이 해야 할 일**: 의학적 annotation + 데이터 품질 판정.

1. `references/annotation_guide.md`를 먼저 읽으세요 — 작업 3종(식사 분류·CGM 이벤트·품질)의 라벨 정의와 절차가 있습니다.
2. Annotation 스키마는 `assets/schema_annot_*.json`.
3. Annotation 도구는 별도 UI 제공 예정 (이 저장소에는 포맷만 정의).
4. 의학적 판단이 필요한 민감 필드는 `references/static_context.md`의 접근 제어 원칙 준수.
5. Inter-annotator agreement 목표: Cohen's κ ≥ 0.70.

## 스키마 버전 관리

- Semantic Versioning 적용. 현재 모든 스키마 `1.0.0`.
- `1.0.x`: 버그 수정, enum 값 추가 (하위 호환)
- `1.x.0`: 선택 필드 추가
- `x.0.0`: Breaking change (필드 제거 등, 3개 조직 합의 필수)
- 변경 이력은 `CHANGELOG.md`에 기록

## 기여 방법

`CONTRIBUTING.md` 참조. 간단 요약:

1. 이슈 생성 → 논의
2. 브랜치 생성 (`feat/xxx`, `fix/xxx`, `docs/xxx`)
3. PR 시 CI(`validate.py --sample`)가 자동 실행됨
4. 스키마 변경은 3개 조직 대표자 리뷰 필요

## 라이선스

Apache License 2.0. 자세한 내용은 `LICENSE` 파일 참조.

## 근거 논문

핵심 참고 논문은 `references/papers.md`에 매핑표와 함께 정리됨. 주요 논문:

- GluFormer (Nature 2026) — CGM foundation model
- CGMformer (PMC 2025) — BERT-style masked pretraining
- CGM-LSM (arXiv 2024) — decoder-only LM 구조
- Virtual CGM (Sci Rep 2025) — life-log 기반 혈당 추론
- WBM (Apple 2025) — 웨어러블 행동 데이터 FM
- LSM (ICLR 2025) — 센서 FM 스케일링
- EHR+Wearable Foundation Model (2026) — 다중 시간 스케일 통합

## 문의

- 닥터다이어리 IT실: (담당자 연락처 추가 필요)
- KAIST AI 대학원: (담당자 연락처 추가 필요)
- 서울대 의과학실: (담당자 연락처 추가 필요)

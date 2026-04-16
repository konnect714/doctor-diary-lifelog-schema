# Foundation Model 논문 근거 요약

본 스키마 설계가 근거하는 주요 논문들과 각 논문에서 차용한 설계 결정.

## 1. GluFormer (Nature, 2026 — Lutsker et al.)

- **URL**: https://www.nature.com/articles/s41586-025-09925-9
- **arXiv**: https://arxiv.org/abs/2408.11876
- **규모**: 10,812명 성인의 1,000만+ CGM 측정값
- **구조**: Transformer decoder + autoregressive next-token prediction
- **토큰화**: 연속 혈당값을 이산 bin으로 변환
- **핵심 결과**: 19개 외부 코호트(5개국, 8개 CGM 기기)에 일반화. HbA1c보다 당뇨 발병(66% vs 7%)과 심혈관 사망(69% vs 0%)을 상위 quartile에서 더 잘 예측.
- **멀티모달 확장**: 식이 데이터 통합으로 개별 혈당 반응 예측 가능.

**차용한 설계 결정**:
- CGM을 autoregressive 시퀀스로 모델링 → 5분 그리드 표준화
- 식단을 별도 이벤트가 아닌 조건 데이터로 통합하는 방식
- 사전학습용 데이터는 **비당뇨인**도 대량 포함 (범용성 확보)

## 2. CGMformer (PMC, 2025)

- **URL**: https://pmc.ncbi.nlm.nih.gov/articles/PMC11970253/
- **구조**: Transformer encoder + masked language modeling (BERT 스타일)
- **토큰화**: 40~300 mg/dL 범위를 **260개 이산 레벨**로 변환, 하루 288 토큰 시퀀스 (5분 간격)
- **시간 인코딩**: sin/cos positional encoding으로 24시간 주기성 표현
- **학습 목표**: 45~60% 토큰 마스킹, TF-IDF 가중치로 고/저혈당 토큰에 높은 마스킹 비중
- **다운스트림**: 비당뇨인을 6개 T2D 위험 클러스터로 분류, 개인화 식이 추천

**차용한 설계 결정**:
- **260개 bin, 1 mg/dL 단위** → schema_cgm.json의 `glucose_token` 필드
- **하루 288 스텝 (5분)** → CGM 그리드 표준
- **sin/cos time encoding** → `sin_time`, `cos_time` 필드 추가

## 3. CGM-LSM (arXiv 2412.09727)

- **URL**: https://arxiv.org/abs/2412.09727
- **GitHub**: https://github.com/JHU-CDHAI/cgmlsm
- **규모**: 160만 CGM 레코드
- **구조**: Transformer decoder (GPT 스타일) + autoregressive
- **입력/출력**: 직전 24시간 → 다음 2시간 예측
- **성능**: 1시간 horizon에서 RMSE 48.51% 감소

**차용한 설계 결정**:
- **24시간 context window** → 학습 단위 기본값
- CNN보다 Transformer가 receptive field 측면에서 유리 → 사용자의 아키텍처(CNN + Transformer)에서 **CGM 단기는 CNN, 장기 context는 Transformer** 역할 분담의 근거

## 4. Life-log based Virtual CGM (Scientific Reports, 2025)

- **URL**: https://www.nature.com/articles/s41598-025-01367-7
- **규모**: 171명 건강한 성인, 식이·활동·혈당 기록
- **구조**: Bidirectional LSTM encoder-decoder + dual attention (temporal + feature)
- **샘플링 전략**: 식사 이벤트를 기준(0분)으로 삼고, **이전 90분 ~ 이후 90분** 구간 추출
- **시간 인코딩**: sin/cos 삼각함수로 24시간 주기성 반영
- **성능**: RMSE 19.49 mg/dL, MAPE 12.34%

**차용한 설계 결정**:
- **식사 이벤트 중심 window 추출** → 학습 데이터 샘플링 전략 (식후 반응 학습용)
- 닥터다이어리 데이터처럼 **식단 + 운동 + CGM**이 결합된 데이터셋의 직접적 선례

## 5. WBM — Wearable Behavioral Model (Apple, 2025)

- **URL**: https://arxiv.org/html/2507.00191v1
- **규모**: 162K 참가자, 150억+ 시간별 측정
- **구조**: Mamba-2 backbone, 시간별 patch 입력
- **데이터 형식**: **168시간 × 54변수 행렬** (일주일), missingness mask 포함
- **핵심 문제**: 불규칙 샘플링과 결측 처리

**차용한 설계 결정**:
- **명시적 missingness mask** → 모든 시계열 스키마에 `missing_mask` 필드 필수
- 시간 단위 aggregation으로 이질적 샘플링 주기 통일
- 27개 행동 변수 × 2 (값 + 마스크) = 54 채널 구조 → 본 프로젝트의 다채널 입력 설계 참고

## 6. LSM — Large Sensor Model (ICLR 2025)

- **URL**: https://ubicomplab.cs.washington.edu/pdfs/lsm_iclr25.pdf
- **데이터 형식**: **26 신호 × 300분 2D 행렬**
- **학습 목표**: masked signal reconstruction (MSE)
- **스케일링 법칙**: 10^7 시간 데이터에서 포화, 운동 감지 +27% 정확도

**차용한 설계 결정**:
- **2D 행렬 형태의 학습 입력** (변수 × 시간) → 최종 학습 텐서 layout
- Masked reconstruction을 pretraining objective로 고려

## 7. Multimodal EHR + Wearable Foundation Model (arXiv 2601.12227, 2026)

- **URL**: https://arxiv.org/html/2601.12227v1
- **핵심 아이디어**: EHR(희소·이벤트)과 웨어러블(조밀·연속)을 **단일 연속시간 잠재 프로세스**로 통합. 모달리티별 인코더 + 공유 temporal backbone.
- **학습 목표**: self-supervised + cross-modal alignment (InfoNCE 스타일)

**차용한 설계 결정**:
- **건강검진(EHR-like)과 CGM(wearable-like) 분리** → Layer 3의 정적 컨텍스트 근거
- 모달리티별 encoder → CNN(CGM) + Transformer(context) 아키텍처의 설계 원칙
- 비동기 업데이트 허용 (검진은 연 1회, CGM은 5분마다)

## 설계 결정 → 논문 매핑 요약표

| 설계 결정 | 근거 논문 |
|----------|----------|
| CGM 5분 그리드, 하루 288 스텝 | CGMformer, GluFormer |
| 260개 bin 토큰화 | CGMformer |
| sin/cos 시간 인코딩 | CGMformer, Virtual CGM |
| 24시간 입력 window | CGM-LSM |
| 명시적 missing_mask | WBM, LSM |
| 식사 이벤트 중심 window | Virtual CGM (Sci Rep) |
| 건강검진을 정적 컨텍스트로 분리 | EHR+Wearable FM |
| 2D 행렬 (변수 × 시간) 학습 입력 | LSM, WBM |
| CNN(단기) + Transformer(장기) 분업 | CGM-LSM (receptive field 논의) |

## 주의할 점

- **CGM-LSM은 CNN을 "receptive field 제한"으로 비판**하지만, 본 프로젝트는 **CNN을 CGM의 단기 패턴 추출기, Transformer를 다모달 context 결합에 사용**하는 하이브리드이므로 모순되지 않음. 오히려 Hybrid Transformer-LSTM 논문(PMC 2024)과 같은 계열.
- **GluFormer는 비당뇨인 중심**으로 사전학습해 일반화를 확보했음. 닥터다이어리도 **당뇨 사용자만 학습시키면 일반화에 제약**이 생길 수 있음 → 코호트 구성 시 고려.
- **모든 논문이 성인 대상**. 소아·임산부 데이터가 포함될 경우 스키마에 `cohort_type` 필드 추가 권장.

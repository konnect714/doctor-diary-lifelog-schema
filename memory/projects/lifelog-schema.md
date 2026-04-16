# Doctor Diary Lifelog Schema

**Repo:** github.com/konnect714/doctor-diary-lifelog-schema
**Status:** Active, v1.1.0
**Owner:** DJ (konnect714)

## What It Is
닥터다이어리 앱의 lifelog 데이터(CGM, 식단, 운동, 건강검진)를 시계열 foundation model 학습용으로 수집·정렬하기 위한 데이터 스키마 정의 저장소.

## Architecture
3층 구조:
- Layer 1: CGM 5분 고정 그리드 (288 steps/day)
- Layer 2: 식단/운동 이벤트 (원본 보존 → 학습 시 그리드 투영)
- Layer 3: 건강검진 정적 컨텍스트 (조건 임베딩)

## Key Files
- 7개 JSON Schema (assets/)
- validate.py, align_to_grid.py, extract_from_app.py, met_mapping.py (scripts/)
- 6개 참조 문서 (references/)
- CI: GitHub Actions (Python 3.10/3.11/3.12)

## Version History
| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-04-16 | 초기 릴리스 |
| 1.1.0 | 2026-04-16 | GluFormer 호환, 품질 메트릭, 추출 스크립트, CI 강화 |

## Optimization Log (v1.1.0)
- 14건 이슈 발견 (CRITICAL 3, HIGH 3, MEDIUM 4, LOW 4)
- 8편 최신 논문 검증 (2024-2026)
- 12개 필드 추가, 4개 신규 파일, 6개 파일 수정
- 벤치마크: 8/8 샘플 PASS, alignment smoke test PASS

## Next Steps
1. IT실: HMAC-SHA256 user_id_hash 형식 확정
2. IT실: extract_from_app.py 커스터마이즈 후 실데이터 추출
3. KAIST: Layer 2 HDF5/Zarr 구조 정의
4. 서울대: Annotation UI 개발
5. 전체: Pydantic 모델 추가, 실데이터 1000건+ 통합 테스트

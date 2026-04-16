# Contributing Guide

이 저장소는 세 조직(닥터다이어리 IT실, KAIST AI 대학원, 서울대 의과학실)이 함께 편집합니다. 스키마 변경이 세 조직의 파이프라인에 모두 영향을 주므로 신중한 협업 프로세스가 필요합니다.

## 기여 절차

### 1. 이슈 먼저

큰 변경(필드 추가·제거·rename, 스크립트 동작 변경)은 **PR 전에 이슈를 먼저 생성**해 논의합니다. 작은 수정(오타, 문서 보강, 테스트 추가)은 바로 PR 가능.

이슈 템플릿:
- **맥락**: 왜 이 변경이 필요한가
- **영향 범위**: 세 조직 중 누구의 작업에 영향을 주는가
- **하위 호환성**: 기존 데이터로 계속 동작하는가

### 2. 브랜치 전략

`main`은 안정 브랜치. 직접 커밋 금지.

브랜치 네이밍:
- `feat/add-hba1c-history` — 새 기능/필드
- `fix/cgm-token-off-by-one` — 버그 수정
- `docs/annotation-guide-update` — 문서만
- `schema/v1.1.0-exercise-hrv` — 스키마 변경 (버전 명시)

### 3. 커밋 메시지

Conventional Commits 권장:

```
feat(schema): add hba1c_history field to checkup schema

HbA1c 추적이 필요한 다운스트림 작업을 위해 과거 검진값 배열 추가.
필드는 선택사항이므로 하위 호환.

Refs #42
```

### 4. Pull Request

PR 설명에 포함할 것:
- 변경 요약
- 스키마 변경이면 **영향 받는 조직** 명시 (IT실 / KAIST / 서울대)
- 하위 호환성 여부
- 리뷰 요청 대상 (3개 조직 중 관련된 대표자)

PR이 생성되면 CI가 자동으로 `scripts/validate.py --sample`을 실행합니다. 통과해야 머지 가능.

## 스키마 변경 규칙

### Semantic Versioning

각 스키마 파일의 `schema_version` 필드:

- **1.0.0 → 1.0.1 (PATCH)**: 버그 수정, 문서 보강, enum 값 추가만. 하위 호환 보장.
- **1.0.0 → 1.1.0 (MINOR)**: **선택 필드** 추가. 기존 데이터는 그대로 유효.
- **1.0.0 → 2.0.0 (MAJOR)**: 필드 제거, 필수 필드 추가, 타입 변경 등 breaking change.

### 변경 승인

| 버전 유형 | 필요한 승인 |
|----------|------------|
| PATCH | 1명 리뷰어 |
| MINOR | 2명 리뷰어 (서로 다른 조직 1명 이상 포함) |
| MAJOR | 3개 조직 대표자 모두 승인 + 전환 계획 문서화 |

### 전환 계획 (MAJOR 변경 시)

1. 구버전·신버전 **병행 지원 최소 1개월**
2. `CHANGELOG.md`에 마이그레이션 가이드 작성
3. IT실의 export 파이프라인 업데이트 완료 확인 후 구버전 deprecation

### 변경 후 필수 작업

- [ ] `schema_version` 필드 값 업데이트
- [ ] `CHANGELOG.md`에 기록
- [ ] 샘플 데이터(`assets/sample_*.json`)도 신버전에 맞게 수정
- [ ] `scripts/validate.py --sample` 통과 확인
- [ ] 관련 `references/*.md` 문서 업데이트
- [ ] `README.md` 업데이트 (필요 시)

## 코드 스타일

### Python

- `black` 포맷터 (line length 100)
- `ruff` 린터
- 타입 힌트 권장

### JSON Schema

- 들여쓰기 2칸
- 필드 순서: `type` → `enum`/`format`/`pattern` → `description` → 기타 제약
- 한글 `description` 허용 (오히려 권장 — 의학 용어 정확성)

## 의료 데이터 취급

**이 저장소에는 실제 사용자 데이터를 절대 커밋하지 마십시오.**

`.gitignore`에 `*.jsonl`, `data/`, `exports/`, `*.npz` 등이 등록되어 있지만 이는 최후의 안전망이며, 커밋 전 `git diff`로 반드시 확인.

샘플 데이터(`assets/sample_*.json`)는 **합성 데이터**이며 실제 사용자와 무관합니다.

## 리뷰 관점

PR 리뷰 시 다음을 확인:

### 공통
- [ ] 샘플 데이터 검증 통과
- [ ] `CHANGELOG.md` 업데이트
- [ ] 문서 최신화

### IT실 리뷰 관점
- 추출 파이프라인에서 이 필드를 실제로 제공 가능한가
- PII 유출 가능성
- 기존 DB 스키마와의 매핑 가능성

### KAIST 리뷰 관점
- 학습 입력 텐서 구조에 반영 가능한가
- `align_to_grid.py`에 추가 로직 필요한가
- 기존 학습 코드와 호환

### 서울대 리뷰 관점
- 의학적으로 타당한 필드·단위·enum인가
- Annotation 작업 부담에 영향
- 민감정보 분류 적절성

## 연락

- 이슈/PR은 GitHub에서
- 긴급 사안이나 민감 데이터 관련 논의는 오프라인/이메일로

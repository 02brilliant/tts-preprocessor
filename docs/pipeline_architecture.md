# Pipeline & Architecture

본 문서는 TTS 전처리 엔진의 핵심 설계 원칙과 실행 단계를 정의한다.

## 1. 핵심 원칙 (Core Invariance Principle)

*   **한글 불변성:** 입력된 한글 문자열은 어떠한 단계에서도 수정하지 않으며, 공백과 문장부호를 보존한다.
*   **Typed Surface 기반:** 숫자, 기호 등 변환이 필요한 대상만 구조적 읽기 단위인 `typed surface`로 변환하여 관리한다.
*   **표면 중심 복원:** 변환된 결과물은 최종 단계에서만 텍스트로 렌더링되어 한글 문맥의 훼손을 방지한다.

## 2. 파이프라인 실행 단계

1.  **Early Preprocessing:** 괄호 처리, 쉼표 숫자 정규화 등 파서 진입 전 최소 정규화 및 보호 대상 식별.
2.  **Dictionary / Fixed Mapping:** 사전 기반의 고정 매핑 적용 (Acronym 등).
3.  **Rules Engine:** 날짜, 시간, 단위, 수사 등 복합 패턴 분석 및 `typed surface` 생성.
4.  **Typed Surface Registration:** 분석된 결과를 구조적 메타데이터로 등록하고 조사를 안전하게 부착.
5.  **Surface-aware Restoration:** 등록된 `typed surface`를 최종 읽기 텍스트로 복원.
6.  **Prosody:** 기존 부호를 보존하며 경계 기반의 쉼표 삽입 등 운율 처리 수행.

## 3. 실행 엔트리포인트 (Entrypoints)

*   **Source Pipeline:** `engine.main.transform` (개발 및 검증용)
*   **Binary Runtime:** `bin/build_binary_entrypoint.py` (배포용 바이너리 핵심 로직)
*   **API / Wrapper:** 바이너리를 직접 호출하여 동작 (`api/server.py`, `bin/run_preprocessor.py`)

## 4. 주요 구현 규칙

*   **후처리 제약:** 한글이 포함된 평문 세그먼트는 후처리 헬퍼 적용 대상에서 제외한다 (`skip_hangul` 옵션).
*   **조사 처리:** 입력된 조사를 보존하는 것을 원칙으로 하며, 임의의 조사 교정은 금지한다.
*   **Prosody 제약:** 기존 문장부호를 삭제하거나 이동하지 않고, 삽입 동작만 허용한다.

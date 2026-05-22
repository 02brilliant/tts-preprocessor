# Runtime & Deployment

본 문서는 소스 코드 빌드, 패키징 및 서비스 실행 구조를 정의한다.

## 1. 운영 원칙

*   **바이너리 우선 실행:** 서비스 환경(API, CLI 등)에서는 소스 코드를 직접 참조하지 않고, 빌드된 바이너리(`tts_preprocessor`)를 실행한다.
*   **환경 격리:** 빌드 시 소스 코드(`.py`)와 내부 문서(`docs/`, `tests/`)가 패키지에 포함되지 않도록 차단한다.

## 2. 실행 경로 (Entrypoints)

*   **개발 환경:** `engine.main.transform` (소스 기반 직접 실행)
*   **로컬 바이너리:** `dist/tts_preprocessor` (빌드 직후 결과물)
*   **패키지 바이너리:** `packages/tts-preprocessor/bin/tts_preprocessor` (최종 릴리스 형태)
*   **서비스 계층:** `api/server.py`, `bin/run_preprocessor.py` (환경변수 또는 최신 패키지 바이너리 탐색 후 호출)

## 3. 빌드 및 릴리스 절차

1.  **바이너리 빌드:** `bash scripts/build_binary.sh` 실행 -> `dist/` 생성.
2.  **릴리스 프로세스:** `python scripts/release.py` 실행.
    *   소스 테스트 -> 바이너리 빌드 -> 바이너리 동작 테스트 -> 패키징 순으로 진행.
3.  **패키징 결과물:** `packages/tts-preprocessor/` 및 `downloads/tts-preprocessor.zip` 생성.

## 4. 서비스 배포 구조

서버 배포 시 다음의 구조를 유지하며 소스 트리는 제외한다.

  ```text
  app/
    api/          # 서비스 인터페이스 (바이너리 호출용)
    web/          # 웹 인터페이스 자산
    packages/     # 고정 바이너리 패키지
    downloads/    # 배포용 압축 파일
  ```

## 5. 서버 운영 명령

*   **서버 시작:** `bash scripts/start_server.sh` (최신 패키지 바이너리 자동 선택)
*   **서버 중지:** `bash scripts/stop_server.sh`
*   **상태 확인:** `bash scripts/check_server.sh`

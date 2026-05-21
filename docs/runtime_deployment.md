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

로컬 릴리스 패키지는 로컬 검증과 수동 패키징이 필요할 때 생성한다.

1.  **바이너리 빌드:** `bash scripts/build_binary.sh` 실행 -> `dist/` 생성.
2.  **릴리스 프로세스:** `python scripts/release.py` 실행.
    *   소스 테스트 -> 바이너리 빌드 -> 바이너리 런타임 테스트 -> 패키징 -> packaged binary semantic probe 순으로 진행.
3.  **패키징 결과물:** `packages/tts-preprocessor/` 및 `downloads/tts-preprocessor.zip` 생성.

서버 배포는 `bash scripts/deploy_server.sh`를 기준으로 한다. 이 스크립트는
원격 임시 `buildsrc`에 필요한 소스와 semantic probe runner를 동기화하고,
원격에서 PyInstaller 바이너리와 패키지를 만든 뒤 서버를 재시작한다.
원격 패키지 빌드 단계의 semantic 검증은 반드시 binary-only runner로
수행하며, 원격 Python에서 source 또는 `production_source` runner를 실행하지
않는다.

semantic probe의 canonical 진입점은 다음 파일이다.

```text
scripts/probes/run_semantic_probes.py
```

릴리스/배포/원격 패키지 빌드 스크립트는 이 runner를 호출하고 exit code만
판단한다. feature expected normalized text는 `scripts/probes/` probe 파일
내부에만 둔다. 개별 probe 직접 실행은 개발과 디버그 용도로 유지한다.
deployment/release script는 기본 `core` suite만 사용하며, 12개 그룹 기반
scenario regression probe는 배포 필수 smoke가 아닌 수동/확장 semantic
검증이다.

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
*   **배포:** `bash scripts/deploy_server.sh`
*   **상태 확인:** `bash scripts/check_server.sh`

`check_server.sh`는 health/sanity check이다. 기능 semantic regression 검증은
배포 후 다음 통합 probe runner를 API 대상으로 실행한다.

```text
python3 scripts/probes/run_semantic_probes.py --suite core --runtime api --api http://10.20.10.162:8010
```

12개 그룹 기반 scenario regression probe는 수동/확장 검증으로 실행한다.

```text
python3 scripts/probes/scenario_regression.py
python3 scripts/probes/run_semantic_probes.py --suite scenario
python3 scripts/probes/run_semantic_probes.py --suite all
python3 scripts/probes/run_semantic_probes.py --suite scenario --runtime api --api http://10.20.10.162:8010
```

개별 probe 직접 실행은 개발/디버그용으로 다음 명령을 사용한다.

```text
python3 scripts/probes/run_semantic_probes.py --suite core
python3 scripts/probes/decimal_fractional_zero.py
python3 scripts/probes/colon_time_like_policy.py
python3 scripts/probes/large_unit_numeric_surface.py
python3 scripts/probes/json_like_protected_spans.py
```

기존 top-level probe 명령과 helper 파일은 삭제되었으며 더 이상 canonical
경로가 아니다.

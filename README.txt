# TTS Preprocessor 운영 메모

## 실행 원칙

- `engine/` 소스는 개발과 테스트용이다.
- 제품 변환은 PyInstaller 실행 파일을 통해 수행한다.
- 1단계 공식 entrypoint는 `bin/build_binary_entrypoint.py`다.
- 2단계 LLM 공식 entrypoint는 `bin/build_llm_stage_entrypoint.py`이며,
  1단계 엔진에 의존하지 않고 `normalized_text`만 입력으로 받는다.
- 웹서버/API는 `TTS_PREPROCESSOR_BINARY`로 지정한
  `packages/tts-preprocessor/tts-preprocessor`를 호출한다.
- `check_server.sh`는 health/sanity check이며 semantic regression 대체물이 아니다.
- canonical semantic probe entrypoint는 `scripts/probes/run_semantic_probes.py`다.

## 운영체제별 빌드 책임

| 대상 | 빌드 위치 | 최종 ZIP |
|---|---|---|
| Linux 운영 | Ubuntu 22.04 운영 서버의 기존 `buildenv` | `tts-preprocessor-linux.zip` |
| macOS Apple Silicon | M1 Mac 로컬 `.venv` | `tts-preprocessor-macos.zip` |
| Windows | GitHub Actions `windows-latest` | `tts-preprocessor-windows.zip` |

Linux 운영 바이너리는 macOS나 GitHub Actions에서 빌드하지 않는다. 통합
배포는 원격 Linux prepare와 로컬 macOS 빌드를 병렬 실행하고 둘 다 성공한
뒤에만 서버를 중지하고 Linux package/ZIP을 publish한다. 이후 정확한 기존
macOS·Windows ZIP을 삭제하고 새 macOS ZIP을 검증·반영한 다음 서버를
시작한다.


## Linux 운영 배포

```sh
cd ~/tts-preprocessor
source .venv/bin/activate
PYTHONPATH=. .venv/bin/python -m pytest -m "not binary_runtime" -q

bash scripts/deploy_server.sh
bash scripts/check_server.sh

.venv/bin/python scripts/probes/run_semantic_probes.py \
  --suite core \
  --runtime api \
  --api http://10.20.10.162:8010
```

운영 서버는 Ubuntu 22.04.5 / glibc 2.35 환경을 유지한다. API 서버는
`~/tts-preprocessor/.venv`, Linux 바이너리 빌드는
`~/tts-preprocessor/buildenv`를 사용하며 둘 다 일반 GIL Python 3.13
환경이어야 한다. 배포 스크립트는 이 환경을 생성하거나 패키지를
설치·업그레이드하지 않고, source sync 전에 두 Python 런타임을 검증한다.
PyInstaller 호환성은 dist, staging package, published package의 core
semantic probe로 판정한다.

`deploy_server.sh`는 source sync 후 Linux prepare와 같은 worktree의 macOS
arm64 빌드를 동시에 시작한다. 두 빌드가 성공해야 Linux publish, desktop ZIP
무효화, 새 macOS ZIP 업로드, 서버 시작과 health 검증을 수행한다. 서버는
publish 전에 중지한다. publish 이후 실패에는 자동 rollback을 하지 않으며
서버를 시작하지 않고 전체 배포 재실행을 안내한다. Windows ZIP은 빌드하거나
업로드하지 않는다.

## macOS Apple Silicon 패키지

```sh
bash scripts/build_macos_package.sh
```

산출물:

- `build/macos/dist/tts-preprocessor`
- `build/macos/dist/tts-llm-stage`
- `downloads/tts-preprocessor-macos.zip`

ZIP 루트에는 `tts-preprocessor`, `tts-llm-stage`, `README.txt`만 포함된다. 현재 빌드는
Apple Silicon arm64 전용이며 Intel x86_64 및 Universal Binary는 지원
범위가 아니다. 코드 서명·공증이 없으므로 Gatekeeper 경고가 발생할 수 있다.
통합 배포에서는 이 스크립트를 직접 실행할 필요 없이 `deploy_server.sh`가
항상 새로 실행한다.

## Windows 패키지

코드 리뷰 → commit → push 후 GitHub 저장소 → Actions →
Build Windows executable → Run workflow

산출 artifact:

```text
tts-preprocessor-windows → tts-preprocessor-windows.zip
```

다운로드한 ZIP을 로컬 `downloads/`에 배치한다. Windows workflow는
CPython 3.13.14와 현재 검증된 `PyInstaller==6.21.0`을 사용한다.

## 데스크톱 ZIP 업로드

Windows ZIP 계약만 확인:

```sh
bash scripts/upload_desktop_packages.sh --platform windows --validate-only
```

Windows ZIP만 업로드:

```sh
bash scripts/upload_desktop_packages.sh --platform windows
```

업로드 스크립트는 Windows 전용이며 명시적 `--platform windows`를 요구한다.1
macOS/Linux ZIP, 서버 패키지, 서버 프로세스는 변경하지 않는다. SSH 인증은
기존 SSH 설정과 agent를 사용하며 개인키나 인증정보를 스크립트에 저장하지
않는다.

## 로컬 Linux 검증 릴리스

`release.py`와 `build_binary.sh`는 Linux 로컬 검증 전용이다. macOS에서는
실행하지 않는다.

```sh
.venv/bin/python scripts/release.py
```

결과:

```text
downloads/tts-preprocessor-linux.zip
```

이 결과는 운영 서버 호환성을 보장하지 않는다. 운영 Linux 바이너리는 반드시
Ubuntu 22.04 운영 서버의 기존 `buildenv`에서 생성한다.

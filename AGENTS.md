# 프로젝트 작업 지침

## 작업 범위

- 작업 디렉터리는 이 `AGENTS.md`가 위치한 저장소 루트로 한다.
- 작업을 시작하기 전에 현재 디렉터리와 Git 상태를 확인한다.

```sh
pwd
git status --short
git branch --show-current
```

- 사용자가 명시적으로 요청하지 않는 한 저장소 외부의 파일은 수정하지 않는다.
- 기존의 미커밋 변경사항이 있으면 임의로 삭제하거나 덮어쓰지 않는다.

## Python 환경

- 로컬 개발과 테스트에는 저장소의 `.venv` 가상환경을 사용한다.
- Python 명령은 가상환경 활성화 여부에 의존하지 말고 다음 인터프리터를 직접 사용한다.

```sh
.venv/bin/python
```

- 로컬 개발 작업에서 시스템 `python` 또는 `python3`를 프로젝트 인터프리터 대신 사용하지 않는다.
- `.venv`가 없거나 필요한 패키지가 설치되어 있지 않으면 임의로 다른 Python을 사용하지 말고 현재 환경 상태를 보고한다.
- macOS에서는 프로젝트 가상환경의 Python 아키텍처가 `arm64`인지 확인한다.

```sh
.venv/bin/python --version
.venv/bin/python -c "import platform, sys; print(platform.machine()); print(sys.executable)"
```

## 테스트

- 일반 소스 변경 후 기본 검증 명령은 다음과 같다.

```sh
PYTHONPATH=. .venv/bin/python -m pytest -m "not binary_runtime" -q
```

- Linux/macOS 통합 배포는 `scripts/deploy_with_gates.sh`를 사용한다. packaged path가
  dirty이면 배포 전 자동 commit한 뒤 `deploy_server.sh` 내부의 source pytest와
  semantic probe 게이트를 실행한다.

- 변경 범위가 작더라도 관련 테스트를 먼저 실행하고, 완료 전에는 가능한 경우 기본 소스 테스트 전체를 실행한다.
- 테스트 실패를 숨기거나 무시하지 않는다.
- 실패가 기존 문제로 판단되더라도 실패한 테스트 이름과 근거를 보고한다.

## 빌드 및 배포

- macOS에서는 Linux 운영 배포용 PyInstaller 바이너리를 빌드하지 않는다.
- macOS에서 생성한 바이너리를 Linux 운영 서버에 배포하지 않는다.
- Linux 운영 바이너리는 배포 정책에 정의된 호환 Ubuntu 서버 환경에서만 빌드한다.
- `scripts/release.py` 또는 `scripts/build_binary.sh`를 macOS에서 운영 릴리스 목적으로 실행하지 않는다.
- API 및 운영 런타임이 소스 모듈을 직접 사용하는 방식으로 배포 구조를 변경하지 않는다.
- 배포 관련 변경은 source-free production runtime 정책을 보존해야 한다.

## 변경 작업

- 파일을 수정하기 전에 반드시 작업 트리 상태를 확인한다.

```sh
git status --short
```

- 사용자가 요청한 범위만 수정한다.
- 관련 없는 파일의 포맷이나 내용을 임의로 변경하지 않는다.
- 기존 사용자 변경사항을 되돌리지 않는다.
- 새 의존성을 추가할 때는 필요성과 영향을 설명하고 사용자 승인 없이 전역 환경에 설치하지 않는다.
- 비밀정보, SSH 개인키, 인증 토큰, `.env` 내용은 출력하거나 Git에 추가하지 않는다.

## 완료 보고

작업 완료 후 다음을 확인하고 보고한다.

```sh
git status --short
git diff --stat
git diff
```

보고에는 다음 내용을 포함한다.

- 수정한 파일과 주요 변경 내용
- 실행한 테스트 또는 검증 명령
- 테스트 결과
- 실행하지 못한 검증과 그 이유
- 남아 있는 위험이나 후속 작업

사용자가 명시적으로 요청하지 않는 한 자동으로 커밋하거나 push하지 않는다.

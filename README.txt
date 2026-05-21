# TTS Preprocessor

## 실행 원칙

- `engine/` 소스는 개발과 테스트용이다.

- 제품 실행은 Python 소스(`engine/`)를 직접 import하지 않고, PyInstaller로 빌드된 실행파일을 통해서만 수행한다.
- 빌드 직후 실행파일은 `dist/tts_preprocessor`에 생성되고, 릴리스 패키지용 실행파일은 `packages/tts-preprocessor/bin/tts_preprocessor`에 복사된다.
- 웹서버/API는 최종적으로 패키지 내부 실행파일(`packages/tts-preprocessor/bin/tts_preprocessor`)을 호출한다.

- 소스를 수정한 뒤에는 실행모듈을 반드시 다시 빌드해야 한다.
- 로컬 릴리스 패키지 생성은 로컬 검증/수동 패키징용이다.
- 서버 배포는 `bash scripts/deploy_server.sh`가 원격 임시 buildsrc에서 바이너리와 패키지를 생성한 뒤 서버를 재시작하는 흐름을 기준으로 한다.
- semantic probe 실행 진입점은 `scripts/probes/run_semantic_probes.py`다.
- feature expected normalized text는 `scripts/probes/` probe 파일 내부에만 둔다.
- 릴리스/배포/원격 패키지 빌드 스크립트는 semantic probe runner를 호출하고 exit code만 판단한다.
- 원격 패키지 빌드 단계는 binary-only probe만 실행한다.
- `check_server.sh`는 health/sanity check이며, 기능 semantic regression 대체물이 아니다.
- 기본 release/deploy 경로는 `core` suite만 사용하고, 12개 그룹 scenario probe는 수동/확장 regression 검증이다.
- 개별 `scripts/probes/*.py` 직접 실행은 개발/디버그용으로 유지한다.
- 기존 top-level probe 명령과 helper 파일은 삭제되었으며 더 이상 canonical 경로가 아니다.


로컬 릴리스 패키지 생성 흐름:

1. `bash scripts/build_binary.sh`
   - `dist/tts_preprocessor` 생성

2. `python scripts/release.py`
   - `packages/tts-preprocessor/bin/tts_preprocessor` 생성
   - `downloads/tts-preprocessor.zip` 생성


## 개발 테스트

cd ~/tts-preprocessor
source .venv/bin/activate
PYTHONPATH=. ./.venv/bin/pytest -q -s tests # 전체 테스트


## 로컬 릴리스 패키지 생성

cd ~/tts-preprocessor
source .venv/bin/activate
bash scripts/build_binary.sh
python scripts/release.py
bash scripts/start_server.sh # 로컬 서버 시작 [http://localhost:8010/web/]
bash scripts/stop_server.sh # 로컬 서버 종료



## 서버 배포 [http://10.20.10.162:8010/web/]
cd ~/tts-preprocessor
source .venv/bin/activate
bash scripts/deploy_server.sh # 원격 buildsrc에서 패키지 생성 후 배포
bash scripts/check_server.sh # health/sanity 검증
python3 scripts/probes/run_semantic_probes.py --suite core --runtime api --api http://10.20.10.162:8010
python3 scripts/probes/run_semantic_probes.py --suite scenario --runtime api --api http://10.20.10.162:8010


## semantic probe
cd ~/tts-preprocessor
source .venv/bin/activate
python3 scripts/probes/run_semantic_probes.py --suite core
python3 scripts/probes/scenario_regression.py
python3 scripts/probes/run_semantic_probes.py --suite scenario
python3 scripts/probes/run_semantic_probes.py --suite all


## 개별 probe 개발/디버그
cd ~/tts-preprocessor
source .venv/bin/activate
python3 scripts/probes/run_semantic_probes.py --suite core
python3 scripts/probes/decimal_fractional_zero.py
python3 scripts/probes/colon_time_like_policy.py
python3 scripts/probes/large_unit_numeric_surface.py
python3 scripts/probes/json_like_protected_spans.py

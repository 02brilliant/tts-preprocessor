# TTS Preprocessor

## 실행 원칙

- `engine/` 소스는 개발과 테스트용이다.

- 제품 실행은 Python 소스(`engine/`)를 직접 import하지 않고, PyInstaller로 빌드된 실행파일을 통해서만 수행한다.
- 빌드 직후 실행파일은 `dist/tts_preprocessor`에 생성되고, 릴리스 패키지용 실행파일은 `packages/tts-preprocessor/bin/tts_preprocessor`에 복사된다.
- 웹서버/API는 최종적으로 패키지 내부 실행파일(`packages/tts-preprocessor/bin/tts_preprocessor`)을 호출한다.

- 소스를 수정한 뒤에는 실행모듈을 반드시 다시 빌드해야 한다.
- 배포 전에는 반드시 `bash scripts/build_binary.sh` → `python scripts/release.py` 순서로 실행한다.


소스 수정 후 실행 흐름:

1. `bash scripts/build_binary.sh`
   - `dist/tts_preprocessor` 생성

2. `python scripts/release.py`
   - `packages/tts-preprocessor/bin/tts_preprocessor` 생성
   - `downloads/tts-preprocessor.zip` 생성

3. `bash scripts/deploy_server.sh`
   - 원격 서버의 `app/packages/tts-preprocessor/bin/tts_preprocessor` 갱신
   - 웹/API 서버 재시작
   

## 개발 테스트

cd ~/tts-preprocessor
source .venv/bin/activate
PYTHONPATH=. ./.venv/bin/pytest -q -s tests # 전체 테스트


## 로컬 릴리스 패키지 생성

cd ~/tts-preprocessor
source .venv/bin/activate
bash scripts/build_binary.sh
python scripts/release.py
bash scripts/start_server.sh # 로컬 서버 시작

bash scripts/stop_server.sh # 로컬 서버 종료

- 로컬 웹페이지: [http://localhost:8010/web/]


## 서버 배포
cd ~/tts-preprocessor
source .venv/bin/activate
bash scripts/build_binary.sh
python scripts/release.py # 고정 배포 산출물 생성
bash scripts/deploy_server.sh # 배포 실행
bash scripts/check_server.sh # 배포 결과 검증

- 서버 웹페이지: [http://10.20.10.162:8010/web/]

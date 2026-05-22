# TTS Preprocessor 운영 메모

## 실행 원칙

- `engine/` 소스는 개발과 테스트용이다.
- 제품 실행은 Python 소스(`engine/`)를 직접 import하지 않고, PyInstaller로 빌드된 실행파일을 통해 수행한다.
- PyInstaller entrypoint는 `bin/build_binary_entrypoint.py`다.
- 빌드 직후 Linux 실행파일은 `dist/tts_preprocessor`에 생성된다.
- 릴리스 패키지용 Linux 실행파일은 `packages/tts-preprocessor/bin/tts_preprocessor`에 복사된다.
- 웹서버/API는 최종적으로 패키지 내부 실행파일을 호출한다.
- 소스를 수정한 뒤에는 실행모듈을 반드시 다시 빌드해야 한다.
- `check_server.sh`는 health/sanity check이며, semantic regression 대체물이 아니다.
- semantic probe canonical entrypoint는 `scripts/probes/run_semantic_probes.py`다.
- 기본 release/deploy 검증은 `core` suite 기준이고, `scenario` suite는 수동/확장 regression 검증이다.
- production `span_default`는 span 변환·comma adapter·bracket filter 후 `split_paragraphs()`로 긴 문단을 보수적으로 나눈다. 기존 줄바꿈은 문단 경계 정책에 따라 `\n\n`으로 정규화될 수 있다.

## Linux 운영 배포 원칙

Linux 운영 바이너리는 기존 서버 배포 프로세스를 유지한다.

- 운영 서버: Ubuntu 22.04.5 / glibc 2.35 / Python 3.10.12 / `buildenv`
- 로컬 WSL: Ubuntu 24.04.3 / glibc 2.39 / Python 3.12.3

WSL에서 만든 Linux 바이너리는 운영 서버 glibc와 맞지 않을 수 있으므로 운영 배포용으로 사용하지 않는다.





## ===== 서버 (Linux 운영) 배포 [http://10.20.10.162:8010/web/]

cd ~/tts-preprocessor
source .venv/bin/activate

bash scripts/deploy_server.sh   # 원격 buildsrc에서 패키지 생성 후 배포
bash scripts/check_server.sh    # health/sanity 검증

python3 scripts/probes/run_semantic_probes.py --suite core --runtime api --api http://10.20.10.162:8010
python3 scripts/probes/run_semantic_probes.py --suite scenario --runtime api --api http://10.20.10.162:8010





## ===== Windows / Mac OS용 실행모듈 빌드
# GitHub commit & push 완료 후, GitHub 웹페이지에서 실행

GitHub 저장소
→ Actions
→ Build desktop executables
→ Run workflow
→ Run workflow 클릭

생성되는 artifact:
tts-preprocessor-windows → tts-preprocessor-windows.zip
tts-preprocessor-macos   → tts-preprocessor-macos.zip

downloads 폴더에 복사 후, 서버 복사 실행
cd ~/tts-preprocessor
scp downloads/tts-preprocessor-windows.zip \
    downloads/tts-preprocessor-macos.zip \
    brilliant@10.20.10.162:~/tts-preprocessor/app/downloads/
ssh brilliant@10.20.10.162 'ls -lh ~/tts-preprocessor/app/downloads/'   # 서버 확인





## ===== 로컬 릴리스 패키지 생성

cd ~/tts-preprocessor
source .venv/bin/activate

PYTHONPATH=. ./.venv/bin/pytest -q -s tests ## 로컬 개발 테스트

bash scripts/build_binary.sh
python scripts/release.py

bash scripts/start_server.sh    # 로컬 서버 시작 [http://localhost:8010/web/]
bash scripts/stop_server.sh     # 로컬 서버 종료

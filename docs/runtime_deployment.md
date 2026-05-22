# Runtime, Architecture & Deployment

## 1. 문서 목적과 범위

이 문서는 TTS Preprocessor의 **런타임 실행 경로**, **아키텍처 개요**, **Linux 운영 빌드/릴리스/배포**, **Windows·macOS 보조 빌드**, **웹 다운로드**, **배포 후 검증**을 한곳에 정리한다.

- 숫자·기호·단위 등 **변환 정책의 세부 규칙**은 `docs/policies/` 아래 policy 문서가 기준이다.
- 파이프라인 단계 개요만 필요하면 `docs/pipeline_architecture.md`를 참고한다.
- Windows·macOS GHA 빌드 절차만 빠르게 볼 때는 `docs/build_desktop_executables.md`를 참고할 수 있다.

## 2. 핵심 아키텍처 원칙

제품 런타임은 **한글 원문 불변**을 전제로, 숫자·기호 등만 구조적으로 읽는다.

| 원칙 | 요약 |
|------|------|
| 한글 불변성 | 입력 한글·공백·문장부호는 변환 대상이 아닌 보존 대상이다. |
| Typed surface | 변환이 필요한 구간만 구조적 읽기 단위로 다룬다. |
| Owner / claim / gate | span 엔진에서 표면 소유·청구·게이트로 충돌을 막고, owner가 처리하지 못한 구간은 preserve 또는 full-claim 규칙을 따른다. (세부: policy 문서) |
| 표면 복원 | 분석 결과는 최종 단계에서만 읽기 텍스트로 렌더링한다. |
| Prosody insert-only | 쉼표·문단 구분은 **삽입만** 허용하며, 기존 부호 삭제·이동은 하지 않는다. |
| Paragraph shaping | `span_default` 최종 출력은 `engine.prosody.paragraph.split_paragraphs`로 긴 문단을 보수적으로 나눈다. 기존 `\n`은 문단 경계 정책(`\n+` → `\n\n`)에 따라 정규화될 수 있다. 쉼표 prosody(comma adapter) 이후·bracket filter 이후 문자열 단계에서만 적용한다. |

파이프라인 단계(early preprocess → dictionary → rules → typed surface → restoration → prosody comma → paragraph split)는 `docs/pipeline_architecture.md`를 본다.

## 3. 실행 경로와 entrypoint

| 역할 | 경로 / 모듈 | 비고 |
|------|-------------|------|
| Source transform (개발·테스트) | `engine.main.transform`, `engine.main.transform_with_rollout` | `span_default`가 소스 기준 production rollout |
| PyInstaller 빌드 소스 entry | `bin/build_binary_entrypoint.py` | Linux `build_binary.sh`, 원격 `build_remote_package.sh`, GHA desktop workflow **동일** |
| 로컬 dist 바이너리 | `dist/tts_preprocessor` | `scripts/build_binary.sh` 산출물 (이름: underscore) |
| 패키지 바이너리 | `packages/tts-preprocessor/bin/tts_preprocessor` | API·`start_server.sh` 기본 런타임 |
| API 서버 | `api/server.py` (`python -m api.server`) | `/api/transform`는 패키지 바이너리 subprocess 호출 |
| CLI 래퍼 | `bin/run_preprocessor.py` | `api.binary_runtime.run_transform_binary` 경유 |
| 바이너리 탐색 순서 | `TTS_PREPROCESSOR_BINARY` → `dist/tts_preprocessor` → `packages/.../tts_preprocessor` | `api/binary_runtime.py` |
| Desktop 바이너리 (GHA) | `tts-preprocessor.exe` / `tts-preprocessor` | Linux 운영 패키지와 **파일명·빌드 경로 분리** |

`bin/build_binary_entrypoint.py`는 기본 `--rollout-mode span_default`로 `engine.main.transform_with_rollout`을 호출한다. 이 경로는 span 엔진 변환·comma adapter·bracket filter 후 `split_paragraphs()`로 문단을 나눈다. API production 경로는 소스 import 없이 패키지 바이너리만 실행한다 (`api/server.py` 주석).

## 4. Linux 운영 빌드·릴리스·배포

### 4.1 환경 구분

| 환경 | OS / libc / Python | Linux 운영 바이너리 빌드 |
|------|-------------------|-------------------------|
| 운영 서버 | Ubuntu 22.04.5, glibc 2.35, Python 3.10.12, `buildenv` | **여기서만** 운영용 빌드 |
| 로컬 WSL | Ubuntu 24.04.3, glibc 2.39, Python 3.12.3 | 운영 배포용 바이너리 **빌드하지 않음** (glibc 불일치 위험) |
| 로컬 개발 venv | `.venv` | `build_binary.sh` / `release.py` 로컬 검증용 |

GitHub Actions desktop workflow에 **Linux job을 넣지 않는** 이유도 동일하다. `ubuntu-latest` runner glibc도 운영 서버 2.35와 다를 수 있다.

### 4.2 PyInstaller (Linux·원격 공통)

`scripts/build_binary.sh` 및 원격 `scripts/build_remote_package.sh` 기준:

```bash
pyinstaller \
  --clean \
  --onefile \
  --name tts_preprocessor \
  --paths "$ROOT_DIR" \
  --collect-submodules engine \
  --add-data "$ROOT_DIR/engine/data:engine/data" \
  bin/build_binary_entrypoint.py
```

- 원격 빌드는 Python 3.10 `buildenv` + `enum.StrEnum` **runtime hook** 추가 (`build_remote_package.sh`).
- `build_binary.sh`는 빌드 후 dist 바이너리 **smoke** 1건 실행.

### 4.3 `scripts/release.py` (로컬 릴리스)

릴리스 패키지는 배포 대상 Linux와 호환되는 빌드 환경에서 실행한다. 운영 서버 배포 기준은 `buildenv`이며, 로컬 `.venv` 실행은 개발/검증용으로만 취급한다.

```bash
python scripts/release.py
```

1. `pytest -m "not binary_runtime"` — 소스 테스트
2. `bash scripts/build_binary.sh` — `dist/tts_preprocessor`
3. `pytest -m binary_runtime` — 바이너리 런타임 테스트
4. `python scripts/build_package.py` — 패키징
5. `scripts/probes/run_semantic_probes.py --runtime binary --binary packages/tts-preprocessor/bin/tts_preprocessor` — **core** suite (기본값)

**산출물**

- `packages/tts-preprocessor/README.txt`
- `packages/tts-preprocessor/bin/tts_preprocessor`
- `downloads/tts-preprocessor.zip` (zip 루트: `tts-preprocessor/` 디렉터리)

패키지에는 `.py` 소스, `engine/`, `docs/`, `tests/` 트리가 들어가면 실패한다 (`build_package.py` 검증).

### 4.4 `scripts/deploy_server.sh` (운영 배포)

로컬에서 rsync + 원격 빌드 + 재시작.

```bash
bash scripts/deploy_server.sh
```

**동기화 대상 (로컬 → 원격 `~/tts-preprocessor`)**

| 로컬 | 원격 |
|------|------|
| `api/` | `app/api/` |
| `web/` | `app/web/` |
| `scripts/` | `scripts/` |
| `bin/`, `engine/` | `buildsrc/bin/`, `buildsrc/engine/` |
| `scripts/probes/` | `buildsrc/scripts/probes/` |
| `docs/Release_Package_README.txt` | `buildsrc/docs/Release_Package_README.txt` |

원격에서 `scripts/build_remote_package.sh` 실행 후 `app/packages/`, `app/downloads/tts-preprocessor.zip` 생성. `buildsrc/`는 빌드 후 삭제된다.

**원격 app 구조 (배포 후)**

```text
~/tts-preprocessor/
  app/
    api/
    web/
    packages/tts-preprocessor/bin/tts_preprocessor
    downloads/tts-preprocessor.zip
  scripts/
  buildenv/
  logs/
  run/
```

원격 패키지 빌드는 dist·packaged 바이너리 각각에 **binary-only** semantic probe (`--runtime binary`)를 실행한다. source / `production_source` runner는 사용하지 않는다.

배포 시 `app/downloads/` 기존 항목은 `build_remote_package.sh`가 비운 뒤 Linux zip만 다시 만든다. Windows·macOS zip은 **수동 재업로드**가 필요할 수 있다.

### 4.5 `scripts/check_server.sh`

```bash
bash scripts/check_server.sh
```

**health / sanity check** (기본 대상: `10.20.10.162:8010`):

- `GET /web/`
- `GET /downloads/tts-preprocessor.zip`
- `GET /docs` (FastAPI OpenAPI UI)
- `POST /api/transform` — 고정 payload 1건과 기대 `normalized_text` 문자열 포함 여부

semantic regression **대체가 아니다**. Windows·macOS zip 존재는 확인하지 않는다.

## 5. Windows·macOS 실행모듈 보조 빌드

파일: [`.github/workflows/build-desktop-executables.yml`](../.github/workflows/build-desktop-executables.yml)

| 항목 | 내용 |
|------|------|
| 트리거 | `workflow_dispatch` **수동 전용** (push/tag 없음) |
| Runner | `windows-latest`, `macos-latest` only |
| Python | 3.10 |
| Entrypoint | `bin/build_binary_entrypoint.py` (Linux와 동일) |
| 바이너리 이름 | `tts-preprocessor` / `tts-preprocessor.exe` (hyphen, underscore 아님) |
| `--add-data` | `engine/data` — Windows `;`, macOS `:` |
| 기타 | `StrEnum` runtime hook, `engine` submodule 수집 |

**GitHub에서 실행**

1. 저장소 → **Actions** → **Build desktop executables**
2. **Run workflow**

**Artifacts**

| OS | Artifact 이름 | zip (업로드용) |
|----|---------------|----------------|
| Windows | `tts-preprocessor-windows` | `tts-preprocessor-windows.zip` |
| macOS | `tts-preprocessor-macos` | `tts-preprocessor-macos.zip` |

각 desktop zip 루트에는 실행 파일과 `README.txt`(`docs/Release_Package_README.txt` 복사본)가 함께 들어간다. Artifact 업로드물은 zip 파일 하나뿐이다. macOS **code signing / notarization은 포함되지 않는다** (Gatekeeper 경고 가능).

## 6. 웹서비스 다운로드 구조

`api/server.py` 정적 mount:

- `/web` → `web/`
- `/downloads` → `downloads/`
- `/` → `/web/` 리다이렉트

`web/index.html`은 세 OS 항목을 **항상 표시**하고, 각 zip을 `HEAD`로 **독립 확인**한다.

| OS | 파일명 | URL |
|----|--------|-----|
| Linux | `tts-preprocessor.zip` | `/downloads/tts-preprocessor.zip` |
| Windows | `tts-preprocessor-windows.zip` | `/downloads/tts-preprocessor-windows.zip` |
| macOS | `tts-preprocessor-macos.zip` | `/downloads/tts-preprocessor-macos.zip` |

- Linux zip: `release.py` / 원격 `build_remote_package.sh` 흐름에서 생성
- Windows·macOS zip: GHA artifact를 `app/downloads/`(또는 로컬 `downloads/`)에 **수동 업로드**
- 파일이 없으면 해당 행만 **준비 중**, 다른 OS 링크는 그대로 표시

## 7. 배포 후 검증

### 7.1 Health / sanity

```bash
bash scripts/check_server.sh
```

### 7.2 Semantic regression (별도 실행)

Canonical runner: `scripts/probes/run_semantic_probes.py`

| suite | probe 파일 |
|-------|------------|
| `core` (기본) | `decimal_fractional_zero.py`, `colon_time_like_policy.py`, `large_unit_numeric_surface.py`, `json_like_protected_spans.py` |
| `scenario` | `scenario_regression.py` |
| `all` | core + scenario |

**릴리스/원격 빌드**는 `--runtime binary` + `--binary <path>`만 사용하며, 기본 **core** suite다.

```bash
# 패키지 바이너리 (로컬)
python3 scripts/probes/run_semantic_probes.py \
  --runtime binary \
  --binary packages/tts-preprocessor/bin/tts_preprocessor

# API (배포 후, 호스트·포트는 환경에 맞게)
python3 scripts/probes/run_semantic_probes.py \
  --suite core \
  --runtime api \
  --api http://10.20.10.162:8010

# 확장 / 수동 (배포 필수 아님)
python3 scripts/probes/run_semantic_probes.py --suite scenario
python3 scripts/probes/run_semantic_probes.py --suite all
python3 scripts/probes/scenario_regression.py
```

개별 `scripts/probes/*.py` 직접 실행은 개발·디버그용이다.

## 8. 서버 운영 명령

원격·로컬 공통 스크립트 (`scripts/`). 서버는 기본 포트 **8010**, 바이너리는 `TTS_PREPROCESSOR_BINARY` 또는 `packages/tts-preprocessor/bin/tts_preprocessor`.

```bash
# 시작 (app/ 또는 repo root에서 api·web·packages 존재 시 동작)
bash scripts/start_server.sh

# 중지
bash scripts/stop_server.sh

# 배포 (rsync + 원격 빌드 + 재시작)
bash scripts/deploy_server.sh

# health / sanity
bash scripts/check_server.sh
```

로컬 릴리스만:

```bash
bash scripts/build_binary.sh
python scripts/release.py
```

## 9. 운영 금지·주의 사항

- Linux **운영** 바이너리를 WSL Ubuntu 24.04(glibc 2.39)에서 빌드해 서버에 올리지 않는다.
- desktop workflow에 **Linux job**을 추가하거나 push/tag에 연결하지 않는다.
- Windows·macOS artifact → `downloads/` 업로드는 **수동**이다.
- `check_server.sh`만으로 semantic 정상성을 판단하지 않는다.
- `deploy_server.sh` / 원격 `build_remote_package.sh`는 `app/downloads/`를 비운 뒤 Linux zip만 재생성한다. desktop zip은 재업로드가 필요할 수 있다.
- macOS 바이너리는 서명·공증 없이 배포되므로 Gatekeeper 경고가 날 수 있다.
- API·제품 실행 경로에서 `engine/` 소스를 직접 import하지 않는다. 소스 변경 후에는 바이너리를 반드시 재빌드한다.

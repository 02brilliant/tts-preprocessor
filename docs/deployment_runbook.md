# TTS Preprocessor Deployment Runbook

## 1. 기준과 운영 런타임

배포 정책의 authoritative 기준은
`docs/policies/TTS_Preprocessor_deployment_policy.md`다. 이 문서는 현재 단일
배포자·단일 Apple Silicon Mac·단일 Ubuntu 22.04 서버의 실제 운영 절차를
설명한다.

운영 API는 변환 소스를 import하지 않고 다음 PyInstaller 실행 파일을
`TTS_PREPROCESSOR_BINARY`로 실행한다.

```text
~/tts-preprocessor/app/packages/tts-preprocessor/tts-preprocessor
```

공식 빌드 entrypoint는 `bin/build_binary_entrypoint.py`이며
`engine.main.transform`을 호출한다. Linux, macOS, Windows는 공용
`tts_preprocessor.spec`과
`pyinstaller_runtime_hooks/enum_strenum_compat.py`를 사용한다. 최종 운영
`app/`에는 `engine/`, 변환 테스트, Python 변환 소스를 두지 않는다.

| 대상 | 빌드 위치 | 최종 ZIP |
|---|---|---|
| Linux 운영 | Ubuntu 22.04 운영 서버의 기존 `buildenv` | `tts-preprocessor-linux.zip` |
| macOS Apple Silicon | M1 Mac 로컬 `.venv` | `tts-preprocessor-macos.zip` |
| Windows | GitHub Actions `windows-latest` | `tts-preprocessor-windows.zip` |

Linux 운영 바이너리는 macOS 또는 GitHub Actions에서 만들지 않는다.

## 2. Linux + macOS 통합 배포

Mac 저장소 루트에서 실행한다.

```sh
bash scripts/deploy_server.sh
```

이 명령은 다음 순서로 동작한다.

1. Darwin arm64, `.venv` Python/PyInstaller, 로컬 명령과 필수 파일 검사
2. 서버의 기존 `buildenv`와 필수 원격 명령 검사
3. 새 원격 `buildsrc`에 entrypoint, `engine/`, spec, 공용 runtime hook,
   core semantic probes, release README와 다음 시작에 쓸 server control script 전송
4. 고유 deploy ID로 원격 Linux `prepare`와 로컬 macOS arm64 빌드를 병렬 시작
5. 두 PID를 모두 `wait`하고 각 종료 코드 확인
6. 두 작업 모두 성공한 경우에만 로컬 macOS ZIP 재검증
7. 서버 중지
8. 검증된 Linux staging package와 ZIP publish
9. staging된 `start_server.sh`, `stop_server.sh`를 운영 scripts에 설치
10. 기존 `tts-preprocessor-macos.zip`과
   `tts-preprocessor-windows.zip`만 정확히 삭제
11. 새 macOS ZIP을 숨김 임시 이름으로 전송
12. 원격 크기, ZIP 무결성, 정확한 두 파일을 확인한 뒤 최종 이름으로 `mv`
13. 운영 `app/`에 남은 `engine/`, `docs/` 제거
14. 서버 시작
15. Web, Linux ZIP, macOS ZIP, API docs, API transform sanity 검증
16. 해당 deploy ID의 staging과 임시 `buildsrc` 정리

Windows ZIP은 이 통합 배포에서 만들거나 업로드하지 않는다.

### 2.1 Linux prepare / publish / cleanup

`deploy_server.sh`가 같은 deploy ID를 세 명령에 전달한다.

```sh
bash scripts/build_remote_package.sh prepare <deploy-id>
bash scripts/build_remote_package.sh publish <deploy-id>
bash scripts/build_remote_package.sh cleanup <deploy-id>
```

`prepare`는 기존 Ubuntu `buildenv`만 사용한다. buildenv 생성, `pip install`,
`pip upgrade`, PyInstaller 변경은 하지 않는다. 다음 검증이 모두 성공하기
전에는 운영 package와 모든 다운로드 ZIP을 변경하지 않는다.

1. Linux dist PyInstaller 빌드
2. dist binary core semantic probe
3. deploy-ID별 staging package 생성
4. staging packaged binary core semantic probe
5. staging Linux ZIP 생성 및 구조 검증
6. ZIP SHA-256이 포함된 prepare marker 생성 및 재검증

Linux ZIP 내부는 다음 두 파일뿐이다.

```text
tts-preprocessor/README.txt
tts-preprocessor/tts-preprocessor
```

`publish`는 서버가 중지된 후에만 실행한다. marker의 deploy ID, staging 경로,
ZIP SHA-256과 ZIP 구조를 다시 확인한 뒤 운영 package와 Linux ZIP을 순서대로
교체하고 published binary core semantic probe를 실행한다.

publish 단계에는 backup 또는 자동 rollback이 없다. publish 실패 시 서버를
다시 시작하지 않으며 현재 운영 package와 Linux ZIP이 부분 반영됐을 수 있다.
오류를 확인한 뒤 통합 배포 명령 전체를 다시 실행한다.

`cleanup`은 해당 deploy ID의 staging package, staging ZIP, marker 및
`buildsrc`만 제거한다. 운영 package, 최종 Linux/macOS/Windows ZIP,
`buildenv`, 서버 로그는 제거하지 않는다. 여러 번 실행해도 안전하다.

### 2.2 중단과 실패 상태

병렬 빌드 중 `INT` 또는 `TERM`을 받으면 두 자식 프로세스를 종료하고
`wait`한다. publish, 서버 중지, desktop 삭제, 업로드, 서버 시작은 실행하지
않는다.

자동 rollback은 어떤 publish 이후 실패에도 수행하지 않는다.

| 실패 단계 | 서버 상태 | Linux 반영 | macOS/Windows ZIP | 자동 rollback | 사용자 조치 |
|---|---|---|---|---|---|
| 로컬/원격 preflight | 기존 서버 실행 유지 | 기존 artifact | 기존 상태 유지 | 없음 | 누락 조건 수정 후 전체 배포 재실행 |
| Linux prepare 또는 macOS build | 기존 서버 실행 유지 | 기존 artifact | 기존 상태 유지 | 없음 | 로그 확인 후 전체 배포 재실행 |
| server stop | 중지 여부를 확인해야 함 | 기존 artifact | 기존 상태 유지 | 없음 | 서버 상태 확인 후 전체 배포 재실행 |
| Linux publish | 서버 중지 상태 | package/ZIP 부분 반영 가능 | 기존 상태 유지 | 없음 | 오류 수정 후 전체 배포 재실행 |
| desktop ZIP 삭제 | 서버 중지 상태 | 새 Linux 반영 | 두 파일 중 일부 또는 전부 없을 수 있음 | 없음 | 전체 배포 재실행 |
| macOS SCP | 서버 중지 상태 | 새 Linux 반영 | macOS/Windows 없음 | 없음 | 전체 배포 재실행 |
| macOS 원격 검증/`mv` | 서버 중지 상태 | 새 Linux 반영 | macOS 없을 수 있고 Windows 없음 | 없음 | 전체 배포 재실행 |
| server start | 시작 실패 또는 불확정 | 새 Linux 반영 | 새 macOS 반영, Windows 없음 | 없음 | 로그 확인 후 전체 배포 재실행 |
| final check | 서버가 시작됐으나 검증 실패 | 새 Linux 반영 | 새 macOS 반영, Windows 없음 | 없음 | 서버 확인 후 필요 시 전체 배포 재실행 |
| cleanup | 검증된 서버 실행 유지 | 새 Linux 반영 | 새 macOS 반영, Windows 없음 | 없음 | 출력된 deploy ID cleanup 명령 재시도 |

Linux publish 이후 실패의 기본 복구 명령은 다음과 같다.

```sh
bash scripts/deploy_server.sh
```

cleanup만 실패했다면 출력된 deploy ID로 다음 명령을 실행한다.

```sh
ssh brilliant@10.20.10.162 \
  bash ~/tts-preprocessor/scripts/build_remote_package.sh cleanup <deploy-id>
```

## 3. macOS Apple Silicon package

통합 배포가 현재 작업 트리에서 매번 실행한다. 단독 로컬 빌드도 가능하다.

```sh
bash scripts/build_macos_package.sh
```

- Darwin arm64와 `.venv` Python arm64만 허용
- `.venv/bin/python`, `.venv/bin/pyinstaller`, 공용 spec/hook 사용
- 실행 파일: `build/macos/dist/tts-preprocessor`
- ZIP: `downloads/tts-preprocessor-macos.zip`
- ZIP 최상위: `tts-preprocessor`, `README.txt`
- 원본과 압축 해제 실행 파일 smoke test
- 임시 ZIP 검증 후 기존 ZIP 원자 교체

Intel x86_64와 Universal Binary는 범위 밖이다. 코드 서명·공증이 없으므로
Gatekeeper 경고가 발생할 수 있다.

## 4. Windows 별도 빌드와 업로드

1. 코드 리뷰
2. commit
3. push
4. GitHub 웹의 **Build Windows executable** workflow 수동 실행
5. `tts-preprocessor-windows.zip` artifact 다운로드
6. 다음 위치에 저장

   ```text
   downloads/tts-preprocessor-windows.zip
   ```

7. 로컬 검증

   ```sh
   bash scripts/upload_desktop_packages.sh \
     --platform windows \
     --validate-only
   ```

8. Windows ZIP만 서버에 업로드

   ```sh
   bash scripts/upload_desktop_packages.sh \
     --platform windows
   ```

Windows ZIP은 최상위에 `tts-preprocessor.exe`, `README.txt`만 포함한다.
업로드 스크립트는 Linux/macOS ZIP, 운영 package, 서버 프로세스를 변경하지
않는다.

통합 Linux/macOS 배포 직후 Windows ZIP이 없는 것은 정상이다. 같은 소스의
Windows workflow가 끝난 뒤 별도로 제공한다.

## 5. 서버 확인

```sh
bash scripts/check_server.sh
```

필수:

- `GET /web/`
- `GET /downloads/tts-preprocessor-linux.zip`
- `GET /downloads/tts-preprocessor-macos.zip`
- `GET /docs`
- `POST /api/transform`과 고정 sanity 응답

선택:

- `GET /downloads/tts-preprocessor-windows.zip`

Windows ZIP 부재는 실패가 아니다. `check_server.sh`는 health/sanity이며
canonical semantic regression 대신 사용하지 않는다.

API core semantic probe:

```sh
.venv/bin/python scripts/probes/run_semantic_probes.py \
  --suite core \
  --runtime api \
  --api http://10.20.10.162:8010
```

## 6. 다운로드 URL

| OS | URL |
|---|---|
| Linux | `/downloads/tts-preprocessor-linux.zip` |
| macOS | `/downloads/tts-preprocessor-macos.zip` |
| Windows | `/downloads/tts-preprocessor-windows.zip` |

웹은 세 파일을 독립적으로 확인한다. Windows는 수동 업로드 전까지 준비 중으로
표시될 수 있다.

Linux ZIP 이름 마이그레이션:

```text
이전: tts-preprocessor.zip
현재: tts-preprocessor-linux.zip
```

기존 이름은 자동 배포에서 삭제하지 않는다. 새 URL 확인 후 별도 승인된
일회성 작업으로 제거한다. 리다이렉트나 복제본은 제공하지 않는다.

## 7. 로컬 Linux 검증 도구

`scripts/release.py`와 `scripts/build_binary.sh`는 Linux 로컬 검증 전용이며
macOS 운영 배포에 사용하지 않는다. `scripts/build_package.py`는 준비된
바이너리만 packaging하며 바이너리를 직접 빌드하지 않는다.

로컬 Linux package 경로:

```text
packages/tts-preprocessor/tts-preprocessor
downloads/tts-preprocessor-linux.zip
```

운영 Linux 호환성 판단은 Ubuntu 22.04 서버의 기존 `buildenv`와 dist,
staging packaged, published packaged core semantic probe 결과를 기준으로 한다.

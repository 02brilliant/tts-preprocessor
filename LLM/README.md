# Local LLM API integration

LLM 기능은 별도 프록시 프로세스를 실행하지 않는다. 기존 `api.server`가 같은
포트에서 `/api/llm/models`와 `/api/llm/transform`을 제공한다.

## 파일 구성

- `docs/LLM_prompt.txt`: 요청마다 UTF-8로 다시 읽는 프롬프트 템플릿
- `docs/info_Local_LLM_server.txt`: 개발 참고용 서버 정보. 런타임은 이 파일에서
  인증정보를 읽지 않는다.
- `models.json`: 선택 가능한 모델 및 기본 모델

프롬프트 파일을 수정하면 다음 LLM 요청부터 반영되며 API 서버 재시작은 필요 없다.

## 환경변수

기존 API 서버 프로세스에 아래 값을 주입한다.

- `LOCAL_LLM_BASE_URL`: 로컬 LLM 애플리케이션 base URL
- `LOCAL_LLM_TOKEN`: 로컬 LLM bearer token
- `LOCAL_LLM_TIMEOUT_SECONDS`: upstream 제한시간(초), 기본값 `300`

토큰을 소스, 명령행 인자, Git 또는 브라우저에 넣지 않는다.

### 기존 배포 명령을 사용하는 운영 서버

`bash scripts/deploy_server.sh`는 서버의
`~/tts-preprocessor/config/llm.env`를 읽을 수 있는지 먼저 확인하고, `LLM/` 런타임
코드와 프롬프트 템플릿만 `app/LLM/`으로 배포한다. 개발 참고용
`LLM/docs/info_Local_LLM_server.txt`는 전송하지 않는다.

배포 전에 운영 서버에서 한 번만 다음처럼 환경 파일을 만든다. 값은 운영 환경의
실제 값으로 직접 입력하고, 파일 내용은 터미널 출력이나 Git에 넣지 않는다.

```sh
mkdir -p ~/tts-preprocessor/config
chmod 700 ~/tts-preprocessor/config
umask 077
editor ~/tts-preprocessor/config/llm.env
```

파일에는 `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_TOKEN` 및 필요하면
`LOCAL_LLM_TIMEOUT_SECONDS=300`을 `KEY=value` 형식으로 설정한다. 이후에는 기존과
같이 `bash scripts/deploy_server.sh`를 실행한다. 시작 스크립트가 이 파일을 읽어
기존 API 서버 프로세스에만 환경변수로 전달한다.

## 확인

기존 서버가 실행된 상태에서 다음을 확인한다.

```sh
curl http://127.0.0.1:8010/api/llm/models
curl http://127.0.0.1:8010/docs
```

LLM upstream 연결 실패는 `/api/llm/transform`에만 오류로 반환하며 기존
`/api/transform` 규칙 기반 전처리에는 영향을 주지 않는다.

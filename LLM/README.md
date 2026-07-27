# Local and Gemini LLM API integration

LLM 기능은 별도 프록시 프로세스를 실행하지 않는다. 기존 `api.server`가 같은
포트에서 `/api/llm/models`와 `/api/llm/transform`을 제공한다.

규칙 기반 엔진과 LLM은 다음 순서로만 연결한다.

1. `/api/transform`: 사용자 원고를 패키징된 규칙 엔진에 전달해
   `normalized_text` 생성
2. `/api/llm/transform`의 `prosody` 단계: `normalized_text`를
   `docs/LLM_prompt_prosody.txt`에 넣어 `prosody_text` 생성
3. `/api/llm/transform`의 `speech` 단계: 직전 `prosody_text`를
   `docs/LLM_prompt_speech.txt`에 넣어 `speech_text` 생성

두 LLM 단계는 같은 선택 모델로 직렬 실행한다. 앞 단계가 실패하면 다음 단계를
호출하지 않는다. 규칙 기반 `normalized_text` 계약과 source-free binary runtime은
이 통합으로 변경되지 않는다.

## 파일 구성

- `docs/LLM_prompt_prosody.txt`: `{{NORMALIZED_TEXT}}`를 정확히 한 번 포함하는
  2단계 프롬프트
- `docs/LLM_prompt_speech.txt`: `{{PROSODY_TEXT}}`를 정확히 한 번 포함하는
  3단계 프롬프트
- `models.json`: 선택 가능한 모델, 공급자 및 기본 모델
- `response_validation.py`: 단계별 LLM 출력 불변 조건 검증
- `docs/info_Local_LLM_server.txt`: 개발 참고용 서버 정보. 런타임은 이 파일에서
  인증정보를 읽지 않는다.

두 활성 프롬프트는 요청마다 UTF-8로 다시 읽는다. 파일을 수정하면 서버를
재시작하지 않아도 다음 해당 단계 요청부터 반영된다.

## API 계약

모델 목록:

```http
GET /api/llm/models
```

Prosody 요청:

```json
{
  "stage": "prosody",
  "normalized_text": "규칙 기반 결과",
  "model": "gemma4:e4b"
}
```

응답:

```json
{
  "prosody_text": "규칙 기반 결과, ",
  "model": "gemma4:e4b",
  "elapsed_ms": 123.456
}
```

Speech 요청:

```json
{
  "stage": "speech",
  "prosody_text": "국물은, 따뜻합니다.",
  "model": "gemma4:e4b"
}
```

응답:

```json
{
  "speech_text": "궁무른, 따뜨탐니다.",
  "model": "gemma4:e4b",
  "elapsed_ms": 123.456
}
```

`stage`가 없거나 단계와 입력 필드가 맞지 않는 요청은 거부한다. Prosody 응답은
입력 문자 보존과 쉼표·ASCII 공백만의 추가를 검증한다. Speech 응답은 공백,
줄바꿈, 쉼표, 고정 문장부호 및 잠금 토큰 보존을 검증한다. 계약을 위반한 모델
응답은 조용히 보정하지 않고 upstream 응답 오류로 반환한다.

## 환경변수

기존 API 서버 프로세스에 아래 값을 주입한다.

- `LOCAL_LLM_BASE_URL`: 로컬 LLM 애플리케이션 base URL
- `LOCAL_LLM_TOKEN`: 로컬 LLM bearer token
- `LOCAL_LLM_TIMEOUT_SECONDS`: upstream 제한시간(초), 기본값 `300`
- `GEMINI_API_KEY`: Gemini API 전용 키
- `GEMINI_TIMEOUT_SECONDS`: Gemini API 제한시간(초), 기본값 `300`

토큰과 API 키를 소스, 명령행 인자, Git 또는 브라우저에 넣지 않는다. Gemini
호출은 기존 API 서버가 `x-goog-api-key` 헤더를 사용해 서버 측에서만 수행한다.

### 기존 배포 명령을 사용하는 운영 서버

`bash scripts/deploy_server.sh`는 서버의
`~/tts-preprocessor/config/llm.env`를 읽을 수 있는지 먼저 확인하고, `LLM/` 런타임
코드와 두 활성 프롬프트만 `app/LLM/`으로 배포한다. 개발 참고용
`LLM/docs/info_Local_LLM_server.txt`는 전송하지 않는다.

배포 전에 운영 서버에서 한 번만 다음처럼 환경 파일을 만든다. 값은 운영 환경의
실제 값으로 직접 입력하고, 파일 내용은 터미널 출력이나 Git에 넣지 않는다.

```sh
mkdir -p ~/tts-preprocessor/config
chmod 700 ~/tts-preprocessor/config
umask 077
editor ~/tts-preprocessor/config/llm.env
```

파일에는 로컬 LLM용 `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_TOKEN` 또는 Gemini용
`GEMINI_API_KEY` 중 사용할 공급자의 설정을 `KEY=value` 형식으로 둔다. 필요하면
각 공급자의 timeout을 설정한다. 최소 한 공급자가 완전히 설정되어야 서버가
시작된다. 이후에는 기존과 같이 `bash scripts/deploy_server.sh`를 실행한다.
시작 스크립트가 이 파일을 읽어 기존 API 서버 프로세스에만 환경변수로 전달한다.

## 확인

기존 서버가 실행된 상태에서 다음을 확인한다.

```sh
curl http://127.0.0.1:8010/api/llm/models
curl http://127.0.0.1:8010/docs
```

선택 공급자의 연결 실패는 해당 LLM 단계에만 오류로 반환한다. 기존
`/api/transform` 규칙 기반 전처리와 다른 공급자 설정에는 영향을 주지 않는다.

실제 Gemini 연결을 명시적으로 확인할 때만 환경변수를 주입한 셸에서 다음을
실행한다.

```sh
PYTHONPATH=. .venv/bin/python LLM/tests/smoke_gemini.py
```

이 smoke 검증은 설정된 Gemini 모델마다 Prosody와 Speech 요청을 각각 한 번씩,
총 두 번 전송하므로 API 사용량이 발생한다. 응답 본문과 API 키는 출력하지 않는다.

### `Gemini API is disabled` 오류

`Gemini API authentication or permission failed` 또는
`Gemini API is disabled for this API key's Google Cloud project`가 표시되고
upstream 403 응답에 Generative Language API 비활성화가 포함되면, API 키를
바꾸기 전에 해당 키가 연결된 Google Cloud 프로젝트에서 **Generative Language
API**를 활성화한다. 활성화 뒤 전파에 몇 분이 걸릴 수 있으므로, 완료 후 기존
서버를 재시작하고 smoke 검증을 다시 실행한다. 키 값은 `llm.env`에만 두며
Git·명령행·브라우저에 넣지 않는다.

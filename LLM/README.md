# Local, Gemini, and OpenAI LLM API integration

LLM 기능은 별도 프록시 프로세스를 실행하지 않는다. 기존 `api.server`가 같은
포트에서 `/api/llm/models`와 `/api/llm/transform`을 제공한다.

규칙 기반 엔진과 LLM은 다음 순서로만 연결한다.

1. `/api/transform`: 사용자 원고를 패키징된 규칙 엔진에 전달해
   `normalized_text` 생성
2. `/api/llm/transform`: `normalized_text`를 `docs/LLM_prompt.txt`에 넣어
   읽기·발음·운율이 반영된 최종 `speech_text` 생성

LLM은 선택 모델로 한 번만 호출한다. 규칙 기반 `normalized_text` 계약과
source-free binary runtime은 이 통합으로 변경되지 않는다.
model을 생략하면 기본 로컬 모델 `gemma4:31b`를 사용한다. 규칙 확정
읽기를 위한 별도 lock/provenance, 반복 안정성 측정, 자동 재시도는
사용하지 않는다.

규칙 엔진은 문맥형 숫자+단위의 의미를 확정하지 못하면 해당 표면을
terminal preserve하고 raw 숫자를 남길 수 있다. 후단 LLM은
`normalized_text` 문장 자체와 일반적인 표준 한국어 용례를 이용해 의미별
읽기를 보완한다. 규칙 엔진의 decision log, candidate, marker는 LLM 요청에
붙이지 않는다. 여러 의미가 가능하면 가장 자연스러운 하나를 선택하여
값·단위·조사/접사를 유지한 한국어 읽기로 만들며, 정책상 보호 대상이
아닌 숫자와 영문을 `speech_text`에 남기지 않는다.

이미 규칙 엔진이 한글 읽기로 확정한 표면과 canonical spacing은 후단
LLM에서 고정한다. 대표적으로 `오분 뒤`, `삼번 버스`, `제 삼장`을
`오 분`, `삼 번`, `제삼장`으로 다시 쓰지 않는다. 따라서
`/api/transform`의 `normalized_text`는 LLM 없이 그대로 TTS에 전달할 수
있는 독립적인 최종 규칙 출력이다.

## 파일 구성

- `docs/LLM_prompt.txt`: `{{NORMALIZED_TEXT}}`를 정확히 한 번 포함하는 통합
  읽기·발음·운율 프롬프트
- `models.json`: 선택 가능한 모델, 공급자 및 기본 모델
- `openai_client.py`: OpenAI Responses API 호출 및 응답/오류 처리
- `response_validation.py`: 통합 LLM 출력 불변 조건 검증
- `docs/info_Local_LLM_server.txt`: 개발 참고용 서버 정보. 런타임은 이 파일에서
  인증정보를 읽지 않는다.

활성 프롬프트는 요청마다 UTF-8로 다시 읽는다. 파일을 수정하면 서버를
재시작하지 않아도 다음 요청부터 반영된다.

## API 계약

모델 목록:

```http
GET /api/llm/models
```

통합 LLM 요청:

```json
{
  "normalized_text": "국물은 좋습니다.",
  "model": "gemma4:31b"
}
```

응답:

```json
{
  "speech_text": "궁무른, 따뜨탐니다.",
  "model": "gemma4:31b",
  "elapsed_ms": 123.456
}
```

요청은 `normalized_text`만 입력으로 받으며 이전 `stage`와 `prosody_text` 필드는
거부한다. contextual decision metadata나 다른 규칙 엔진 내부 정보도
요청에 허용하지 않는다. 응답은 기존 공백·줄바꿈·고정 문장부호와 잠금 토큰을 보존하고,
운율용 쉼표와 ASCII 공백만 추가할 수 있다. 숫자 읽기에 포함된
소수점·자릿수 쉼표·시각 쌍점은 숫자 읽기로 소비할 수 있으며 문장부호나
파일 확장자의 마침표와 구분한다. 계약을 위반한 모델 응답은 조용히
보정하지 않고 upstream 응답 오류로 반환한다. 모델이 비어 있지 않은 문자열을
반환했으나 계약만 위반한 경우 오류 `detail`에는 `message`, `stage`와
`speech_text`가 포함된다. Web 화면은 원출력을 표시하고 계약 위반 변경을
강조한다. 입력에서 삭제된 구조 문자는 취소선과 계약 위반 테두리를 함께
표시한다.

## 환경변수

기존 API 서버 프로세스에 아래 값을 주입한다.

- `LOCAL_LLM_BASE_URL`: 로컬 LLM 애플리케이션 base URL
- `LOCAL_LLM_TOKEN`: 로컬 LLM bearer token
- `LOCAL_LLM_TIMEOUT_SECONDS`: upstream 제한시간(초), 기본값 `300`
- `GEMINI_API_KEY`: Gemini API 전용 키
- `GEMINI_TIMEOUT_SECONDS`: Gemini API 제한시간(초), 기본값 `300`
- `OPENAI_API_KEY`: OpenAI API 전용 키
- `OPENAI_TIMEOUT_SECONDS`: OpenAI API 제한시간(초), 기본값 `300`
- `OPENAI_REASONING_EFFORT`: GPT-5.6 추론 강도. `none`, `low`, `medium`,
  `high`, `xhigh`, `max` 중 하나이며 기본값은 `medium`

토큰과 API 키를 소스, 명령행 인자, Git 또는 브라우저에 넣지 않는다. Gemini
호출은 기존 API 서버가 `x-goog-api-key` 헤더를 사용해 서버 측에서만 수행한다.
OpenAI 호출도 기존 API 서버가 `Authorization: Bearer` 헤더를 사용해 서버
측에서만 수행한다.

## OpenAI GPT-5.6 Luna

웹 모델 선택기에는 `gpt-5.6-luna (medium)`, `gpt-5.6-luna (low)`,
`gpt-5.6-luna (none)`을 별도 항목으로 제공하지만, 세 항목 모두 OpenAI의
같은 upstream 모델 ID `gpt-5.6-luna`로 라우팅한다. 각 항목이 요청별
`reasoning.effort` 값을 지정한다. 호출에는
`POST https://api.openai.com/v1/responses`를 사용하고, 통합 프롬프트 전체를
Responses API의 `input`으로 전달한다. 모델 설정에 항목별 강도가 없을 때만
`OPENAI_REASONING_EFFORT`를 fallback으로 사용한다. 이 서비스는 요청 간 대화 상태를
사용하지 않으므로 `store=false`로 호출한다. 응답의 `output` 배열에서 모든
`message` 항목의 `output_text`를 순서대로 결합한 뒤 기존
`response_validation.py` 계약을 동일하게 적용한다.

현재 프로젝트의 `gpt-5.6-luna`는 비용 민감형 대량 처리용 모델이다. 모델과
Responses API 사양은 다음 공식 문서를 기준으로 한다.

- [GPT-5.6 Luna 모델](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
- [Responses API 텍스트 생성](https://developers.openai.com/api/docs/guides/text)
- [GPT-5.6 모델 가이드](https://developers.openai.com/api/docs/guides/latest-model)

### 기존 배포 명령을 사용하는 운영 서버

`bash scripts/deploy_server.sh`는 서버의
`~/tts-preprocessor/config/llm.env`를 읽을 수 있는지 먼저 확인하고, `LLM/` 런타임
코드와 통합 활성 프롬프트만 `app/LLM/`으로 배포한다. 개발 참고용
`LLM/docs/info_Local_LLM_server.txt`는 전송하지 않는다.

배포 전에 운영 서버에서 한 번만 다음처럼 환경 파일을 만든다. 값은 운영 환경의
실제 값으로 직접 입력하고, 파일 내용은 터미널 출력이나 Git에 넣지 않는다.

```sh
mkdir -p ~/tts-preprocessor/config
chmod 700 ~/tts-preprocessor/config
umask 077
editor ~/tts-preprocessor/config/llm.env
```

파일에는 로컬 LLM용 `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_TOKEN`, Gemini용
`GEMINI_API_KEY` 또는 OpenAI용 `OPENAI_API_KEY` 중 사용할 공급자의 설정을
`KEY=value` 형식으로 둔다. 필요하면 각 공급자의 timeout과 OpenAI 추론 강도를
설정한다. 최소 한 공급자가 완전히 설정되어야 서버가 시작된다. 이후에는
기존과 같이 `bash scripts/deploy_server.sh`를 실행한다.
시작 스크립트가 이 파일을 읽어 기존 API 서버 프로세스에만 환경변수로 전달한다.

OpenAI만 사용할 때의 예시는 다음과 같다. 실제 키 값은 운영 서버에서 직접
입력한다.

```sh
OPENAI_API_KEY=실제_키
OPENAI_REASONING_EFFORT=medium
OPENAI_TIMEOUT_SECONDS=300
```

## 확인

기존 서버가 실행된 상태에서 다음을 확인한다.

```sh
curl http://127.0.0.1:8010/api/llm/models
curl http://127.0.0.1:8010/docs
```

선택 공급자의 연결 실패는 LLM 단계에만 오류로 반환한다. 기존
`/api/transform` 규칙 기반 전처리와 다른 공급자 설정에는 영향을 주지 않는다.

실제 Gemini 연결을 명시적으로 확인할 때만 환경변수를 주입한 셸에서 다음을
실행한다.

```sh
PYTHONPATH=. .venv/bin/python LLM/tests/smoke_gemini.py
```

이 smoke 검증은 설정된 Gemini 모델마다 통합 요청을 한 번 전송하므로 API
사용량이 발생한다. 응답 본문과 API 키는 출력하지 않는다.

실제 OpenAI 연결은 `OPENAI_API_KEY`가 설정된 셸에서 다음으로 확인한다.

```sh
PYTHONPATH=. .venv/bin/python LLM/tests/smoke_openai.py
```

이 smoke 검증은 설정된 OpenAI 모델마다 통합 요청을 한 번 전송하므로 API
사용량이 발생한다. 성공 시 모델 ID, 출력 길이, 소요 시간만 출력하며 응답
본문과 API 키는 출력하지 않는다.

### OpenAI 오류

- `OpenAI API authentication failed.`: 키 값과 활성 상태를 확인한다.
- `OpenAI API key does not have permission ...`: 키가 속한 프로젝트에
  `gpt-5.6-luna` 사용 권한과 결제 설정이 있는지 확인한다.
- `OpenAI API quota or rate limit was exceeded.`: 프로젝트의 사용 한도와
  rate limit을 확인한 뒤 재시도한다.

### Gemini 403 오류

- `Gemini API is disabled ...`: 키가 연결된 Google Cloud 프로젝트에서
  **Generative Language API**를 활성화한 뒤 전파를 기다리고 재시도한다.
- `Gemini API key is blocked ...`: Google AI Studio에서 새 Gemini API 키를
  만들거나 기존 키의 API 제한을 **Generative Language API (Gemini API)**로
  설정한다.

키 값은 `llm.env`에만 두며 Git·명령행·브라우저에 넣지 않는다.

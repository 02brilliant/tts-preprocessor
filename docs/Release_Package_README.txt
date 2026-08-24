[TTS 전처리 실행모듈 사용 안내]

각 OS ZIP은 아래 네 실행 파일과 README.txt를 제공합니다. 사용자가 선택한
단계에 해당하는 실행 파일 하나만 호출하십시오.

- 1단계 규칙간소화: tts-preprocessor-simplified
- 2단계 규칙기반교정: tts-preprocessor
- 3단계 LLM최소: tts-preprocessor-llm-minimal
- 4단계 LLM자연스러운발화: tts-preprocessor-llm-natural

Windows에서는 각 파일명 끝에 .exe가 붙습니다. 0단계는 실행 파일을 호출하지
않고 원문을 그대로 사용합니다.

2단계는 전체 규칙 엔진을 한 번 실행합니다. 1단계는 같은 엔진·사전·숫자·기호·
단위 규칙을 공유하되 일반 영문 발음 fallback만 제외한 프로필입니다. 2단계가
1단계를 먼저 실행하는 구조는 아닙니다.

3단계와 4단계는 원문을 직접 입력받습니다. 각 실행 파일 내부에서 2단계 전체
규칙 엔진을 정확히 한 번 실행한 다음, 3단계는 LLM_prompt.txt, 4단계는
LLM_prompt_lv2.txt를 사용합니다. 호출 gate가 후속 교정 가능성을 찾으면 LLM을
한 번 호출하고 응답을 검증하며, 명백히 불필요하면 규칙 결과를 그대로 최종
출력합니다. 3단계는 일반 한국어 철자를 발음형으로 바꾸지 않고 잔여 읽기와
띄어읽기·쉼표를 처리합니다. 4단계만 합성어 `ㄴ` 첨가, 비예측적 된소리와
자연발화 축약을 적용합니다. 4단계는 3단계보다 생략 조건이 엄격하여 더 많은
입력에서 LLM을 호출하며, 한국어 발음 등록어 목록은 사용하지 않습니다. 별도
tts-llm-stage 실행 파일이나 --prompt-level 선택은 제공하지 않습니다.

Linux/macOS 예시:

  ./tts-preprocessor-simplified --text "ABC와 KOSPI, 3kg"
  ./tts-preprocessor --text "KBS 뉴스입니다"
  ./tts-preprocessor-llm-minimal --text "KBS 뉴스입니다" --model "gemma4-31B-it (vLLM)"
  ./tts-preprocessor-llm-natural --text "KBS 뉴스입니다" --model "gemma4-31B-it (vLLM)"
  ./tts-preprocessor-llm-minimal --check
  ./tts-preprocessor-llm-natural --check

Windows PowerShell 예시:

  .\tts-preprocessor-simplified.exe --text "ABC와 KOSPI, 3kg"
  .\tts-preprocessor.exe --text "KBS 뉴스입니다"
  .\tts-preprocessor-llm-minimal.exe --text "KBS 뉴스입니다" --model "gemma4-31B-it (vLLM)"
  .\tts-preprocessor-llm-natural.exe --text "KBS 뉴스입니다" --model "gemma4-31B-it (vLLM)"

LLM 실행 파일은 --text, --input, 표준입력, --output, --json, --model,
--list-models, --check를 지원합니다. 공급자별 환경변수는 운영 환경에서
설정하며 인증정보를 실행 파일이나 명령행에 포함하지 마십시오.
--json 응답의 rule_elapsed_ms는 규칙기반 처리시간, llm_elapsed_ms는 프롬프트
구성·LLM 호출·응답 검증을 포함한 LLM 처리시간입니다. elapsed_ms는 LLM 서버
요청시간 호환 필드입니다. llm_called가 false이면 LLM을 생략한 것이며,
speech_text는 normalized_text와 같고 elapsed_ms·llm_elapsed_ms는 0.0입니다.
llm_skip_reason에는 생략 사유 코드가 들어갑니다.

- 로컬 모델: LOCAL_LLM_BASE_URL, LOCAL_LLM_TOKEN
- Gemini: GEMINI_API_KEY
- OpenAI: OPENAI_API_KEY
- vLLM: VLLM_BASE_URL, VLLM_TOKEN

## 패키지 실행모듈의 LLM 서버

웹페이지는 모델 선택을 제공하지만, ZIP으로 배포되는 3단계·4단계 실행모듈은
`gemma4-31B-it (vLLM)` 모델을 고정해 사용합니다. 이 모델의 vLLM upstream ID는
`google/gemma-4-31B-it`이며, 웹페이지에서 선택한 다른 모델 설정은 패키지
실행모듈에 전달되지 않습니다. `--model`을 생략해도 이 모델이 기본값으로
사용되며, 명시할 때도 동일한 모델 ID를 사용하십시오.

실행 환경은 사내 네트워크에서 해당 vLLM 서버에 접근할 수 있어야 합니다. 운영팀은
실행파일을 호출하는 환경에 서버가 제공한 값을 다음과 같이 주입하십시오.

- `VLLM_BASE_URL`: 사내 vLLM OpenAI-compatible 서버의 base URL
- `VLLM_TOKEN`: 서버가 요구하는 Bearer 인증 토큰

실행모듈은 `POST {VLLM_BASE_URL}/v1/chat/completions`로 요청합니다. `VLLM_BASE_URL`에
이미 `/v1` 또는 `/v1/chat/completions`가 포함되어 있으면 경로를 중복하지 않습니다.
서버 주소와 인증 토큰은 패키지 README·실행파일·명령행에 기록하지 말고 운영 환경의
환경변수로만 관리하십시오. `--check`는 패키지 자산을 확인하며 vLLM 연결 확인은
실제 LLM 실행 시 수행됩니다.

LLM 응답이 문장 구조, 보호 표면, 규칙 확정 읽기 계약을 위반하면 임의로
보정하거나 통과시키지 않고 오류로 종료합니다. 임시 LOCK 토큰이나 규칙 엔진의
내부 메타데이터는 LLM 입력에 추가하지 않습니다.

운영체제별 ZIP:

- Linux: tts-preprocessor-linux.zip
- macOS Apple Silicon arm64: tts-preprocessor-macos.zip
- Windows: tts-preprocessor-windows.zip

각 운영체제에 맞는 ZIP을 사용하십시오. macOS 패키지는 Intel x86_64 및
Universal Binary를 지원하지 않으며 코드 서명·공증이 포함되지 않습니다.

[TTS 전처리 실행모듈 사용 안내]

이 실행모듈은 사용자가 입력한 TTS 스크립트를 발음교정 처리하여
TTS 엔진에서 자연스럽게 읽히도록 변환하는 역할을 합니다.

숫자, 날짜, 시간, 단위, 통화, 약어, 범위, 전화번호, 특수기호 등을
한국어 TTS가 읽기 좋은 발화 형태로 변환합니다.

--------------------------------------------------
■ 제공 실행모듈
--------------------------------------------------

현재 실행모듈은 운영체제별로 3가지가 제공됩니다.

1) Linux 실행모듈
   - 배포 ZIP: tts-preprocessor-linux.zip
   - 파일명: tts-preprocessor
   - Linux 서버/API/웹 backend 연동용
   - 예시 경로: ./tts-preprocessor

2) Windows 실행모듈
   - 배포 ZIP: tts-preprocessor-windows.zip
   - 파일명: tts-preprocessor.exe
   - Windows PC 또는 Windows 서버에서 직접 실행 가능

3) macOS 실행모듈
   - 배포 ZIP: tts-preprocessor-macos.zip
   - 파일명: tts-preprocessor
   - Apple Silicon arm64 Mac에서 직접 실행 가능
   - Intel x86_64 및 Universal Binary는 현재 지원 범위가 아닙니다.
   - 서명/공증이 포함되지 않아 최초 실행 시 Gatekeeper 경고가 표시될 수 있습니다.

주의:
- Linux 운영 서버용 실행모듈과 Windows/macOS 실행모듈은 서로 다른 OS용 바이너리입니다.
- 사용하는 운영체제에 맞는 실행모듈을 다운로드하여 사용해야 합니다.
- Windows/macOS 실행모듈은 보조 배포용이며, 서버 운영 배포 기준은 Linux 실행모듈입니다.
- 새 Linux 운영 버전 배포 직후 Windows ZIP은 같은 소스 버전의 GitHub Actions
  빌드가 완료될 때까지 일시적으로 제공되지 않을 수 있습니다.

--------------------------------------------------
■ 주요 변환 기능
--------------------------------------------------

- 숫자 / 날짜 / 시간 / 단위 / 통화 → 한국어 발화 형태 변환
- 약어 / 사전 기반 읽기 변환
- 범위 / 비율 / 온도 / 퍼센트 / 전화번호 변환
- 보호 구간 보존
- 쉼표 추가 삽입 (leading-connector comma adapter, insert-only)
- 문단 분리 (current production: comma·bracket filter 후 split_paragraphs로 보수적 줄바꿈)

예:

입력:
AI는 2025-01-03에 3kg 제품을 69% 할인한다

출력:
에이아이는 이천이십오년 일월 삼일에 삼 킬로그램 제품을 육십구 퍼센트 할인한다

--------------------------------------------------
■ 괄호 및 보호 구간 사용 규칙
--------------------------------------------------

- ( ) → 괄호와 괄호 안 내용을 제거합니다.
- [ ] → 괄호 안 내용은 유지하고, 괄호 기호만 제거합니다.
- ` ` → 백틱 안 내용은 code-like 입력으로 보고 변환하지 않습니다.

예:

입력:
가격은 (임시) 3kg입니다

출력:
가격은 삼 킬로그램입니다

입력:
가격은 [3kg]입니다

출력:
가격은 3kg입니다

입력:
값은 `3kg`입니다

출력:
값은 `3kg`입니다

--------------------------------------------------
■ 지원 입력/출력 방식
--------------------------------------------------

이 실행모듈은 다음 3가지 방식을 지원합니다.

1) 문자열 입력 방식
   - 실시간 처리/API 연동에 권장

2) 파일(txt) 입력 방식
   - 배치 처리에 적합

3) 표준입력(stdin) 방식
   - 파이프라인 처리에 적합

--------------------------------------------------
■ OS별 실행 파일명
--------------------------------------------------

Linux:
  ./tts-preprocessor

Windows:
  tts-preprocessor.exe

macOS:
  ./tts-preprocessor

아래 예시는 각 OS별 실행 파일명만 다르고, 옵션 사용 방식은 동일합니다.

--------------------------------------------------
■ 1. 문자열 입력 방식
--------------------------------------------------

직접 문자열을 입력하여 변환 결과를 출력합니다.

[Linux]

./tts-preprocessor --text "AI는 2025-01-03에 3kg 제품을 69% 할인한다"

[Windows - PowerShell 또는 CMD]

.\tts-preprocessor.exe --text "AI는 2025-01-03에 3kg 제품을 69% 할인한다"

[macOS]

./tts-preprocessor --text "AI는 2025-01-03에 3kg 제품을 69% 할인한다"

출력:

에이아이는 이천이십오년 일월 삼일에 삼 킬로그램 제품을 육십구 퍼센트 할인한다

--------------------------------------------------
■ 2. 파일(txt) 입력 방식
--------------------------------------------------

입력 파일을 읽어서 출력 파일로 결과를 저장합니다.

[Linux]

./tts-preprocessor --input input.txt --output output.txt

[Windows - PowerShell 또는 CMD]

.\tts-preprocessor.exe --input input.txt --output output.txt

[macOS]

./tts-preprocessor --input input.txt --output output.txt

input.txt:

AI는 2025-01-03에 3kg 제품을 69% 할인한다

output.txt:

에이아이는 이천이십오년 일월 삼일에 삼 킬로그램 제품을 육십구 퍼센트 할인한다

--------------------------------------------------
■ 3. 표준입력(stdin) 방식
--------------------------------------------------

파이프를 이용한 입력 처리 방식입니다.

[Linux]

echo "AI는 2025-01-03에 3kg 제품을 69% 할인한다" | ./tts-preprocessor

[Windows - PowerShell]

"AI는 2025-01-03에 3kg 제품을 69% 할인한다" | .\tts-preprocessor.exe

[Windows - CMD]

echo AI는 2025-01-03에 3kg 제품을 69% 할인한다 | tts-preprocessor.exe

[macOS]

echo "AI는 2025-01-03에 3kg 제품을 69% 할인한다" | ./tts-preprocessor

출력:

에이아이는 이천이십오년 일월 삼일에 삼 킬로그램 제품을 육십구 퍼센트 할인한다

--------------------------------------------------
■ TTS 시스템 연동 방법
--------------------------------------------------

TTS 시스템에서는 파일 방식보다 문자열 입력 방식을 권장합니다.

권장 방식:
- TTS backend에서 실행모듈을 subprocess로 호출
- 입력 문장을 --text 인자로 전달
- stdout을 발음교정 결과로 사용

--------------------------------------------------
[Python 예제 - Linux/macOS]
--------------------------------------------------

import subprocess

text = "AI는 2025-01-03에 3kg 제품을 69% 할인한다"

result = subprocess.run(
    ["./tts-preprocessor", "--text", text],
    capture_output=True,
    text=True,
    encoding="utf-8",
    check=True,
)

pron_text = result.stdout.strip()
print(pron_text)

--------------------------------------------------
[Python 예제 - Windows]
--------------------------------------------------

import subprocess

text = "AI는 2025-01-03에 3kg 제품을 69% 할인한다"

result = subprocess.run(
    [r".\tts-preprocessor.exe", "--text", text],
    capture_output=True,
    text=True,
    encoding="utf-8",
    check=True,
)

pron_text = result.stdout.strip()
print(pron_text)

--------------------------------------------------
[Node.js 예제 - Linux/macOS]
--------------------------------------------------

const { execFile } = require("child_process");

const text = "AI는 2025-01-03에 3kg 제품을 69% 할인한다";

execFile(
  "./tts-preprocessor",
  ["--text", text],
  { encoding: "utf8" },
  (err, stdout, stderr) => {
    if (err) {
      console.error(stderr);
      throw err;
    }

    const pron_text = stdout.trim();
    console.log(pron_text);
  }
);

--------------------------------------------------
[Node.js 예제 - Windows]
--------------------------------------------------

const { execFile } = require("child_process");

const text = "AI는 2025-01-03에 3kg 제품을 69% 할인한다";

execFile(
  ".\\tts-preprocessor.exe",
  ["--text", text],
  { encoding: "utf8" },
  (err, stdout, stderr) => {
    if (err) {
      console.error(stderr);
      throw err;
    }

    const pron_text = stdout.trim();
    console.log(pron_text);
  }
);

--------------------------------------------------
■ Linux 사용 시 주의사항
--------------------------------------------------

- 실행 권한이 필요할 수 있습니다.

chmod +x ./tts-preprocessor

- 서버/API 연동 시에는 packaged 실행모듈 경로를 명확히 지정하는 것을 권장합니다.
- 운영 API는 source import가 아니라 실행모듈 subprocess 호출 방식으로 연동해야 합니다.

--------------------------------------------------
■ Windows 사용 시 주의사항
--------------------------------------------------

- PowerShell에서는 실행 파일 앞에 .\ 를 붙여 실행합니다.
  예: .\tts-preprocessor.exe --text "문장"

- CMD에서는 현재 폴더에 있는 실행 파일을 직접 실행할 수 있습니다.
  예: tts-preprocessor.exe --text "문장"

- 입력/출력 파일은 UTF-8 인코딩을 권장합니다.

--------------------------------------------------
■ macOS 사용 시 주의사항
--------------------------------------------------

- 최초 실행 시 실행 권한이 필요할 수 있습니다.

chmod +x ./tts-preprocessor

- 서명/공증되지 않은 실행모듈은 Gatekeeper 경고가 표시될 수 있습니다.
- 경고가 표시되면 macOS 보안 설정에서 실행을 허용해야 할 수 있습니다.
- 현재 제공 ZIP은 Apple Silicon arm64 전용입니다.
- Intel Mac용 x86_64 및 Universal Binary는 제공하지 않습니다.
- 입력/출력 파일은 UTF-8 인코딩을 권장합니다.

--------------------------------------------------
■ 공통 주의사항
--------------------------------------------------

- 운영 반영 전 반드시 테스트 후 적용하십시오.
- 입력 텍스트는 UTF-8 인코딩을 사용하십시오.
- stdout은 변환 결과로 사용합니다.
- stderr는 오류/진단 메시지 확인에 사용합니다.
- 실행 실패 시 exit code와 stderr를 함께 확인하십시오.
- source code를 수정한 뒤에는 반드시 실행모듈을 재빌드해야 합니다.

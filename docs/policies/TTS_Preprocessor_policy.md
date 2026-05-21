# TTS Preprocessor Policy

이 문서는 현재 TTS Preprocessor 구현과 테스트 판단의 단일 canonical policy이다. 버전별 보존 문서와 과거 변경 기록은 참고 자료이며, 정책 해석과 구현 판단은 이 문서를 우선한다.

이 문서는 owner/claim/gate, full consume, unsafe preserve, bracket protection, no-crash fallback, Korean eligibility, symbol alias, preserve taxonomy, numeric/unit/currency/date/range/code-separator 정책을 하나의 본문으로 통합한다.

전처리 대상 여부를 결정하는 앞단 gate는 기존 owner 정책을 대체하지 않는다. 기존 owner는 eligible segment에 대해서만 기존 정책대로 동작한다. preserve로 분류된 segment는 기본적으로 owner가 접근하지 않으며 원문 그대로 반환한다. 단, 본 문서에서 `Owner Fallback Candidate`로 명시된 경우는 초기 preserve claim이 아니라 다음 후보 owner 평가를 허용한다. `Absolute Preserve`, `Owner Fallback Candidate`, `Terminal Fallback Preserve`는 반드시 구분한다.

---

## 0.0 Korean Eligibility / Symbol Alias Integrated Policy

### 0.0.1 Guard 우선순위 고정

Korean Eligibility Gate는 반드시 아래 순서로 평가한다. 구현자는 이 순서를 바꾸면 안 된다.

1. **Code-like / URL / email / file path / JSON / shell command preserve**
   - 이 판정은 numeric-list 판정보다 항상 우선한다.
   - 한글이 없는 code-like segment 안에 숫자, 단위, 통화, slash, percent, pH, Hz 등이 있어도 부분 rewrite하지 않는다.
2. **전체 입력 standalone supported token transform**
   - 전체 입력에 한글이 없어도, 입력 전체가 정책에 명시된 standalone numeric/unit/currency/fraction/duration/percent-point/pH/frequency token이면 기존 owner 정책으로 변환한다.
3. **전체 입력 no-Hangul global bypass**
   - 전체 입력에 한글 음절 `[가-힣]`이 없고 standalone supported token도 아니면 원문 전체를 preserve한다.
4. **전체 입력에 한글이 있는 경우 line-level gate 적용 여부 결정**
   - 모든 non-empty line이 Korean-eligible line이면 line별 transform을 하지 않고 기존 core transform을 한 번만 실행한다.
   - 한글 line과 no-Hangul line이 섞인 mixed input에서만 line-level gate를 적용한다.
5. **line-level gate 내부 우선순위**
   - empty/blank line preserve
   - code-like / URL / email / path / JSON / shell preserve
   - Korean line transform
   - standalone supported token line transform
   - Korean-context numeric-list line transform
   - 그 외 no-Hangul line preserve

구현자는 다음과 같은 단순 guard를 사용하면 안 된다.

```python
if no_hangul(text):
    return text
```

위 구현은 `25℃`, `$25.99`, `1/3`, `2.5%p`, `pH 7.4`, `60Hz`, `3시간 18분` 같은 standalone supported token을 잘못 preserve하므로 정책 위반이다. standalone supported token 판정은 global no-Hangul bypass보다 반드시 먼저 수행한다.

#### 0.0.1.1 Standalone Numeric vs Code-like Numeric Clarification

입력 전체가 pure numeric token 하나이고 URL/path/email/JSON/shell/code-like 구조를 형성하지 않으면 standalone supported token으로 본다. 단, 숫자가 code-like line, JSON, shell command, assignment, path, URL, identifier-like token 내부에 포함되어 있으면 code-like preserve가 우선한다.

사용자가 pure numeric 입력을 코드 조각으로 의도했는지는 문자열만으로 판별하지 않는다. 별도 runtime profile 또는 caller metadata가 없는 한 standalone numeric transform을 적용한다.

Pure numeric token에는 plain integer와 valid thousands-comma integer를 포함한다. 일반 한국어 원고 또는 numeric-list segment 안의 bare integer/comma integer는 owner가 full consume하여 일반 정수 reading으로 변환한다. List separator comma는 숫자 내부 comma와 구분하며, invalid comma나 identifier/code-like 내부 숫자는 preserve한다.

큰 수는 4자리 단위로 묶어 읽는다. 큰 단위는 `만`, `억`, `조`, `경` 순서로 붙이고, 0인 묶음은 읽지 않는다. 같은 4자리 묶음 내부는 붙여 읽으며, non-empty 큰 단위 묶음 사이에는 한 칸을 둔다. 마지막 단위 없는 묶음도 앞 묶음과 한 칸 띄운다.

```text
12345 -> 만 이천삼백사십오
1,250 -> 천이백오십
12,345 -> 만 이천삼백사십오
123,456 -> 십이만 삼천사백오십육
1,234,567 -> 백이십삼만 사천오백육십칠
12,345,678,901 -> 백이십삼억 사천오백육십칠만 팔천구백일
12,345,678,901,234 -> 십이조 삼천사백오십육억 칠천팔백구십만 천이백삼십사
12,345,678,901,234,567 -> 일경 이천삼백사십오조 육천칠백팔십구억 백이십삼만 사천오백육십칠
100,000,001 -> 일억 일
100,010,001 -> 일억 만 일
1,000,100,000 -> 십억 십만
1,250, 12,345 -> 천이백오십, 만 이천삼백사십오
const x = 12345; -> const x = 12345;
{"value":12345} -> {"value":12345}
id_12345 -> id_12345
A12345 -> A12345
v1.2.3 -> v1.2.3
```

### 0.0.2 Global Korean Eligibility Bypass

입력 전체에 한글 음절 `[가-힣]`이 전혀 없고, 입력 전체가 standalone supported token도 아니며, 입력이 영어/비한국어 prose 또는 code-like block이면 원문 전체를 preserve한다.

Preserve 예:

```text
The temperature is 25℃.
The price is $25.99.
pH 7.4 was maintained for 3 hours.
The ratio is 1/3 and the change is 2.5%p.
curl -X POST http://localhost:8010/api/transform
{"text":"25℃"}
```

Standalone supported token 예외는 global bypass보다 우선한다.

Transform 예:

```text
25℃ -> 이십오도
$25.99 -> 이십오쩜구구 달러
1/3 -> 삼분의 일
2.5%p -> 이쩜오 퍼센트포인트
45m² -> 사십오 제곱미터
pH 7.4 -> 피에이치 칠쩜사
60Hz -> 육십 헤르츠
3시간 18분 -> 세 시간 십팔분
```

### 0.0.2.1 Hangul-containing input whole-fallback prohibition

입력 전체에 한글 음절 `[가-힣]`이 하나라도 포함되어 있으면, 입력 전체 raw text를 통째로 preserve/fallback하여 반환하는 것은 금지한다.

예외는 변환 가능한 surface가 전혀 없어서 결과가 우연히 원문과 같은 경우뿐이다.

parser failure, owner collision, render failure, validation failure, unsafe tail, unsupported token, inline JSON, inline shell command, inline URL/email/path/code-like token은 해당 span, 해당 token, 해당 sentence, 해당 line 중 가장 좁은 안전 단위로만 preserve한다.

한글 포함 입력에서 하나의 실패가 입력 전체 transform을 막으면 regression failure로 본다.

### 0.0.3 Line-level Korean Eligibility Gate

전체 입력에 한글이 포함되어 있고, 한글 line과 no-Hangul line이 섞인 경우에만 line-level gate를 적용한다. line split/join은 원래 newline separator를 보존해야 한다.

Line 분류:

1. **Korean line**
   - 한글 음절 `[가-힣]` 포함
   - 기존 core transform 적용
2. **Standalone supported token line**
   - 한글 없음
   - line 전체가 지원 token
   - 기존 owner 정책으로 transform
3. **Numeric-list line**
   - 한글 없음
   - 한국어 문맥 사이에 있는 숫자/단위/기호 목록
   - 기존 owner 정책으로 transform
4. **Non-Korean preserve line**
   - 영어 prose, URL, email, path, JSON, shell, code-like line
   - 원문 preserve
5. **Empty/blank line**
   - preserve
   - numeric-list adjacency를 끊는 boundary

### 0.0.4 Numeric-list adjacency 정의

`numeric-list line`은 다음 조건을 모두 만족해야 한다.

1. 현재 line 자체에는 한글 음절 `[가-힣]`이 없다.
2. 현재 line은 URL, email, file path, JSON, shell command, code-like segment가 아니다.
3. 현재 line은 숫자, 단위, 통화, 비율, 분수, 온도, 시간, percent-point, pH, frequency, 쉼표, 공백, 허용된 owner-local alias symbol 중심의 목록형 segment이다.
4. 현재 line의 **직전 또는 직후 non-empty line** 중 하나가 Korean-eligible line이다.

인접성은 “직전/직후 non-empty line”까지만 본다. `위로 2줄`, `아래로 1줄` 같은 확장 window는 적용하지 않는다.

빈 줄은 preserve하며, numeric-list adjacency를 끊는 boundary로 본다. 영어 prose, URL, email, path, JSON, shell command, code-like line도 문맥 boundary로 본다.

Transform 예:

```text
오늘 관측값입니다.
25℃, 3시간 18분, 2.5%p, 1/3, 45m², $25.99
이상입니다.
```

Expected:

```text
오늘 관측값입니다.
이십오도, 세 시간 십팔분, 이쩜오 퍼센트포인트, 삼분의 일, 사십오 제곱미터, 이십오쩜구구 달러
이상입니다.
```

Preserve 예:

```text
오늘 원문 인용입니다.
The temperature is 25℃ and pH 7.4.
이상입니다.
```

Expected:

```text
오늘 원문 인용입니다.
The temperature is 25℃ and pH 7.4.
이상입니다.
```

### 0.0.5 Preserve 대상 exact preservation 계약

`Absolute Preserve`로 분류된 line 또는 전체 입력은 exact string preservation을 보장해야 한다. 다음 항목은 transform 대상이 아니면 공백, 문장부호, 기호, 대소문자, escape sequence를 변경하지 않고 그대로 반환한다.

1. 비한국어 prose
2. URL
3. email
4. file path
5. JSON
6. shell command
7. code snippet
8. code-like line
9. square bracket 내부 보호 구간
10. unsafe alphabetic/identifier tail로 인해 owner가 full consume을 금지한 surface

Transform 대상 한국어 line에서는 기존 prosody/paragraph 정책을 따른다. `Absolute Preserve` 대상 line에 대해서만 exact string preservation을 요구한다. `Owner Fallback Candidate`는 이 절의 exact preserve 대상이 아니며, 모든 후보 owner가 실패했을 때만 `Terminal Fallback Preserve`로 원문 출력된다.

### 0.0.5.1 Preserve taxonomy / Owner Fallback terminology

본 문서의 `preserve`는 구현에서 반드시 다음 세 종류로 구분한다. Codex 구현자는 “owner 실패”와 “absolute preserve”를 혼동하면 안 된다.

#### Absolute Preserve

`Absolute Preserve`는 해당 segment에 어떤 owner도 재진입하지 않는 보호 상태다. 이 상태에서는 내부 숫자, 통화, 단위, pH, Hz, slash, percent 등을 다시 읽지 않는다.

대상:

```text
URL
email
file path
JSON
shell command
code snippet
code-like line
non-Korean prose global bypass
Korean literal lock
Korean-to-Korean space lock
Korean punctuation lock
square bracket internal boundary
unsafe alphabetic/identifier tail
```

예:

```text
https://example.com/a?x=1 -> same
test@example.com -> same
/home/user/file.txt -> same
The temperature is 25℃. -> same
const value = "$25.99"; -> same
15.2km/La -> same
pH7.4test -> same
40℉abc -> same
[3kg] -> 3kg
```

#### Owner Fallback Candidate

`Owner Fallback Candidate`는 특정 owner의 claim/gate 조건을 만족하지 않는 경우 다음 후보 owner로 넘길 수 있는 상태다. 이 단계에서는 preserve claim을 만들지 않는다. 모든 후보 owner가 실패할 때만 최종 원문 출력으로 떨어진다.

대표 대상:

```text
event owner 실패 dotted numeric -> dotted decimal owner
calendar-invalid date-like -> guarded code separator owner
middle-dot event 실패 -> middle-dot numeric block owner
generic numeric + Korean suffix -> numeric suffix / counter owner
leading-zero numeric block -> code digit reading fallback
hyphen numeric candidate -> range/date/phone/code 후보 평가 후 terminal fallback
two-block N-M / N:M numeric-delimited candidate -> specific owner first, broad numeric fallback blocked
```

예:

```text
13.3 비상계엄 -> 십삼쩜삼 비상계엄
12.32 사태 -> 십이쩜삼이 사태
12·3수치 -> 십이 삼수치
2025-13-03 -> 이공이오 일삼 공삼
010 - 1234 - 5678 -> 공일공 천이백삼십사 오천육백칠십팔
0.8초 -> 영쩜팔초
제15권 -> 제 십오권
```

#### Terminal Fallback Preserve

`Terminal Fallback Preserve`는 모든 후보 owner가 실패하거나 full consume/validation에 실패한 뒤 최종적으로 원문을 출력하는 안전 상태다. 이는 초기 preserve classification과 구분한다.

예:

```text
1,23,456원 -> 1,23,456원
12.5MBabc -> 12.5MBabc
010 - ABC - 5678 -> 010 - ABC - 5678
```

금지:

```text
owner 실패를 즉시 Absolute Preserve로 처리
Absolute Preserve segment 내부를 다음 owner로 재진입
full consume 실패 후 일부만 변환하고 raw residue를 남김
```

#### Numeric-delimited two-block fallback blocking

`N-M`, `N:M` 형태의 two-block numeric-delimited surface는 broad numeric fallback 대상이 아니다.

이 상태는 `NO_CLAIM_BLOCK_NUMERIC_FALLBACK`으로 해석한다.

- specific owner가 명시 gate를 만족하면 먼저 claim할 수 있다.
- specific owner가 없으면 broad number owner가 내부 `N`, `M` 블럭에 재진입해 부분 변환하면 안 된다.
- 최종 출력이 원문과 같더라도 이는 즉시 `FINAL_PRESERVE`로 분류했다는 뜻이 아니다.
- URL/path/email/code/backtick/fenced code/JSON-like protected span 내부, code-like token, unsafe tail, 파일명/확장자 내부는 `Absolute Preserve` 성격으로 처리한다.

Numeric-delimited owners must not hard-code delimiter characters independently.
They must use shared delimiter equivalence classes during owner scanning.
Delimiter equivalence is scanner-local only: implementations must not globally
rewrite or normalize the input string, and the original surface must remain
available for preserve decisions and output.

First-pass shared delimiter classes:

```text
COLON_LIKE_DELIMITERS: :, ：
RANGE_LIKE_DELIMITERS: -, –, ~, ～
TILDE_LIKE_DELIMITERS: ~, ～, ∼, 〜
```

`COLON_LIKE_DELIMITERS` define the delimiter set for `N:M` time, semantic pair,
and fallback-block scanning. `RANGE_LIKE_DELIMITERS` define the delimiter set for
`N-M` range-compatible unit reading and fallback-block scanning. Current
tilde-like numeric range policy is owner-local and uses `TILDE_LIKE_DELIMITERS`
(`~`, `～`, `∼`, `〜`) for broad `에서` reading.

Out of scope for this first pass: ratio sign `∶`, minus sign `−`, em dash `—`,
date owner delimiter expansion, phone owner delimiter expansion, slash ratio,
full-width slash ratio, and Korean `대` delimiter. `∼` and `〜` are not part of
`RANGE_LIKE_DELIMITERS`, but they are in scope for the current tilde-like range
owner through `TILDE_LIKE_DELIMITERS`.

Numeric-delimited owners may use a shared decimal-aware numeric block parser.
The shared numeric block accepts unsigned integer and unsigned decimal forms,
and may accept an optional leading ASCII sign only in owners that explicitly opt
into signed numeric-delimited surfaces. `-` is rendered as `마이너스`; `+` is
rendered as `플러스`. Valid thousands comma grouping is allowed only in the
integer part. The decimal part is a literal `.` followed by one or more ASCII
digits. Fractional digits are preserved for reading, including trailing zeros,
and no system-level limit is imposed on fractional digit length.

Allowed examples:

```text
0
0.5
0.0
1
1.50
1,000.5
1,000,000.000
```

Rejected examples:

```text
-1
01
001
01.5
01,000.5
.5
1.
1,00
10,00
1,0000
1.2.3
```

Comma is validation-only. Rendering removes comma from the integer part and
uses the existing integer reading. Decimal numeric-delimited owners must follow
the existing decimal canonical: the separator is rendered as `쩜`, not spaced
`점`, and the fractional digit sequence is rendered digit-by-digit without
converting through float or Decimal value semantics. A leading minus sign is
rendered with the existing signed-number canonical, defaulting to `마이너스`;
a leading plus sign is rendered as `플러스`. Invalid signed decimal/comma
formats must not partially rewrite internal numeric fragments.

```text
1.0 -> 일쩜영
1.50 -> 일쩜오영
1.500 -> 일쩜오영영
0.05 -> 영쩜영오
2.000 -> 이쩜영영영
1,000.5 -> 천쩜오
1,000,000.000 -> 백만쩜영영영
-1.250 -> 마이너스 일쩜이오영
-0.0 -> 마이너스 영쩜영
+1.250 -> 플러스 일쩜이오영
+0.0 -> 플러스 영쩜영
```

Leading plus sign numeric policy:

A leading plus sign before a valid numeric surface may be read as `플러스` only
when an appropriate owner can safely and fully claim the surface. This includes
general signed numbers, unit/symbol/currency/temperature/percent surfaces,
numeric-delimited semantic pair and multi-colon surfaces, tilde-like signed
range surfaces, and international phone numbers. The decimal separator remains
the compact `쩜` canonical and fractional trailing zeros are preserved.
Temperature owner surfaces are the sign-canonical exception: leading `+` on
Celsius/Fahrenheit temperature symbols is rendered as `영상`, and leading `-` is
rendered as `영하`. Temperature owners must full-consume signed temperature
surfaces before general signed number/unit owners.

The plus sign must not be claimed inside protected/code-like/path/URL/email
contexts or math/code-like expressions such as `C++`, `A+B`, `foo+bar`, or
`a+=1`. If a plus-signed numeric-like surface cannot be fully claimed by its
owner, broad numeric fallback must not partially rewrite internal numeric
fragments. Signed range with `-` or `–` remains out of scope.

Plus-signed Korean suffix currency must full-consume valid comma-decimal KRW
forms such as `+1,000.50원`; the amount is read with the signed numeric
canonical (`플러스 천쩜오영`) and the `원` suffix remains the currency suffix.
Invalid comma/leading-zero forms such as `+1,00.5원` and `+01원` remain
unclaimed and must not partially rewrite internal numeric fragments.

```text
+1 올랐다 -> 플러스 일 올랐다
값은 +1.5입니다 -> 값은 플러스 일쩜오입니다
+1.5kg -> 플러스 일쩜오 킬로그램
-25kg -> 마이너스 이십오 킬로그램
+25℃ -> 영상 이십오도
+25°C -> 영상 이십오도
+77℉ -> 화씨 영상 칠십칠도
+77°F -> 화씨 영상 칠십칠도
+10% -> 플러스 십 퍼센트
+1,000원 -> 플러스 천 원
+1,000.50원 -> 플러스 천쩜오영 원
+82-10-1234-5678 -> 플러스 팔이 일공 일이삼사 오육칠팔

+.5 -> +.5
++1 -> ++1
+01 -> +01
C++17 -> C++17
email+tag@example.com -> email+tag@example.com
https://example.com?q=+1 -> https://example.com?q=+1
/path/+1/log -> /path/+1/log
```

Unit and percent suffix spacing consistency:

Registered unit suffixes allow both attached and single ASCII-space-separated
forms after a valid signed decimal-aware numeric block. Both forms use the same
unit canonical renderer. Two or more spaces, tabs, or newlines are not treated
as suffix attachment. Invalid numeric blocks are preserved and must not be
partially rewritten.

The percent suffix `%` allows both attached and single ASCII-space-separated
forms after a valid signed decimal-aware numeric block and is rendered as
`퍼센트`. Two or more spaces, tabs, or newlines are not treated as suffix
attachment. Invalid numeric blocks are preserved.

Currency registry entries define canonical currency reading, ISO/code aliases,
symbol aliases, and suffix aliases. Registered currency forms share the same
valid signed decimal-aware numeric parser and canonical renderer.

For a registered currency, equivalent prefix/suffix/code/symbol forms with the
same valid signed decimal-aware numeric block must render to the same canonical
output.

Examples for KRW:

```text
1,000원 / 1,000 원 / KRW1000 / KRW1,000 / KRW 1,000 / ₩1,000 / ￦1,000 / 1000KRW / 1,000KRW / 1,000 KRW -> 천 원
```

Only no-space or one ASCII-space attachment is allowed between currency marker
and number. Two or more spaces, tabs, or newlines are not treated as a single
currency surface.

Invalid numeric blocks are preserved and must not be partially rewritten.

Protected/path/url/email/backtick/JSON-like/code-like surfaces remain preserve.

Math-like expressions are preserved as whole spans until a dedicated math
reading owner is designed. This protection is limited to clear operator
expressions such as `A+B`, `x+y=3`, `a+=1`, `x-y=3`, `x*2=4`, `x/2=3`,
`a==1`, `a>=1`, and `a<=1`; their internal numeric fragments must not be read
by broad numeric fallback. This does not change ordinary signed number handling
such as `값은 +1입니다`.

These targeted follow-up rules do not change bracket/parenthesis elision,
square-bracket protection, temperature sign canonical (`+온도` -> `영상`,
or `-온도` -> `영하`).

`N-M` 단독 또는 ambiguous form은 claim하지 않고 내부 numeric fallback도 막는다.

```text
1-2 -> 1-2
03-04 -> 03-04
12-31 -> 12-31
123-456 -> 123-456
```

`N-M` 뒤에 optional ASCII space와 range-compatible registered unit/counter/classifier/range noun이 있을 때만 range reading으로 처리한다. 모든 등록 단위를 자동 허용하지 않는다.

N-M + UNIT range reading is allowed only when the matched unit/counter/classifier/range noun is explicitly marked range-compatible in the unit registry or an equivalent registry-backed compatibility table. Missing metadata defaults to non-compatible. Future unit entries must declare this property explicitly.

N-M + UNIT range reading은 매칭된 unit/counter/classifier/range noun이 unit registry 또는 이에 준하는 registry-backed compatibility table에서 range-compatible로 명시된 경우에만 허용한다. metadata가 없으면 기본값은 non-compatible이다. 향후 추가되는 단위 항목은 이 속성을 명시해야 한다.

```text
1-2장 -> 일에서 이 장
3-4페이지 -> 삼에서 사 페이지
10-20개 -> 십에서 이십 개
2-3명 -> 이에서 삼 명
3-5분 -> 삼에서 오 분
1-2kg -> 일에서 이 킬로그램
1.5-2kg -> 일쩜오에서 이 킬로그램
0.5-1.0cm -> 영쩜오에서 일쩜영 센티미터
1,000.5-2,000.75원 -> 천쩜오에서 이천쩜칠오 원
2.0-1.5kg -> 이쩜영에서 일쩜오 킬로그램
1.50-2.00kg -> 일쩜오영에서 이쩜영영 킬로그램
0.05-0.10cm -> 영쩜영오에서 영쩜일영 센티미터
1–2kg -> 일에서 이 킬로그램
1.25–2.5kg -> 일쩜이오에서 이쩜오 킬로그램
1~2cm -> 일에서 이 센티미터
1.25~2.5kg -> 일쩜이오에서 이쩜오 킬로그램
1～2개 -> 일에서 이 개
1.25～2.5kg -> 일쩜이오에서 이쩜오 킬로그램
10-20% -> 십에서 이십 퍼센트
100-200원 -> 백에서 이백 원
1-2 장입니다 -> 일에서 이 장입니다
10-20 개는 -> 십에서 이십 개는
```

Tilde-like two-block numeric ranges are read with `에서` when both sides are
valid signed decimal-aware numeric blocks, even without a unit suffix. This
changes the older policy where arbitrary adjacent Korean noun tails blocked
tilde range reading. Each side may independently have `+` or `-`, valid
thousands comma grouping in the integer part, and decimal fractions. The
tilde-like delimiters are exactly `~`, `～`, `∼`, and `〜`. Optional inline
whitespace around the delimiter is allowed, but newline-crossing ranges are not.
A range-compatible unit/counter/classifier may still be consumed when present
and keeps its existing canonical reading. Arbitrary adjacent Korean noun tails
no longer block range reading; the range reading is followed by one generated
space before the original tail. Known particle/ending tails follow the existing
tail attachment behavior. Sentence punctuation after the right numeric block is
allowed and remains original punctuation. Signed range is not supported for `-`
or `–` delimiters, even though unsigned `N-M + UNIT` may use those delimiters.
Slash ratio remains out of scope. Left/right numeric ordering is not used to
decide claim. Existing unsigned generic/shared-suffix range precedence is
preserved.

```text
1~2 -> 일에서 이
+1.5~2 -> 플러스 일쩜오에서 이
+1.5~2 구간 -> 플러스 일쩜오에서 이 구간
+1.5~2테스트 -> 플러스 일쩜오에서 이 테스트
3.410~3.56범위 -> 삼쩜사일영에서 삼쩜오육 범위
3.410~3.56 범위 -> 삼쩜사일영에서 삼쩜오육 범위
-2.480~3.24 -> 마이너스 이쩜사팔영에서 삼쩜이사
-2.480~+3.24 -> 마이너스 이쩜사팔영에서 플러스 삼쩜이사
+2.480~-3.24 -> 플러스 이쩜사팔영에서 마이너스 삼쩜이사
0.05~0.10cm -> 영쩜영오에서 영쩜일영 센티미터
-1.22~+3.520테스트 -> 마이너스 일쩜이이에서 플러스 삼쩜오이영 테스트
+1,000.50~2,000.75테스트 -> 플러스 천쩜오영에서 이천쩜칠오 테스트
1 ~ 2 테스트 -> 일에서 이 테스트
1~2. -> 일에서 이.
1~2테스트 -> 일에서 이 테스트
1～2테스트 -> 일에서 이 테스트
1∼2테스트 -> 일에서 이 테스트
1〜2테스트 -> 일에서 이 테스트
-2.3~4.5kg이다 -> 마이너스 이쩜삼에서 사쩜오 킬로그램이다
2.3~-4.5kg -> 이쩜삼에서 마이너스 사쩜오 킬로그램
-2.3~-4.5kg -> 마이너스 이쩜삼에서 마이너스 사쩜오 킬로그램
-2~4kg -> 마이너스 이에서 사 킬로그램
2~-4kg -> 이에서 마이너스 사 킬로그램
-2~-4kg -> 마이너스 이에서 마이너스 사 킬로그램
-0.0~1.5cm -> 마이너스 영쩜영에서 일쩜오 센티미터
-1,000.50~2,000.75원 -> 마이너스 천쩜오영에서 이천쩜칠오 원
-2.3～4.5kg -> 마이너스 이쩜삼에서 사쩜오 킬로그램
-2.3∼4.5kg -> 마이너스 이쩜삼에서 사쩜오 킬로그램
-2.3〜4.5kg -> 마이너스 이쩜삼에서 사쩜오 킬로그램
-2.3-4.5kg -> -2.3-4.5kg
-2.3–4.5kg -> -2.3–4.5kg
+2.3~4.5kg -> 플러스 이쩜삼에서 사쩜오 킬로그램
2.3~+4.5kg -> 이쩜삼에서 플러스 사쩜오 킬로그램
+1.5-2kg -> +1.5-2kg
+1.5–2kg -> +1.5–2kg
```

Invalid numeric blocks, protected/code-like tokens, path/URL/email/backtick/code
fence/JSON-like internals, file-like/version-like tokens, and non-tilde
delimiters remain excluded. Invalid tilde-like numeric ranges preserve the whole
candidate and must not partially rewrite internal signed/decimal fragments.

```text
1-2테스트 -> 1-2테스트
1–2테스트 -> 1–2테스트
1~2테스트 -> 일에서 이 테스트
1～2테스트 -> 일에서 이 테스트
1.5-2 -> 1.5-2
1.5-2테스트 -> 1.5-2테스트
+01.5~2 -> +01.5~2
+1,00.5~2 -> +1,00.5~2
+.5~2 -> +.5~2
1.~2 -> 1.~2
3..140~4 -> 3..140~4
1~~2 -> 1~~2
01.5-2kg -> 01.5-2kg
1.-2kg -> 1.-2kg
.5-2kg -> .5-2kg
1,00.5-2kg -> 1,00.5-2kg
-1.5-2kg -> -1.5-2kg
v1-2 -> v1-2
v1.5-2 -> v1.5-2
v1~2 -> v1~2
file1~2.txt -> file1~2.txt
/path/1-2/log -> /path/1-2/log
/path/1.5-2kg/log -> /path/1.5-2kg/log
/path/1–2/log -> /path/1–2/log
/path/1~2/log -> /path/1~2/log
https://example.com?q=1~2 -> https://example.com?q=1~2
{"range":"1~2"} -> {"range":"1~2"}
`1-2` -> `1-2`
`1.5-2kg` -> `1.5-2kg`
`1~2` -> `1~2`
`1~2개` -> `1~2개`
```

Valid numeric surfaces may be claimed before adjacent Korean endings/particles or
sentence punctuation when the owner can safely full-consume the numeric core.
The Korean tail remains original text unless the owner has an explicit suffix
rule. Sentence punctuation is outside the claim surface. This applies to signed
temperature/unit/currency/percent/decimal surfaces and numeric-delimited range
or colon surfaces, while invalid numeric blocks and protected/code-like spans
remain preserve/fallback-block targets.

```text
+25℃였고 -> 영상 이십오도였고
-3℃였지만 -> 영하 삼도였지만
+1.5kg. -> 플러스 일쩜오 킬로그램.
+3.140℃. -> 영상 삼쩜일사영도.
3.140. -> 삼쩜일사영.
+25%. -> 플러스 이십오 퍼센트.
+1,000.50원. -> 플러스 천쩜오영 원.
```

`N:M` two-block colon-like form은 time owner가 먼저 판단한다. Time owner가
claim하지 않고, basic time-like shape로 보호되지 않으며, protected/code-like/
path/url/email/backtick context가 아니고 양쪽 block이 valid signed
decimal-aware numeric block이면 기본적으로 `read(N) + " 대 " + read(M)`로 읽는다.
따라서 기존 semantic-pair keyword gate는 여전히 positive context로 남지만,
더 이상 `N:M`을 읽기 위한 유일한 gate가 아니다.
Valid N:M 뒤에 공백 없이 일반 한글 tail이 붙으면 읽기 core 뒤에 한 칸을
생성하고 원문 tail을 이어준다. 조사/어미 tail은 기존 post-surface tail
attachment 정책을 따른다.

```text
1:2 -> 일 대 이
+1:2 -> 플러스 일 대 이
3:4 -> 삼 대 사
1.5:2.0 -> 일쩜오 대 이쩜영
1.50:2 -> 일쩜오영 대 이
-1:+2 -> 마이너스 일 대 플러스 이
1,000:2,000 -> 천 대 이천
+1,000.50:2 -> 플러스 천쩜오영 대 이
13:5 -> 십삼 대 오
25:30 -> 이십오 대 삼십
3:4테스트 -> 삼 대 사 테스트
+1:2테스트 -> 플러스 일 대 이 테스트
1.5:2.0범위 -> 일쩜오 대 이쩜영 범위
1,000:2,000테스트 -> 천 대 이천 테스트
3：4테스트 -> 삼 대 사 테스트
3:4. -> 삼 대 사.
3:4테스트. -> 삼 대 사 테스트.
3:15 -> 3:15
10:20 -> 10:20
+1:02 -> +1:02
```

Basic time-like shape는 `H:MM` 또는 `HH:MM`이고, minute block이 exactly two
digits이며 `00..59`, hour가 `00..24`인 경우다. 이 shape는 broad `대`
읽기보다 우선 보호된다. Time owner가 claim하려면 protected/code-like
context가 아니어야 하고, 기존 explicit time context gate가 필요하다. 허용
gate는 `오전/오후/AM/PM` prefix, `에/부터/까지/쯤/경` 후행 표지, 또는
surface에 좁게 인접한 schedule/time keyword(`회의`, `일정`, `시작`, `종료`,
`마감`, `출발`, `도착`, `예약`)다. `24:09`는 time-like/time 대상이고,
`25:30`은 explicit time context가 없으면 basic time-like가 아니다.

```text
09:30 -> 09:30
09:30에 시작 -> 아홉시 삼십분에 시작
13:05에 시작 -> 십삼시 오분에 시작
14:00부터 -> 십사시부터
24:00부터 -> 이십사시부터
24:09까지 -> 이십사시 구분까지
18:30까지 -> 십팔시 삼십분까지
오전 9:30 -> 오전 아홉시 삼십분
오후 3:15 -> 오후 세시 십오분
회의 14:00 -> 회의 십사시
마감 18:00 -> 마감 십팔시
```

### N:M semantic pair owner

Two-block colon-like N:M surfaces are claimed by the semantic pair owner under
explicit semantic-pair context gates or by the broad numeric colon rule above.
The semantic pair owner renders the surface as read(N) + " 대 " + read(M). It
does not distinguish ratio and score internally because both use the same
rendering.

The owner applies only to colon-like delimiter surfaces whose numeric blocks pass
the shared decimal-aware numeric block parser. It supports both unsigned integer
and unsigned decimal blocks, and it also supports optional leading plus/minus
signs under the same semantic-pair keyword gates.
Thousands comma grouping is allowed only when valid. Fractional digits are
preserved during rendering, including trailing zeros, and decimal output uses
the existing `쩜` canonical. The single digit `0`, `0.xxx`, `-0`, `-0.xxx`,
`+0`, and `+0.xxx`
are allowed, but leading-zero integer parts such as `01`, `001`, `01.5`,
`01,000.5`, `-01`, `-01.5`, `+01`, or `+01.5` are rejected before comma
validation.

Approved first-pass semantic-pair keywords are:

```text
비율, 화면비, 종횡비, 희석, 축척, 스코어, 점수, 승리, 패배, 무승부, 동점,
이겼다, 졌다, 비겼다, 완승, 압승, 역전승, 배율, 스케일, 전적, 세트,
경기, 게임, 매치
```

Semantic-pair keyword context is valid when the keyword immediately precedes
the N:M surface, immediately follows the N:M surface, or the N:M surface is
followed by `로`, `으로`, or `의` and then an approved keyword or verb. These
keywords are no longer the only claim path because broad non-time-like N:M also
uses the same `대` rendering. The particles `에`, `부터`, `까지`, `쯤`, and
`경` are not semantic-pair gates because they are time-like gates.

```text
1:2 비율 -> 일 대 이 비율
1.5:2 비율 -> 일쩜오 대 이 비율
1.5:2.0 비율 -> 일쩜오 대 이쩜영 비율
0.5:1 희석 -> 영쩜오 대 일 희석
1.25:100 축척 -> 일쩜이오 대 백 축척
1,000.5:2 비율 -> 천쩜오 대 이 비율
1:1,000,000.000 축척 -> 일 대 백만쩜영영영 축척
2.0:0.0 무승부 -> 이쩜영 대 영쩜영 무승부
3.50:1.25 경기 -> 삼쩜오영 대 일쩜이오 경기
1：2 비율 -> 일 대 이 비율
1.5：2 비율 -> 일쩜오 대 이 비율
-1.250:3.14 비율이다 -> 마이너스 일쩜이오영 대 삼쩜일사 비율이다
-1:2 비율 -> 마이너스 일 대 이 비율
1:-2 비율 -> 일 대 마이너스 이 비율
-1:-2 비율 -> 마이너스 일 대 마이너스 이 비율
-0.0:1 비율 -> 마이너스 영쩜영 대 일 비율
1.2:-2.30 경기 -> 일쩜이 대 마이너스 이쩜삼영 경기
-1,000.50:2 배율 -> 마이너스 천쩜오영 대 이 배율
+1:2 비율 -> 플러스 일 대 이 비율
1:+2 비율 -> 일 대 플러스 이 비율
+1.5:-2.0 경기 -> 플러스 일쩜오 대 마이너스 이쩜영 경기
+1,000.50:2 스케일 -> 플러스 천쩜오영 대 이 스케일
비율 1:2 -> 비율 일 대 이
16:9 화면비 -> 십육 대 구 화면비
1:100 희석 -> 일 대 백 희석
1:1,000,000 축척 -> 일 대 백만 축척
2:0으로 이겼다 -> 이 대 영으로 이겼다
3:1 승리 -> 삼 대 일 승리
0:0 무승부 -> 영 대 영 무승부
3:1의 스코어 -> 삼 대 일의 스코어
```

Time-like N:M remains protected from broad `대` reading unless time owner claims
it. The engine does not define a scripture owner in this phase and must not
inspect scripture book names. Scripture-like inputs that are also time-like
remain protected by the time-like rule; otherwise they may follow the broad
numeric colon rule. Two-block N:M duration/media handling remains out of scope.

Signed standalone N:M follows the same broad numeric colon rule. Invalid
signed numeric-delimited forms such as `+01:2 비율`, `+1.:2 비율`, `+.5:2 비율`,
`-01:2 비율`, `-1.:2 비율`, `-.5:2 비율`, and `-1,00.5:2 비율` must preserve the original
surface and must not partially rewrite internal numeric fragments.

Time owner precedence remains higher than semantic-pair owner. Leading-zero and time-like semantic-pair forms are not claimed by the semantic-pair owner.

```text
13:05에 시작 -> 십삼시 오분에 시작
13：05에 시작 -> 십삼시 오분에 시작
13：05 -> 13：05
1:05 비율 -> 1:05 비율
2:00 승리 -> 2:00 승리
요한복음 3:16 -> 요한복음 3:16
요한복음 3.5:16 -> 요한복음 삼쩜오 대 십육
line 10:20 -> line 10:20
line 10.5:20 -> line 10.5:20
영상 1:23 -> 영상 1:23
영상 1.5:2 -> 영상 1.5:2
재생시간 03:15 -> 재생시간 03:15
타임라인 00:03 -> 타임라인 00:03
1.5:2 -> 일쩜오 대 이
01.5:2 비율 -> 01.5:2 비율
1.:2 비율 -> 1.:2 비율
.5:2 비율 -> .5:2 비율
+1.5:2 -> 플러스 일쩜오 대 이
```

Two-block `N:M`은 duration/media owner로 claim하지 않는다. duration은 별도 owner의 더 엄격한 조건에서만 다룬다. Invalid time-like surface는 문장 전체가 아니라 해당 structured surface만 fallback-block/preserve 경계로 둔다.

### Multi-colon numeric "대" owner

Colon-like numeric surfaces with three to eight blocks may be claimed by the
multi-colon numeric owner. This owner reuses the signed decimal-aware numeric
block parser and renderer: comma grouping remains validation-only, decimal
output keeps the existing `쩜` canonical, trailing fractional zeros are
preserved, and a leading minus sign is rendered with the signed canonical
(`마이너스`). A leading plus sign is rendered as `플러스`. Invalid comma grouping,
invalid decimal forms, leading zero integer parts, and empty blocks are not
claimable.

The multi-colon owner uses `COLON_LIKE_DELIMITERS` scanner-locally, so ASCII
colon `:` and full-width colon `：` are equivalent for all-full-width and mixed
delimiter surfaces. Each block independently accepts the signed decimal-aware
numeric sign (`+` or `-`) when the surface is otherwise claimable. Protected
code/path/version contexts remain higher priority, but a protected or
hyphenated English token must not extend across whitespace and overprotect an
independent multi-colon numeric surface.

Three-block `A:B:C` surfaces preserve the higher-priority time/duration/media
decision path. If a three-block surface has an H:MM:SS-like or HH:MM:SS-like
shape, including `H:MM:SS.xxx`, the multi-colon owner must not read it as `대`.
When the surface is not timecode-like and all three blocks are valid signed
decimal-aware numeric blocks, it is rendered as `read(A) + " 대 " + read(B) +
" 대 " + read(C)`.

```text
1:2:3 -> 일 대 이 대 삼
1.2:2.3:3.4 -> 일쩜이 대 이쩜삼 대 삼쩜사
-1:2:-3 -> 마이너스 일 대 이 대 마이너스 삼
+1:2:3 -> 플러스 일 대 이 대 삼
+1.2:2.3:+3.0 -> 플러스 일쩜이 대 이쩜삼 대 플러스 삼쩜영
1,000:2,000:3,000 -> 천 대 이천 대 삼천
1.250:2.00:3.5 -> 일쩜이오영 대 이쩜영영 대 삼쩜오
1：2：3 -> 일 대 이 대 삼
1:2：3 -> 일 대 이 대 삼
+1：2：3：4 -> 플러스 일 대 이 대 삼 대 사
+1:2：3:4 -> 플러스 일 대 이 대 삼 대 사

1:02:03 -> 1:02:03
01:02:03 -> 01:02:03
1:02:03.5 -> 1:02:03.5
오전 1:02:03 -> 오전 1:02:03
영상 1:02:03 -> 영상 1:02:03
1:02:03 비율 -> 1:02:03 비율
+1:02:03 -> +1:02:03
요한복음 1:2:3 -> 요한복음 1:2:3
```

Four-to-eight-block colon numeric surfaces are not treated as time/duration/media
candidates by this owner. If every block is a valid signed decimal-aware numeric
block, the rendered block readings are joined with `대` without a keyword gate.
Nine-or-more blocks remain unclaimed with numeric fallback blocked.

```text
1:2:3:4 -> 일 대 이 대 삼 대 사
1:2:3:4:5 -> 일 대 이 대 삼 대 사 대 오
1:2:3:4:5:6:7:8 -> 일 대 이 대 삼 대 사 대 오 대 육 대 칠 대 팔
-1.2:2.3:-3:4 -> 마이너스 일쩜이 대 이쩜삼 대 마이너스 삼 대 사
1:+2:-3:4 -> 일 대 플러스 이 대 마이너스 삼 대 사
1,000:2,000:3,000:4,000 -> 천 대 이천 대 삼천 대 사천
1.250:2.00:3.5:4 -> 일쩜이오영 대 이쩜영영 대 삼쩜오 대 사
1：2：3：4 -> 일 대 이 대 삼 대 사

1:2:3:4:5:6:7:8:9 -> 1:2:3:4:5:6:7:8:9
01:2:3 -> 01:2:3
+01:2:3 -> +01:2:3
1:+2.:3 -> 1:+2.:3
1:2.:3 -> 1:2.:3
1:.2:3 -> 1:.2:3
1,00:2:3 -> 1,00:2:3
1:2:03:4 -> 1:2:03:4
```

Protected/code-like/path/version contexts remain higher priority. Multi-colon
surfaces that are not claimed, including timecode-like, invalid, context-blocked,
and 9+ block surfaces, must block internal numeric fallback so partial rewrites
such as `일:이:삼`, `일:영이:영삼`, or `마이너스 일쩜이:삼:사` do not appear.

Out of scope: scripture owner, slash ratio, Korean `대` delimiter,
duration/media expansion beyond existing owner behavior, and 9+ block reading.

### 0.0.6 사용자-visible 대괄호 삽입 금지

비한국어 preserve gate는 기존 square bracket protection과 같은 “re-entry 금지 preserve boundary” 원칙을 따른다. 그러나 구현은 사용자-visible 대괄호 `[` `]`를 실제 입력에 삽입하지 않는다.

시스템 preserve boundary는 내부 classification, preserve segment, preserve claim, trace metadata 등으로 표현한다. 이 marker는 최종 출력에 노출되지 않아야 하며, 사용자 입력의 실제 square bracket 정책과 충돌하지 않아야 한다.

금지 구현:

```text
[The temperature is 25℃.]
```

위처럼 시스템이 임의로 visible bracket을 삽입하면 nested bracket, final unwrap, source map, bracket 내부 parser re-entry 금지 정책과 충돌할 수 있으므로 금지한다.

### 0.0.7 All-Korean-lines fast path

입력 전체에 한글이 포함되어 있고, 모든 non-empty line이 Korean-eligible line이면 line-level transform을 하지 않고 기존 core transform을 한 번만 실행한다.

목적:

1. 기존 previous baseline/current policy 한국어 장문 결과 보호
2. prosody/comma/paragraph 처리 회귀 방지
3. line split/join 부작용 방지

line-level mixed gate는 입력에 한글 line과 no-Hangul line이 함께 있을 때만 적용한다.

### 0.0.8 Owner-local Symbol Alias Expansion

현재 정책은 기존 의미를 변경하지 않고 같은 의미의 입력 기호만 owner-local alias로 확장한다. 이 정책은 전역 Unicode normalization 또는 전역 문자열 치환을 허용하지 않는다.

Symbol alias 구현 계약:

1. alias는 각 owner 또는 matcher 내부 local constant로 정의한다.
2. 전역 `str.replace`, NFKC/NFC normalize, 전역 alias table 기반 선치환은 금지한다.
3. source span은 원문 기호를 유지한다.
4. render reading만 기존 owner 의미에 맞춰 생성한다.
5. URL, email, file path, JSON, shell, code-like preserve가 alias owner보다 우선한다.
6. unsafe tail preserve, full consume, no partial rewrite 원칙은 그대로 유지한다.

#### Slash alias

`/`와 `／`는 동일한 slash 의미로 owner-local 확장한다.

적용:

```text
1／3 -> 삼분의 일
15.2km／L -> 리터당 십오쩜이 킬로미터
90km／h -> 시속 구십 킬로미터
2025／01／03 -> 이천이십오년 일월 삼일
```

`⁄`와 `∕`는 fraction owner에 한정하여 적용한다.

```text
1⁄3 -> 삼분의 일
1∕3 -> 삼분의 일
```

Compound unit, path, URL owner에는 `⁄`, `∕`를 일괄 적용하지 않는다.

#### Percent alias

`%`, `％`, `﹪`는 percent 및 percent-point owner-local alias로 적용한다.

```text
33.3％ -> 삼십삼쩜삼 퍼센트
2.5％p -> 이쩜오 퍼센트포인트
2.5﹪p -> 이쩜오 퍼센트포인트
```

unsafe tail은 preserve한다.

```text
2.5％pa -> 2.5％pa
2.5﹪point -> 2.5﹪point
```

#### Colon alias

`:`와 `：`는 time owner에서 동일 의미로 처리한다. Semantic pair owner는 ASCII colon `:`만 대상으로 하며, full-width colon score/ratio는 기존 ambiguity 정책을 유지한다.

```text
13：05 -> 십삼시 오분
3：2 승 -> 기존 score/ratio ambiguity 정책 유지
```

#### Range tilde alias

`~`, `∼`, `～`, `〜`는 range owner에서 동일 의미로 처리한다.

```text
3~8cm -> 삼에서 팔 센티미터
3∼8cm -> 삼에서 팔 센티미터
3～8cm -> 삼에서 팔 센티미터
3〜8cm -> 삼에서 팔 센티미터
```

날짜/시간 shared suffix range는 현재 정책에서 양쪽 숫자에 suffix reading을 적용한다.

```text
1∼11월 -> 일월에서 십일월
1～11월 -> 일월에서 십일월
1〜11월 -> 일월에서 십일월
2~5시 -> 이시에서 오시
10~30분 -> 십분에서 삼십분
```

비날짜/비시간 physical unit range는 기존 shared-suffix range를 유지한다.

```text
3~8cm -> 삼에서 팔 센티미터
3~5km -> 삼에서 오 킬로미터
```

#### Minus sign alias

`-`, `−`, `－`는 signed number, signed temperature, signed percent-point, signed slash fraction owner-local alias로 적용한다.

```text
−2.5℃ -> 영하 이쩜오도
－2.5℉ -> 화씨 영하 이쩜오도
−2.5%p -> 마이너스 이쩜오 퍼센트포인트
−1/3 -> 마이너스 삼분의 일
```

`–`, `—`, `‑` 등 dash-like punctuation은 현재 정책에서 minus alias로 적용하지 않는다.

#### Temperature degree alias

온도 owner는 기존 `℃`, `℉`, `º`, `ºC`, `ºF`에 더해 다음 alias를 허용한다.

```text
25°C -> 이십오도
25° C -> 이십오도
25º C -> 이십오도
25°F -> 화씨 이십오도
25° F -> 화씨 이십오도
25º F -> 화씨 이십오도
-2.5°F -> 화씨 영하 이쩜오도
```

Celsius는 “섭씨”를 붙이지 않고 기존 정책처럼 “도”로 읽는다.

#### Temperature context de-duplication

Temperature context de-duplication is a renderer-local correction, not a change
to signed temperature canonical. If an adjacent Korean temperature label appears
immediately before a matching signed temperature symbol surface, the symbol
owner must not render the same unit label again.

The first-pass context window is intentionally narrow: optional ASCII spaces may
appear between the label and the signed temperature surface, but distant
sentence context is not used. Protected/code-like/path/backtick/JSON-like spans
remain preserve-first.

```text
77°F -> 화씨 영상 칠십칠도
25°C -> 영상 이십오도

화씨 +77°F -> 화씨 영상 칠십칠도
화씨 -77°F -> 화씨 영하 칠십칠도
화씨 +77℉ -> 화씨 영상 칠십칠도
화씨 -77℉ -> 화씨 영하 칠십칠도
화씨 +1.5°F -> 화씨 영상 일쩜오도
화씨 -0.0°F -> 화씨 영하 영쩜영도

섭씨 +25°C -> 섭씨 영상 이십오도
섭씨 -25°C -> 섭씨 영하 이십오도
섭씨 +25℃ -> 섭씨 영상 이십오도
섭씨 -25℃ -> 섭씨 영하 이십오도
섭씨 +1.5°C -> 섭씨 영상 일쩜오도
섭씨 -0.0°C -> 섭씨 영하 영쩜영도
```

Mismatch correction is out of scope. If the adjacent Korean label and the symbol
unit disagree, current owner behavior is preserved rather than corrected.

#### Compatibility unit symbol alias

다음 호환 단위 기호는 기존 의미와 동일하게 owner-local alias로 허용한다.

Area/volume:

```text
㎠ -> 제곱센티미터
㎢ -> 제곱킬로미터
㎤ -> 세제곱센티미터
㎦ -> 세제곱킬로미터
```

Length/mass:

```text
㎝ -> 센티미터
㎜ -> 밀리미터
㎏ -> 킬로그램
㎎ -> 밀리그램
```

Frequency:

```text
㎐ -> 헤르츠
㎒ -> 메가헤르츠
㎓ -> 기가헤르츠
```

예:

```text
45㎠ -> 사십오 제곱센티미터
3㎏ -> 삼 킬로그램
60㎐ -> 육십 헤르츠
3.2㎒ -> 삼쩜이 메가헤르츠
3.2㎓ -> 삼쩜이 기가헤르츠
```

#### Compound slash unit alias

기존 compound unit owner는 slash `／` alias를 동일하게 허용한다.

```text
90km／h -> 시속 구십 킬로미터
90㎞／h -> 시속 구십 킬로미터
5m／s -> 초속 오 미터
5㎝／s -> 초속 오 센티미터
15.2km／L -> 리터당 십오쩜이 킬로미터
15.2㎞／ℓ -> 리터당 십오쩜이 킬로미터
5㎎／L -> 리터당 오 밀리그램
12.5MB／s -> 초당 십이쩜오 메가바이트
3.2GB／s -> 초당 삼쩜이 기가바이트
```

#### Currency symbol alias

Dollar owner는 `$`, `＄`, `﹩`를 동일한 달러 기호로 처리한다.

```text
＄25.99 -> 이십오쩜구구 달러
﹩25.99 -> 이십오쩜구구 달러
```

Yen/won/euro 기존 정책은 유지한다.

### 0.0.9 현재 정책에서 의도적으로 제외하는 alias / normalization

다음은 현재 정책에서 적용하지 않는다.

1. 전역 Unicode normalization
2. fullwidth Latin/digit 전체 normalization
3. `–`, `—`, `‑`를 minus/range/hyphen에 일괄 적용
4. `．`, `，` decimal/comma alias
5. `・`, `･`, `ㆍ` middle-dot alias
6. `㌔`, `㍑` Japanese compatibility unit aliases
7. `㎾h`, `㎾·h` kWh alias
8. `円` currency alias
9. `㎑` kHz alias

위 항목은 필요하면 future/review phase에서 별도 정책으로 다룬다.

### 0.0.10 Unicode normalization 보류

current policy 구현은 원문 codepoint 기준 `[가-힣]` 한글 음절만 Korean eligibility로 본다. NFC/NFKC normalization sandbox, NFD Hangul Jamo 재조합, fullwidth ASCII 전역 정규화는 현재 정책에 포함하지 않는다.

NFD Hangul 또는 Hangul Jamo block 기반 Korean eligibility는 future/review 항목이다.

### 0.0.11 구현 파일 범위와 금지 구현

권장 구현 파일:

```text
engine/span_engine/language_gate.py
engine/span_engine/transform.py
```

가능하면 기존 owner/parser/render 파일은 수정하지 않는다. 특히 다음 파일은 Korean Eligibility 구현을 위해 직접 수정하지 않는 것을 원칙으로 한다.

```text
engine/span_engine/currency.py
engine/span_engine/units.py
engine/span_engine/date_time.py
engine/span_engine/parser.py
engine/span_engine/claim_scanner.py
```

Symbol alias 구현은 필요한 owner-local matcher에 한정해 최소 수정할 수 있다. 이 경우에도 전역 normalization이나 broad fallback은 금지한다.

`transform.py` 구현 계약:

1. 기존 transform 본체를 `_transform_core()` 같은 내부 함수로 분리할 수 있다.
2. public `transform()`은 language gate를 적용한 뒤 eligible segment에만 `_transform_core()`를 호출한다.
3. preserve segment는 `_transform_core()`에 넣지 않는다.
4. line-level gate에서 무한 재귀가 발생하지 않아야 한다.
5. Phase 34C no-crash fallback invariant는 유지한다.

금지 구현:

1. `if no_hangul: return text` 단순 guard
2. 사용자-visible bracket 삽입
3. 전역 Unicode normalization
4. 전역 string replace alias
5. URL/path/code 내부 partial rewrite
6. all-Korean-lines input을 line별로 강제 transform
7. preserve line의 공백/문장부호 변경

### 0.0.12 current policy 필수 테스트 계약

current policy 구현은 최소 다음 테스트를 포함해야 한다.

Policy/document tests:

1. `TTS_Preprocessor_policy_current policy.md` 존재
2. canonical policy 문구 존재
3. `current policy_changelog`는 참고용이며 구현 기준이 아니라는 문구 존재
4. Global no-Hangul bypass 문구 존재
5. Standalone supported token exception 문구 존재
6. Numeric-list line exception 문구 존재
7. Code-like preserve 우선 문구 존재
8. Owner-local alias와 전역 normalization 금지 문구 존재
9. 사용자-visible bracket 삽입 금지 문구 존재

Global bypass tests:

```text
The temperature is 25℃. -> same
The price is $25.99. -> same
pH 7.4 was maintained for 3 hours. -> same
The ratio is 1/3 and the change is 2.5%p. -> same
```

Standalone token tests:

```text
25℃ -> 이십오도
$25.99 -> 이십오쩜구구 달러
1/3 -> 삼분의 일
2.5%p -> 이쩜오 퍼센트포인트
45m² -> 사십오 제곱미터
pH 7.4 -> 피에이치 칠쩜사
60Hz -> 육십 헤르츠
3시간 18분 -> 세 시간 십팔분
```

Korean mixed sentence tests:

```text
오늘 온도는 25℃입니다. -> 오늘 온도는 이십오도입니다.
가격은 $25.99로 표시됐다. -> 가격은 이십오쩜구구 달러로 표시됐다.
pH 7.4 조건에서 실험했다. -> 피에이치 칠쩜사 조건에서 실험했다.
경기 시간은 3시간 18분이었다. -> 경기 시간은 세 시간 십팔분이었다.
```

Numeric-list line tests:

```text
오늘 관측값입니다.
25℃, 3시간 18분, 2.5%p, 1/3, 45m², $25.99
이상입니다.
```

Expected:

```text
오늘 관측값입니다.
이십오도, 세 시간 십팔분, 이쩜오 퍼센트포인트, 삼분의 일, 사십오 제곱미터, 이십오쩜구구 달러
이상입니다.
```

Preserve priority tests:

```text
오늘 원문 인용입니다.
The temperature is 25℃ and pH 7.4.
이상입니다.
```

Expected:

```text
오늘 원문 인용입니다.
The temperature is 25℃ and pH 7.4.
이상입니다.
```

Code-like exact preservation tests:

```text
curl -X POST http://localhost:8010/api/transform
{"text":"25℃"}
https://example.com/a?x=1
test@example.com
/home/user/file.txt
const value = "$25.99";
```

각각 exact preserve해야 한다.

Symbol alias tests:

```text
1／3 -> 삼분의 일
1⁄3 -> 삼분의 일
1∕3 -> 삼분의 일
2.5％p -> 이쩜오 퍼센트포인트
13：05 -> 십삼시 오분
3～8cm -> 삼에서 팔 센티미터
1∼11월 -> 일월에서 십일월
−2.5℃ -> 영하 이쩜오도
25°C -> 이십오도
45㎠ -> 사십오 제곱센티미터
3㎏ -> 삼 킬로그램
60㎐ -> 육십 헤르츠
90km／h -> 시속 구십 킬로미터
＄25.99 -> 이십오쩜구구 달러
```

Regression tests:

1. 장문·duration·fallback 회귀 tests 유지
2. previous baseline owner/claim/gate tests 유지
3. no-crash fallback tests 유지
4. preserve line exact match tests 추가
5. all-Korean-lines fast path가 기존 장문 결과를 바꾸지 않는지 확인

---

## 0.1 previous baseline 기반 정책의 current policy 유지 원칙

아래 본문은 previous baseline에서 구현된 core policy를 canonical 문서에 통합한 것이다. 현재 정책은 이 core policy를 폐기하지 않는다. 다만 위의 Korean Eligibility Gate와 Symbol Alias 정책이 기존 owner 실행 전 segment eligibility를 결정하며, eligible segment에 대해서만 아래 core policy가 적용된다.


새 시스템의 최상위 구조는 다음과 같다.

> 원본 입력을 span 단위로 보존하고, 변환 가능한 수치·기호 구간만 owner가 먼저 점유한 뒤, gate를 통과한 typed surface만 full consume 방식으로 발음화하며, 최종 render 후 shadow validation으로 원본 한글 literal·공백·문장부호·조사 보존을 검증하되, 명시된 Safe post-surface particle exception은 별도 provenance로 검증하는 TTS 전처리 파이프라인.

이 문서의 목적은 두 가지다.

1. 사람이 읽으면 전체 실행 흐름, 정책 의도, 안전장치, 우선순위를 이해할 수 있어야 한다.
2. codex가 읽으면 실행 순서, owner claim, gate 조건, fallback 위치, preserve 조건, render provenance, validation 기준을 구현 가능한 수준으로 해석할 수 있어야 한다.

본 문서의 최우선 정의는 다음이다.

- 한글 literal은 절대 변경하지 않는다.
- 사용자가 입력한 한글과 한글 사이 공백은 절대 변경하지 않는다.
- 사용자가 입력한 한글 뒤 punctuation은 절대 변경하지 않는다.
- 사용자가 입력한 조사는 기본적으로 생성, 수정, 교정, 치환, 삭제하지 않는다. 단, 본 문서의 `Safe Post-Surface Particle Exception`에 정의된 숫자/단위/영문/기호 surface 직후 Safe 조사군은 오독 방지를 위해 제한적으로 교정할 수 있다.
- 구조적 parser는 숫자, 기호, 외래어, 범위, 시간, 사건형 숫자, 단위, 긴급번호, 복합 토큰을 해석하기 위해 한글 주변 context를 읽을 수 있다.

이때 금지되는 것은 `literal rewrite`이고, 허용되는 것은 `context read + structured parse`다.

새 시스템은 “한글을 문자열 태그로 감싸서 보호하는 구조”가 아니다. 내부 표현은 object/span token, surface claim, render piece, shadow unit으로 구성한다. 문서 설명을 위해 `[[K:...]]` 같은 notation을 예시로 사용할 수는 있지만, 코드 내부 중간 문자열에 이런 태그를 삽입하는 구현은 금지한다.


## 0.1 출력 범위와 비목표

본 시스템의 출력은 **TTS 입력용 정규화 문자열**이다. 본 시스템은 사용자의 모든 입력 문장을 표준 한국어 발음으로 교정하는 범용 G2P 또는 표준 발음 전사기가 아니다.

따라서 다음을 비목표로 둔다.

- 한글 lexical token 내부의 오타 교정
- 한글 단어의 표준 맞춤법 교정
- 사용자가 입력한 모든 한글 문장의 표준 발음 전사
- 한글 어절 내부의 연음, 비음화, 유음화, 경음화, ㄴ첨가, 구개음화 전체 구현
- 한글 조사 일반 교정

한글로 입력된 문자는 오타가 있더라도 절대 보존하여 입력한 그대로 읽도록 한다. 한글 lexical token의 실제 표준 발음 처리는 downstream TTS/G2P 계층에 위임한다. 본 preprocessor가 직접 생성하는 것은 숫자, 단위, 통화, 약어, 기호, 범위, 날짜, 시간, 긴급번호, 사건형 숫자, 자모 기호 등 구조적 surface의 TTS 입력용 reading이다.

다만 숫자/단위/영문/기호 등 교정 처리대상 surface 바로 뒤에 붙은 일부 Safe 조사군은 오독 방지를 위해 제한적 예외 규칙으로 교정할 수 있다. 이 예외는 한글 일반 교정이 아니라 `owner가 확정된 generated surface 직후의 post-surface particle exception`이다.

### 0.1.1 OutputType

구현은 최소 다음 세 가지 출력을 구분한다.

```python
@dataclass
class TransformOutput:
    normalized_text: str
    render_pieces: list[RenderPiece]
    trace: TransformTrace | None = None
```

| 출력 | 의미 | 외부 노출 |
|---|---|---|
| `normalized_text` | TTS 엔진에 전달할 최종 정규화 문자열 | 기본 |
| `render_pieces` | provenance와 source span을 포함한 중간 출력 | debug/API optional |
| `trace` | claim/gate/parser/fallback/validation log | debug optional |

`normalized_text`는 표준 발음 전사가 아니라 TTS 입력용 읽기 문자열이다.

공개 API와 디버그 API는 다음처럼 분리한다.

```python
def transform(text: str) -> str:
    return transform_with_trace(text).normalized_text

def transform_with_trace(text: str) -> TransformOutput:
    ...
```

`transform()`은 기존 호환성을 위한 문자열 반환 API다. `transform_with_trace()`는 개발, 회귀 테스트, shadow validation, owner trace 확인을 위한 내부/debug API다.

### 0.1.2 경음화, 동화, 음의 첨가 비구현 원칙

본 preprocessor는 표준 발음법 전체를 구현하지 않는다. 한글 lexical token 내부 또는 한글 어절 경계의 연음, 비음화, 유음화, 경음화, ㄴ첨가, 구개음화 등은 downstream G2P/TTS에 위임한다.

단, 숫자·기호·단위·약어 reading을 생성할 때 필요한 제한적 smoothing은 generated surface 내부 또는 boundary-only 단계에서만 수행할 수 있다. 이 경우에도 `ORIGINAL_KOREAN`, `ORIGINAL_SPACE`, `ORIGINAL_PUNCT` piece는 수정하지 않는다.

### 0.1.3 Decimal Point Reading

소수점 reading은 TTS 자연성을 위해 기본값을 `쩜`으로 유지한다.

```text
7.4 -> 칠쩜사
1,234.56 -> 천이백삼십사쩜오육
```

`점`으로의 변경은 정책 기본값이 아니라 별도 runtime profile 또는 dictionary override로만 허용한다.

## 0. 최종 설계 목표

이 TTS 전처리 시스템의 목표는 단순 문자열 치환이 아니다. 목표는 다음 두 가지를 동시에 만족하는 것이다.

1. 사용자가 입력한 한글 literal, 한글 간 공백, 한글 뒤 punctuation을 절대 훼손하지 않는다. 입력 조사는 기본적으로 보존하되, 숫자/단위/영문/기호 등 owner가 확정된 generated surface 직후 Safe 조사군에 한해서만 제한적 예외 교정을 허용한다.
2. 숫자, 기호, 약어, 단위, 통화, 날짜, 시간, 범위, 긴급번호, 사건형 숫자, 복합 토큰은 문맥을 읽어 정확한 발음열로 변환한다.

새 시스템의 핵심 철학은 다음과 같다.

- Literal Rewrite 금지
- Context Read 허용
- Structured Transform만 허용
- Owner 없는 broad rewrite 금지
- Full Consume 원칙
- Ambiguous Preserve 원칙
- Non-Reentry 원칙
- Shadow Validation 강제
- Prosody Insert-only 원칙

기존 정책의 장점인 Zero-Loss 보호, Non-Reentry, Context Read, Boundary-only Smoothing, Shadow Validation 구상은 채택한다. 반면 위험했던 문자열 태그 직접 삽입, 조사 교정, broad heuristic, 기존 파이프라인 무시는 제거한다.

### 0.1 설계상 핵심 전환

기존 구현 또는 최초 개선안에서 흔히 떠올릴 수 있는 접근은 한글을 문자열 태그로 감싸 보호하고, 나머지 문자열을 parser가 처리한 뒤 태그를 제거하는 방식이다. 이 방식은 문서 설명용으로는 직관적이지만 운영 구현에는 적합하지 않다. 사용자가 태그와 유사한 문자열을 직접 입력할 수 있고, delimiter escaping이 복잡해지며, parser가 원문이 아닌 태그 문자열을 context로 읽게 되어 context-aware parsing이 약화된다.

따라서 새 구조의 핵심 전환은 다음이다.

| 과거 위험 접근 | 최종 설계 접근 |
|---|---|
| 문자열 태그 삽입 | object/span token |
| 원문 문자열 직접 rewrite | typed surface render |
| helper 중심 사후 보정 | owner-first claim + gate |
| 조사 처리 | original particle attach by default; Safe post-surface particle exception only |
| broad heuristic | explicit owner/gate |
| 결과 문자열만 검증 | RenderPiece provenance + Shadow Validation |
| parser 중복 진입 허용 | SurfaceClaimRegistry 기반 Non-Reentry |

### 0.2 성공 기준

새 시스템이 성공했다고 판단하려면 다음 조건을 모두 만족해야 한다.

- 입력 한글 literal이 render 후 `ORIGINAL_KOREAN` provenance로 동일하게 남아 있어야 한다.
- 입력 한글-한글 공백이 `ORIGINAL_SPACE` provenance로 동일하게 남아 있어야 한다.
- 입력 한글 뒤 punctuation이 `ORIGINAL_PUNCT` provenance로 동일하게 남아 있어야 한다.
- 입력 조사는 기본적으로 `ORIGINAL_KOREAN` provenance로 동일하게 attach되어야 한다. 단, 숫자/단위/영문/기호 등 교정 처리대상 surface 바로 뒤의 Safe 조사군은 별도 예외 규칙에 따라 교정된 조사도 `GENERATED_PARTICLE` provenance로 출력할 수 있다.
- generated Hangul reading은 원본 한글 검증 대상과 분리되어야 한다.
- owner가 점유한 span은 다른 owner가 재진입할 수 없어야 한다.
- gate 실패의 의미와 fallback 위치가 명확해야 한다.
- partial consume으로 raw residue를 남기면 안 된다.
- prosody는 insert-only여야 하며 protected surface 내부를 건드리면 안 된다.

## 1. Layer 1 — Invariance / Preservation Layer

이 Layer는 “무엇을 절대 바꾸면 안 되는가”를 정의한다. 이 Layer는 읽기보다 변경 금지에 집중한다.

### 1.1 Core Invariance Principle

시스템 전체에서 가장 높은 우선순위는 한글 보존이다. 다음 규칙은 모든 parser, 모든 helper, 모든 smoothing, 모든 typed surface 등록, 모든 render, 모든 prosody, 모든 paragraph split보다 우선한다.

- 사용자가 입력한 한글 문자열은 절대 변경하지 않는다.
- 사용자가 입력한 한글과 한글 사이 공백은 절대 변경하지 않는다.
- 사용자가 입력한 한글 바로 뒤에 공백 없이 붙은 쉼표는 절대 변경하지 않는다.
- 사용자가 입력한 한글 뒤 문장부호 `.`, `,`, `!`, `?`는 절대 변경하지 않는다.
- 사용자가 입력한 조사는 기본적으로 교정하지 않는다.
- 조사 생성, 조사 수정, 조사 치환, 조사 삭제를 하지 않는다.
- 단, `Safe Post-Surface Particle Exception`에 명시된 owner 확정 generated surface 직후 Safe 조사군은 제한적으로 교정할 수 있다.
- 이 원칙은 모든 parser, typed surface, 후처리, prosody 규칙보다 우선한다. Safe 조사 예외도 이 문서에 정의된 조건을 모두 만족할 때만 적용한다.

금지 예:

- `전문가 -> 전문이`
- `있는 -> 있은`
- `유로을 -> 유로를`
- `엔로 -> 엔으로`
- `배럴으로 -> 배럴로`
- `알으로 -> 알로`
- `종로3가 -> 종로삼이`
- `제4과 -> 제사와`
- `12로 나누다 -> 십이으로 나누다`
- `AI이 -> 에이아이가`
- `전문  가 -> 전문 가`

허용 예:

- `FTA는 -> 에프티에이는`
- `FTA은 -> 에프티에이는`
- `AI이 -> 에이아이이`

`FTA는`은 입력된 `는`이 그대로 attach된 결과다. `FTA은`은 Safe 조사 예외에 따라 `은/는` 쌍만 제한적으로 교정된 결과다. `AI이`는 Safe 조사군 `이`에 해당하지만 `가`는 Risky 조사군이므로 `이`를 그대로 유지한다.

### 1.2 Korean Text Immutability

- 한글 lexical token은 atomic literal이다.
- 한글 단어, 어간, 어미, 조사, 어절 내부 음절은 변형하지 않는다.
- 발음 기반 한글 교정, 형태 교정, lexical rewrite, morphology-like correction을 금지한다.
- 입력 조사 보존은 출력 품질보다 우선한다.
- 잘못 붙은 조사처럼 보여도 입력값이면 그대로 유지한다.

한글 literal은 context로 읽힐 수는 있지만 변환 대상이 아니다. 예를 들어 `21명`에서 `명`은 counter 판단을 위한 context로 읽을 수 있다. 그러나 `명` 자체를 다른 단어로 바꾸거나, 조사처럼 교정하거나, 공백 위치를 임의로 바꾸면 안 된다.

### 1.3 Spacing Preservation Policy

- 입력에 존재하는 한글과 한글 사이의 공백은 절대 보존한다.
- 공백 삽입, 공백 제거, 공백 위치 이동을 금지한다.
- 다중 공백도 그대로 유지한다.
- 숫자, 기호, 외래어 surface 내부에서 새 공백이 생성될 수는 있으나 기존 한글-한글 공백을 바꾸어서는 안 된다.

보존 예:

- `전문 가 -> 전문 가`
- `이 억 -> 이 억`
- `전문  가 -> 전문  가`
- `이  억 -> 이  억`

### 1.4 Punctuation Preservation Principle

- 한글 문자열 뒤에 붙어 있는 `.`, `,`, `!`, `?`는 절대 변경하지 않는다.
- 한글과 문장부호 사이의 기존 공백도 유지한다.
- 문장부호 제거, 이동, 교체, 문장부호 앞 공백 삽입을 금지한다.
- prosody는 insert-only 계층이므로 기존 문장부호를 덮어쓸 수 없다.

보존 예:

- `안녕하세요. -> 안녕하세요.`
- `안녕하세요, -> 안녕하세요,`
- `하지만, -> 하지만,`
- `있습니다, -> 있습니다,`
- `안녕하세요 , 반갑습니다 -> 안녕하세요 , 반갑습니다`

### 1.5 Particle Handling Policy

- 시스템은 조사를 생성하지 않는다.
- 시스템은 조사를 수정하지 않는다.
- 시스템은 조사를 기본적으로 교정하지 않는다. 단, `Safe Post-Surface Particle Exception`에 명시된 조사군은 제한적으로 교정할 수 있다.
- 시스템은 조사를 삭제하지 않는다.
- broad batchim detection 기반 조사 선택 로직은 사용하지 않는다. Safe 조사 예외는 owner가 확정된 generated surface 직후에만 적용한다.
- particle은 typed surface 외부에 attach되는 메타데이터로만 보관할 수 있다.
- attach는 입력 조사 자체를 그대로 재결합하는 동작만 허용한다.
- attach 가능한 surface에서도 입력 조사 외의 다른 조사로 치환하면 안 된다. 단, Safe 조사 예외가 명시적으로 통과한 경우에는 교정된 조사를 generated piece로 출력한다.

허용 예:

- `AI가 -> surface_text=에이아이, trailing_particle=가`
- `FTA는 -> surface_text=에프티에이, trailing_particle=는`
- `3~8cm는 -> surface_text=삼에서 팔 센티미터, trailing_particle=는`

금지 예:

- `AI이 -> 에이아이가`
- `FTA로 -> 에프티에이으로`
- `제4과 -> 제사와`
- `종로3가 -> 종로삼이`
- `MFN을 -> 엠에프엔를`

### 1.6 Generic String Rewrite Prohibition

이 항목은 generic string-level rewrite를 금지한다. 이 항목은 parser의 context read를 금지하는 규칙이 아니다.

금지 작업:

- 한글 literal을 대상으로 하는 replace 기반 후처리
- 조사 교정
- spacing repair
- morphology-like correction
- punctuation overwrite
- typed surface 생성 후 plain string fallback 재유입
- plain string helper가 한글 literal을 직접 수정하는 경로

허용 작업:

- 숫자 owner가 `명`, `개`, `월`, `일` 같은 counter 또는 suffix context를 읽는 것
- time owner가 `에`, `부터`, `까지`, `시작`, `회의` 같은 context를 읽는 것
- emergency owner가 `긴급번호`, `신고`, `화재` 같은 context를 읽는 것
- range owner가 단위 또는 shared suffix를 읽는 것

### 1.7 Literal Rewrite 금지와 Context Read 허용의 구분

이 Layer의 금지는 rewrite에만 적용된다.

- 금지: 한글 literal 변경
- 허용: 한글 주변 context 읽기
- 금지: 한글 literal을 string helper로 교정
- 허용: parser가 한글 주변 token을 보고 숫자, 기호, 외래어, 범위, 시간을 구조적으로 해석

이 구분은 이후 모든 Layer보다 우선한다.

## 2. 절대 채택하지 말아야 할 위험 설계

새 시스템은 최초 개선안의 장점은 흡수하되, 구현상 위험한 설계는 명시적으로 배제한다.

### 2.1 문자열 태그 직접 삽입 금지

다음과 같은 문자열 태그 방식은 실제 구현에 사용하지 않는다.

```text
[[K:한글]]
{{S:유형 | 원본 | 발음}}
[[B:기호]]
[S]
[P]
```

문자열 태그 방식은 다음 문제가 있다.

1. 사용자가 실제로 `[[K:...]]` 같은 문자열을 입력할 수 있다.
2. `[`, `]`, `{`, `}`, `:`, `|` 같은 delimiter escaping이 복잡해진다.
3. parser가 원문 대신 태그 문자열을 읽게 되어 context read가 어려워진다.
4. 태그 stripping 단계에서 원문 손상 가능성이 생긴다.
5. 디버깅은 쉬워 보이지만 운영 안정성이 낮다.

따라서 시스템 내부에서는 문자열 태그가 아니라 object/span token을 사용한다. 문서에서는 설명을 위해 `[[K:...]]` 같은 표현을 예시로 쓸 수 있지만, 코드에서는 절대 중간 문자열에 삽입하지 않는다.

### 2.2 Broad 조사 최적화 / 조사 교정 금지

다음 표현과 구현 방향은 제거한다.

- 음운 보정이 조사 결합 최종 수정을 수행한다.
- 수치 발음 자체를 조사에 최적화하여 조립한다.
- batchim detection 결과로 입력 조사를 바꾼다.
- surface reading에 맞춰 모든 조사 표면을 broad하게 재선택한다.

새 정책 문구는 다음이어야 한다.

- 음운 보정은 시스템 생성 surface 내부 또는 surface boundary에서만 허용한다.
- 사용자 입력 조사는 기본적으로 수정하지 않는다.
- `surface_text + original trailing_particle` 재결합이 기본이다.
- broad 조사 선택, 조사 교정, 조사 치환, 조사 삭제는 금지한다.
- 단, Safe post-surface particle exception에 명시된 `은/는`, `을/를`, `으로/로`, `이` 처리만 owner가 확정된 generated surface 직후에 제한적으로 허용한다. 이 예외는 broad 조사 교정이 아니다.

### 2.3 Broad Administrative Heuristic 금지

`숫자 + 가`, `숫자 + 호`, `숫자 + 동`, `숫자 + 로`, `숫자 + 길`을 넓게 주소로 처리하면 안 된다.

다음은 모두 다른 의미를 가질 수 있다.

- `종로3가`
- `3가 맞다`
- `21호`
- `21동`
- `12로 나누다`

따라서 행정 suffix는 broad heuristic이 아니라 명시 owner/gate로만 처리한다.

허용 조건:

- 좌측에 지명/주소 후보가 있어야 한다.
- 숫자와 행정 suffix가 full consume되어야 한다.
- suffix 뒤 boundary가 안전해야 한다.
- counter/particle 해석과 충돌하면 preserve 또는 기존 owner로 fallback한다.

### 2.4 기존 실행 순서 무시 금지

새 구조는 기존 실행 순서를 폐기하지 않는다. 기존 정책의 실행 단계는 다음 개념으로 재해석한다.

| 기존 개념 | 새 구조 |
|---|---|
| pre-rule cleanup/protection | immutable span tokenization + surface claim phase |
| dictionary/acronym protection | dictionary/acronym claim |
| RULE_PIPELINE | owner-first parse phase |
| restricted helper | restricted helper / boundary smoothing |
| post-rule surface promotion | typed surface generation 또는 late promotion |
| placeholder restore | render piece assembly |
| typed surface render | typed surface render |
| prosody comma | render piece 기반 insert-only prosody |
| paragraph split | render piece/string boundary 기반 conservative split |

Zero-Loss Encoding은 `SpanToken / Shadow Buffer / Lock Token`으로 흡수한다. Progressive Extraction은 `SurfaceClaimRegistry`로 흡수한다. Context-aware Gate는 `GateRegistry`로 흡수한다. Targeted Smoothing은 `Boundary-only Smoothing`으로 제한한다. Shadow Validation은 render 직후 강제한다.

## 3. 최종 아키텍처 개요

새 시스템은 다음 9개 계층으로 구성한다.

1. Layer 0. Raw Input & Source Map
2. Layer 1. Immutable Span Tokenization
3. Layer 2. Surface Claim / Non-Reentry Registry
4. Layer 3. Owner-first Gate Routing
5. Layer 4. Structured Parser / Typed Surface Generation
6. Layer 5. Restricted Helper / Boundary Smoothing
7. Layer 6. Typed Surface Render
8. Layer 7. Shadow Validation
9. Layer 8. Prosody / Paragraph Split

중요한 점은 탐지 순서와 발음 변환 순서를 분리한다는 것이다.

탐지 단계:

- 어떤 구간이 어떤 owner에게 속하는지 먼저 확정한다.
- 점유된 구간은 다른 parser가 재진입하지 못한다.
- Absolute Preserve claim은 재진입을 막는다. Owner Fallback Candidate는 preserve claim이 아니므로 다음 후보 owner 평가를 허용할 수 있다.
- 동일 구간에 여러 owner가 충돌하면 더 좁고 명시적인 owner가 우선한다.
- 동일 priority 충돌은 preserve가 기본이다.

변환 단계:

- owner가 확정된 surface만 structured parser가 읽는다.
- 필요한 gate를 통과해야 한다.
- full consume이 실패하면 preserve한다.
- raw residue를 남기면 안 된다.
- 한글 literal은 context로 읽을 수 있지만 rewrite할 수 없다.

### 3.1 전체 단계별 산출물

| 단계 | 입력 | 산출물 | 핵심 불변 조건 |
|---|---|---|---|
| Phase 0 | `raw_text` | `SourceChar[]`, source map | raw_text 수정 금지 |
| Phase 1 | source map | `SpanToken[]` | Korean/space/punct lock |
| Phase 2 | tokens | `ShadowUnit[]` | 원본 보존 대상 분리 |
| Phase 3 | tokens + shadow | `ClaimedRange[]`, surface candidates | owner-first, non-reentry |
| Phase 4 | claims | `GateDecision[]` | gate 실패 동작 명시 |
| Phase 5 | gated candidates | `Surface[]`, preserve pieces | full consume |
| Phase 6 | surfaces/pieces | stabilized surfaces/pieces | boundary-only smoothing |
| Phase 7 | surfaces/pieces | `RenderPiece[]` | provenance 유지 |
| Phase 8 | render pieces + shadow | validation result | 원본 훼손 차단 |
| Phase 9 | render pieces | comma/paragraph result | insert-only |

### 3.2 처리 흐름 pseudo-code

```python
def transform(raw_text: str) -> str:
    return transform_with_trace(raw_text).normalized_text

def transform_with_trace(raw_text: str) -> TransformOutput:
    source_chars = build_source_map(raw_text)
    tokens = tokenize_immutable_spans(raw_text, source_chars)
    tokens = protect_square_brackets_before_claim(tokens)
    shadow = build_shadow_buffer(tokens)

    claim_registry = SurfaceClaimRegistry()
    candidates = claim_surfaces(tokens, claim_registry)

    gate_results = evaluate_gates(candidates, tokens, claim_registry)
    parse_results = parse_gated_surfaces(gate_results, claim_registry)

    stabilized = apply_restricted_helpers(parse_results)
    pieces = render_to_pieces(stabilized, tokens)

    pieces = apply_safe_post_surface_particle_exception(pieces, claim_registry)

    validation = validate_shadow(pieces, shadow, claim_registry)
    if not validation.passed:
        return TransformOutput(
            normalized_text=raw_text,
            render_pieces=[RenderPiece(raw_text, "ORIGINAL_BOUNDARY", SourceSpan(0, len(raw_text)))],
            trace=build_trace(validation=validation),
        )

    pieces = insert_commas_insert_only(pieces)
    paragraph_result = split_paragraphs_conservative(pieces)
    final_text = apply_final_bracket_filter(paragraph_result)

    return TransformOutput(
        normalized_text=final_text,
        render_pieces=pieces,
        trace=build_trace(validation=validation),
    )
```

이 pseudo-code에서 가장 중요한 점은 다음이다.

- `Safe Post-Surface Particle Exception`은 render 직후, shadow validation 직전에 실행한다.
- `validate_shadow()`는 prosody 이전에 실행된다. prosody는 이미 보존 검증을 통과한 render piece stream에 insert-only로만 개입한다.
- `Final Bracket Filter`는 shadow validation 이후의 출력 shaping 단계다. `(...)` 삭제와 `[...]` unwrap은 validation failure로 보지 않는다.
- `transform()`은 공개 문자열 API이고, `transform_with_trace()`는 `TransformOutput`을 반환하는 debug/internal API다.

## 4. 핵심 데이터 모델## 4. 핵심 데이터 모델

### 4.1 SourceSpan

모든 token과 surface는 원본 입력에서의 위치를 가져야 한다.

```python
@dataclass(frozen=True)
class SourceSpan:
    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start
```

목적:

- 원본 한글 literal 보존 검증
- surface claim 충돌 감지
- shadow validation
- debug trace
- non-reentry enforcement
- fallback 시 원문 preserve

모든 span은 `raw_text` 기준 index를 사용한다. 중간 문자열이나 render string 기준 index를 사용하지 않는다.


### 4.1.1 SourceSpan Index 기준

`SourceSpan.start`와 `SourceSpan.end`는 Python `str`의 Unicode code point index를 기준으로 한다.

- UTF-8 byte offset이 아니다.
- grapheme cluster index가 아니다.
- JavaScript UTF-16 code unit index가 아니다.
- 외부 API에서 byte offset이 필요하면 `byte_start`, `byte_end`를 별도 optional field로 제공한다.

```python
@dataclass(frozen=True)
class SourceSpan:
    start: int  # Python str code point offset, inclusive
    end: int    # Python str code point offset, exclusive
```

결합 문자, emoji, zero-width char, 호환 자모가 포함된 입력도 원문 code point index를 기준으로 추적한다. Unicode normalization은 기본적으로 금지한다.

### 4.2 SourceChar

Phase 0에서 원문 문자 단위 source map을 만든다.

```python
@dataclass(frozen=True)
class SourceChar:
    char: str
    index: int
```

원칙:

- `raw_text`는 절대 수정하지 않는다.
- Unicode normalization은 기본적으로 하지 않는다.
- zero-width char, emoji, 특수기호도 원문 그대로 보존한다.
- Unicode normalization이 필요하다면 별도 owner가 있는 surface 내부에서만 수행하고, 원문 보존 mapping을 유지해야 한다.

### 4.3 SpanToken

문자열 태그 대신 내부 token object를 사용한다.

```python
@dataclass
class SpanToken:
    kind: Literal[
        "KOREAN_LITERAL",
        "SPACE_LOCK",
        "PUNCT_LOCK",
        "BOUNDARY_LITERAL",
        "PLAIN",
        "SURFACE",
    ]
    raw: str
    span: SourceSpan
    immutable: bool = False

    owner: str | None = None
    surface_type: str | None = None
    reading: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

| kind | 의미 | 수정 가능 여부 |
|---|---|---|
| `KOREAN_LITERAL` | 사용자가 입력한 한글 literal | 절대 수정 금지 |
| `SPACE_LOCK` | 한글-한글 사이 공백 또는 보호 대상 공백 | 절대 수정 금지 |
| `PUNCT_LOCK` | 한글 뒤 쉼표/문장부호 | 절대 수정 금지 |
| `BOUNDARY_LITERAL` | 사용자 입력 괄호, 특수기호 등 | owner 없으면 preserve |
| `PLAIN` | 아직 owner가 없는 일반 문자열 | 제한적 처리 가능 |
| `SURFACE` | typed surface | owner parser만 처리 가능 |

`KOREAN_LITERAL`, `SPACE_LOCK`, `PUNCT_LOCK`은 기본적으로 `immutable=True`다.

### 4.4 ShadowUnit

Shadow Validation을 위해 원본 보존 대상을 별도 저장한다.

```python
@dataclass(frozen=True)
class ShadowUnit:
    kind: Literal[
        "KOREAN_LITERAL",
        "KOREAN_SPACE",
        "KOREAN_PUNCT",
        "PARTICLE_LITERAL",
    ]
    raw: str
    span: SourceSpan
```

중요한 점은 출력의 모든 한글을 원본 한글과 비교하면 안 된다는 것이다. 숫자 변환 결과도 한글이기 때문이다.

예:

```text
입력: 21명
출력: 스물한 명
```

`스물한`은 generated Hangul이고, `명`은 original Korean literal이다. Shadow Validation은 이 둘을 구분해야 한다.

### 4.5 RenderPiece

최종 출력 직전의 조각 단위다.

```python
@dataclass
class RenderPiece:
    text: str
    provenance: Literal[
        "ORIGINAL_KOREAN",
        "ORIGINAL_SPACE",
        "ORIGINAL_PUNCT",
        "ORIGINAL_BOUNDARY",
        "GENERATED_READING",
        "GENERATED_PARTICLE",
        "GENERATED_PUNCT",
        "GENERATED_BOUNDARY",
        "SEPARATOR_CONSUMED",
    ]
    source_span: SourceSpan | None = None
    owner: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

Shadow Validation은 `ORIGINAL_*` provenance만 검사한다. 단, Safe 조사 예외로 소비된 원문 조사 span은 `PARTICLE_EXCEPTION_CONSUMED` trace로 검증하며, 교정된 조사는 `GENERATED_PARTICLE`로 출력한다. Prosody가 새로 삽입한 쉼표는 `GENERATED_PUNCT`로 출력한다.

### 4.6 Surface

기존 typed surface 개념을 유지하되, owner와 claim 정보를 더 강하게 갖는다.

```python
@dataclass
class Surface:
    surface_type: str
    owner: str
    raw: str
    span: SourceSpan
    reading: str | None = None
    render_pieces: list[RenderPiece] | None = None

    trailing_particle: str | None = None
    trailing_particle_span: SourceSpan | None = None

    protected: bool = True
    allow_reentry: bool = False
    allow_prosody_inside: bool = False

    metadata: dict[str, Any] = field(default_factory=dict)
```

원칙:

- `protected=True`인 surface 내부는 재분해 금지
- `allow_reentry=False`가 기본
- trailing particle은 원문 그대로 attach
- reading은 시스템 생성값이다. 단, surface 내부에 `ORIGINAL_KOREAN`과 `GENERATED_READING`이 섞이면 `reading` 단일 문자열만 반환하면 안 되고 `render_pieces`를 반드시 반환해야 한다.
- raw는 원본 보존용
- surface 내부에 prosody를 삽입하지 않는다.

현재 문서화 대상 surface type:

- `ACRONYM_SURFACE`
- `ALLOWED_ACRONYM_WITH_PARTICLE`
- `ACRONYM_WITH_LEXICAL_SUFFIX_SURFACE`
- `LEXICAL_MIDDLEDOT_SURFACE`
- `SINGLE_LETTER_HYPHEN_SURFACE`
- `DATE_SURFACE`
- `TIME_SURFACE`
- `CODE_SEPARATOR_BLOCK_SURFACE`
- `NUMERIC_PREFIXED_NOUN_SURFACE`
- `NUMERIC_UNIT_SURFACE`
- `NUMERIC_CURRENCY_SURFACE`
- `COUNTER_SURFACE`
- `RANGE_SURFACE`
- `RANGE_WITH_UNIT_SURFACE`
- `LARGE_UNIT_ATOMIC_SURFACE`
- `SIGNED_DEGREE_SURFACE`
- `SIGNED_TEMPERATURE_SURFACE`
- `JAMO_SURFACE`
- `EVENT_SURFACE`
- `ADMINISTRATIVE_SUFFIX_SURFACE`
- `DOTTED_DECIMAL_NUMERIC_SURFACE`
- `MIDDLE_DOT_NUMERIC_BLOCK_SURFACE`
- `MATH_NUMERIC_SURFACE`
- `PROTECTED_LITERAL_SURFACE`

Opaque surface 공통 금지:

- 내부 segmentation
- 내부 문자 rewrite
- particle correction
- punctuation 이동
- prosody 내부 삽입

### 4.7 ClaimedRange

Non-Reentry Registry의 핵심이다.

```python
@dataclass
class ClaimedRange:
    span: SourceSpan
    owner: str
    claim_type: Literal[
        "surface",
        "preserve",
        "gate_fail",
        "lock",
        "shadow",
    ]
    surface_type: str | None = None
    reason: str | None = None
    reentry_allowed: bool = False
```

사용 예:

```text
[12.3]
-> square bracket protection claim 등록
-> decimal/event parser 재진입 금지
-> 12.3 보존
```

### 4.7.1 SurfaceCandidate: core_span / attach_span 분리

claim registry가 한글 literal을 덮어쓰지 않도록, 변환 대상 span과 attach/context span을 분리한다.

```python
@dataclass
class SurfaceCandidate:
    core_span: SourceSpan
    full_span: SourceSpan
    owner: str
    surface_type: str | None = None
    trailing_particle_span: SourceSpan | None = None
    suffix_spans: list[SourceSpan] = field(default_factory=list)
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

규칙:

- `core_span`은 generated reading의 대상이 되는 숫자/영문/기호 구간이다.
- `full_span`은 core와 attach tail 또는 suffix를 포함하는 후보 전체 범위다.
- claim registry의 non-reentry claim은 기본적으로 `core_span`에 등록한다.
- `trailing_particle_span`은 attach metadata로만 보관하며, 원문 provenance를 유지한다.
- 한글 literal span을 generated reading으로 덮어쓰는 claim은 금지한다.
- `acronym_suffix`, `lexical_compound`, `administrative_suffix`처럼 한글 suffix가 surface body 일부로 포함되는 경우에는 parser가 반드시 piece별 provenance를 반환해야 한다.

예:

```text
21명 -> core_span=21, suffix/context=명, render=[GENERATED_READING("스물한"), ORIGINAL_KOREAN("명")]
FTA율 -> core_span=FTA, suffix_span=율, render=[GENERATED_READING("에프티에이"), ORIGINAL_KOREAN("율")]
종로3가 -> core_span=3, context/suffix=종로/가, render=[ORIGINAL_KOREAN("종로"), GENERATED_READING("삼"), ORIGINAL_KOREAN("가")]
```

### 4.8 SurfaceClaimRegistry

```python
class SurfaceClaimRegistry:
    def __init__(self):
        self.claims: list[ClaimedRange] = []

    def can_claim(self, span: SourceSpan, owner: str) -> bool:
        ...

    def claim(self, claim: ClaimedRange) -> None:
        ...

    def find_overlaps(self, span: SourceSpan) -> list[ClaimedRange]:
        ...

    def is_blocked(self, span: SourceSpan) -> bool:
        ...
```

규칙:

1. 기본 구현에서는 claim replacement를 지원하지 않는다.
2. `CLAIM_ORDER`는 높은 우선순위에서 낮은 우선순위로 실행된다.
3. 이미 등록된 `reentry_allowed=False` claim과 overlap하는 새 claim은 reject한다.
4. Absolute Preserve claim은 재진입을 막는다.
5. gate_fail claim은 정책상 필요한 경우만 재진입을 막는다.
6. 동일 priority 또는 해소 불가능한 overlap은 Terminal Fallback Preserve로 처리하거나, 필요한 경우 Absolute Preserve claim을 등록한다.
7. claim replacement는 향후 확장용이며 v1 구현 범위에서 제외한다.
8. lock/shadow overlap reject는 “한글 literal을 generated reading으로 덮어쓰는 claim”을 금지한다는 의미다. context read, suffix provenance 보존, trailing_particle attach metadata까지 금지하는 뜻이 아니다.

## 5. 전체 실행 흐름 요약

최종 실행 순서는 다음과 같다.

1. Raw Input 수신
2. Source Map 생성
3. Immutable Span Tokenization
4. Shadow Buffer 생성
5. Surface Claim Phase
6. Owner-first Gate Routing
7. Structured Parse Phase
8. Restricted Helper / Boundary Smoothing
9. Typed Surface Render
10. Shadow Validation
11. Prosody Insert-only
12. Paragraph Split
13. Final Bracket Filter
14. Final Output

기존 `normalize_text()` 중심 구현과 대응시키면 다음과 같다.

| 새 단계 | 기존 실행 흐름과의 대응 |
|---|---|
| Source Map | 입력 수신 직후 추가 |
| Immutable Span Tokenization | pre-rule cleanup/protection 이전의 안전 계층 |
| Shadow Buffer | 기존에는 명시 부족, 새 필수 계층 |
| Surface Claim Phase | pre-rule protection + dictionary/acronym + post promotion 후보 선점 |
| Gate Routing | RULE_PIPELINE 내부 조건을 registry화 |
| Structured Parse | RULE_PIPELINE + structured helper |
| Restricted Helper | 기존 restricted helper 유지, boundary-only로 축소 |
| Render | typed surface render 명시화 |
| Shadow Validation | render 직후 필수 검증 |
| Prosody | 기존 insert_commas, 단 RenderPiece 기반 권장 |
| Paragraph Split | 기존 split_paragraphs 유지 |
| Final Bracket Filter | `(...)` 삭제, `[...]` unwrap, bracket 삭제로 생긴 중복 공백 제한 정리 |

### 5.1 실패 전파 방식

각 단계는 실패를 조용히 삼키지 않는다. 실패는 다음 중 하나로 표현되어야 한다.

| 실패 위치 | 표현 | 다음 단계 동작 |
|---|---|---|
| tokenization | invalid span/token log | raw preserve 또는 token preserve |
| claim phase | Absolute Preserve claim 또는 Owner Fallback Candidate | Absolute Preserve는 재진입 차단, Owner Fallback Candidate는 다음 후보 owner 평가 |
| gate | GateDecision | action_on_fail에 따름 |
| parser | ParserResult failure | Terminal Fallback Preserve 또는 명시 fallback |
| helper | helper skip/failure log | 원본 또는 surface 유지 |
| render | render error | validation fail 처리 |
| validation | ValidationLog fail | 실패 span 또는 실패 segment preserve |
| prosody | insert candidate reject | 원문 유지 |

### 5.2 운영 기본값

운영 환경에서는 안전성을 우선한다.

- parser가 확신하지 못하면 preserve한다.
- full consume이 실패하면 preserve한다.
- validation 실패 시 기본 fallback은 실패 span 또는 실패 segment preserve다.
- 입력 전체 preserve는 no-Hangul global bypass 또는 전체 입력이 하나의 absolute preserve block인 경우에만 허용한다.
- owner collision이 해소되지 않으면 preserve한다.
- broad fallback으로 “그럴듯한” 출력을 만들지 않는다.

### 5.3 디버그 기본값

개발/디버그 환경에서는 보존 대신 원인 추적을 우선한다.

- validation fail 시 exception을 발생시킬 수 있다.
- owner trace를 출력한다.
- claim/gate/parser/fallback/validation log를 모두 저장한다.
- skip log와 collision log를 분리한다.

### 5.4 Fallback Status Taxonomy Clarification

`normalized_text`가 원문과 같더라도 trace/debug metadata에서는 가능한 한 다음 status를 구분한다.

- `absolute_preserve`
- `terminal_fallback_preserve`
- `validation_fallback_preserve`
- `exception_fallback_preserve`
- `policy_deferred_preserve`
- `transformed`
- `mixed_transformed_with_preserve`

CLI plain output은 기존 호환성을 위해 `normalized_text`만 출력할 수 있다. debug/API trace 경로에서는 `status`, `owner`, `reason`, `fallback_stage`를 기록하는 것이 권장된다. metric 집계에서는 `absolute_preserve`와 `exception_fallback_preserve`를 같은 상태로 합치면 안 된다.

## 6. Phase 0 — Raw Input & Source Map

### 6.1 목적

입력 문자열을 그대로 보관하고, 이후 모든 변환 조각이 원본 위치를 추적할 수 있게 한다.

### 6.2 산출물

```python
raw_text: str
source_chars: list[SourceChar]
```

### 6.3 원칙

- `raw_text`는 절대 수정하지 않는다.
- 모든 span은 `raw_text` 기준 index를 사용한다.
- Unicode normalization은 하지 않는다.
- zero-width char, emoji, 특수기호도 원문 그대로 보존한다.
- normalization이 필요하다면 별도 owner가 있는 surface 내부에서만 수행한다.
- 원문 보존 mapping이 없는 normalization은 금지한다.

### 6.4 Source Map 생성 pseudo-code

```python
def build_source_map(raw_text: str) -> list[SourceChar]:
    return [SourceChar(char=ch, index=i) for i, ch in enumerate(raw_text)]
```

Source Map은 변환용 데이터가 아니라 추적용 데이터다. Source Map을 만든 뒤에도 `raw_text` 자체를 수정하지 않는다.

### 6.5 Unicode normalization 정책

기본 정책은 Unicode normalization을 수행하지 않는 것이다. 예를 들어 full-width 기호, 특수 단위 기호, emoji, zero-width 문자 등은 원문 그대로 유지한다. 단위 parser나 currency parser가 특정 기호를 해석해야 한다면 해당 parser owner가 원문 span을 보유한 채 reading을 생성한다.

허용:

```text
㎡ -> special_unit owner -> 제곱미터
```

금지:

```text
raw_text 전체 Unicode normalization 후 span 기준 변경
```

### 6.6 실패 처리

Source Map 생성은 원칙적으로 실패하지 않아야 한다. 단, 입력이 비문자열이거나 내부 API에서 bytes/None이 전달되는 경우에는 transform 진입 이전에 type guard를 둔다.

권장 정책:

```python
def transform(input_value: Any) -> str:
    if not isinstance(input_value, str):
        raise TypeError("transform expects str")
```

## 7. Phase 1 — Immutable Span Tokenization

### 7.1 목적

한글 literal, 한글 간 공백, 한글 뒤 punctuation 등 절대 변경 금지 대상을 token으로 분리한다.

### 7.2 Korean Literal Token

연속된 `[가-힣]+`를 `KOREAN_LITERAL`로 만든다.

```text
전문가 유지
-> KOREAN_LITERAL("전문가")
-> SPACE_LOCK(" ")
-> KOREAN_LITERAL("유지")
```

주의:

- 한글을 token으로 분리한다는 것은 rewrite 금지를 의미한다.
- parser가 context로 읽는 것은 허용된다.
- 한글 token 자체를 surface reading으로 덮어쓰지 않는다.

### 7.3 Space Lock

다음 공백은 `SPACE_LOCK`이다.

- 한글과 한글 사이의 공백
- 한글 뒤 쉼표/문장부호 앞의 기존 공백
- 정책상 보존해야 하는 다중 공백

예:

```text
전문  가
-> KOREAN_LITERAL("전문")
-> SPACE_LOCK("  ")
-> KOREAN_LITERAL("가")
```

출력도 반드시 다음이어야 한다.

```text
전문  가
```

### 7.4 Punctuation Lock

한글 literal 바로 뒤에 붙은 다음 문장부호는 `PUNCT_LOCK`이다.

```text
. , ! ?
```

예:

```text
안녕하세요,
-> KOREAN_LITERAL("안녕하세요")
-> PUNCT_LOCK(",")
```

prosody는 이 쉼표를 제거하거나 이동할 수 없다.

### 7.5 Boundary Literal

사용자 입력 괄호, 대괄호, 중괄호, 특수기호는 문자열 태그로 escape하지 않고 `BOUNDARY_LITERAL`로 보관한다.

```text
[ ] ( ) { } : |
```

중요:

- 사용자가 입력한 `[[K:...]]` 같은 문자열도 그냥 사용자 문자열이다.
- 시스템 태그로 해석하지 않는다.
- boundary literal은 명시 owner가 없으면 preserve한다.

### 7.6 Tokenization pseudo-code

```python
def tokenize_immutable_spans(raw_text: str, source_chars: list[SourceChar]) -> list[SpanToken]:
    tokens: list[SpanToken] = []
    i = 0
    while i < len(raw_text):
        if is_hangul(raw_text[i]):
            start = i
            while i < len(raw_text) and is_hangul(raw_text[i]):
                i += 1
            tokens.append(SpanToken(
                kind="KOREAN_LITERAL",
                raw=raw_text[start:i],
                span=SourceSpan(start, i),
                immutable=True,
            ))
            continue

        if is_space(raw_text[i]):
            start = i
            while i < len(raw_text) and is_space(raw_text[i]):
                i += 1
            kind = classify_space_lock(raw_text, start, i)
            tokens.append(SpanToken(
                kind=kind,
                raw=raw_text[start:i],
                span=SourceSpan(start, i),
                immutable=(kind == "SPACE_LOCK"),
            ))
            continue

        if is_punctuation_lock_position(raw_text, i):
            tokens.append(SpanToken(
                kind="PUNCT_LOCK",
                raw=raw_text[i],
                span=SourceSpan(i, i + 1),
                immutable=True,
            ))
            i += 1
            continue

        start = i
        i += 1
        tokens.append(SpanToken(
            kind="PLAIN" if is_plain_char(raw_text[start]) else "BOUNDARY_LITERAL",
            raw=raw_text[start:i],
            span=SourceSpan(start, i),
        ))

    return merge_adjacent_plain_tokens(tokens)
```

### 7.7 Tokenization 검증

Tokenization 결과는 다음을 만족해야 한다.

- 모든 token span은 겹치지 않는다.
- 모든 token span은 raw_text 전체를 순서대로 cover한다.
- immutable token의 raw는 raw_text slice와 동일하다.
- `KOREAN_LITERAL`, `SPACE_LOCK`, `PUNCT_LOCK`은 이후 단계에서 text를 바꿀 수 없다.

검증 pseudo-code:

```python
def validate_token_coverage(raw_text: str, tokens: list[SpanToken]) -> None:
    cursor = 0
    for token in tokens:
        assert token.span.start == cursor
        assert raw_text[token.span.start:token.span.end] == token.raw
        cursor = token.span.end
    assert cursor == len(raw_text)
```


### 7.5 Hangul Range and Jamo Reading Policy

본 시스템은 한국어 대상 TTS 전처리기이므로 한글 입력 보존이 기본이다. 다만 완성형 한글 외에 단독 자모가 입력되는 경우, 자모 기호는 구조적 surface로 보아 표준 자모 명칭으로 읽을 수 있다.

#### 7.5.1 한글 범위 분류

| 범위 | 처리 |
|---|---|
| Hangul Syllables `U+AC00–U+D7A3` | `KOREAN_LITERAL`, 원문 보존 |
| Hangul Compatibility Jamo `U+3130–U+318F` | `JAMO_SURFACE` 후보, 표준 자모 명칭 reading 가능 |
| Hangul Jamo `U+1100–U+11FF` | 기본 preserve, 명시 mapping이 있으면 `JAMO_SURFACE` 가능 |
| Hangul Jamo Extended-A/B | 기본 preserve |
| 옛한글 조합 문자 | 기본 preserve |

#### 7.5.2 자모 reading 기본 목록

표준 자모 명칭을 기본값으로 사용한다. 추후 TTS 품질상 변경이 필요하면 이 목록을 수정하여 코드 구현으로 넘긴다.

| 입력 | reading |
|---|---|
| `ㄱ` | `기역` |
| `ㄲ` | `쌍기역` |
| `ㄴ` | `니은` |
| `ㄷ` | `디귿` |
| `ㄸ` | `쌍디귿` |
| `ㄹ` | `리을` |
| `ㅁ` | `미음` |
| `ㅂ` | `비읍` |
| `ㅃ` | `쌍비읍` |
| `ㅅ` | `시옷` |
| `ㅆ` | `쌍시옷` |
| `ㅇ` | `이응` |
| `ㅈ` | `지읒` |
| `ㅉ` | `쌍지읒` |
| `ㅊ` | `치읓` |
| `ㅋ` | `키읔` |
| `ㅌ` | `티읕` |
| `ㅍ` | `피읖` |
| `ㅎ` | `히읗` |
| `ㅏ` | `아` |
| `ㅐ` | `애` |
| `ㅑ` | `야` |
| `ㅒ` | `얘` |
| `ㅓ` | `어` |
| `ㅔ` | `에` |
| `ㅕ` | `여` |
| `ㅖ` | `예` |
| `ㅗ` | `오` |
| `ㅘ` | `와` |
| `ㅙ` | `왜` |
| `ㅚ` | `외` |
| `ㅛ` | `요` |
| `ㅜ` | `우` |
| `ㅝ` | `워` |
| `ㅞ` | `웨` |
| `ㅟ` | `위` |
| `ㅠ` | `유` |
| `ㅡ` | `으` |
| `ㅢ` | `의` |
| `ㅣ` | `이` |

#### 7.5.3 자모 변환 조건

- 단독 compatibility jamo는 `JAMO_SURFACE`로 변환할 수 있다.
- 연속 자모열은 각 자모를 공백으로 분리해 읽는다.
- 완성형 한글 음절은 자모 분해하지 않는다.
- 자모가 모델명, 코드, emoticon, placeholder의 일부로 보이면 preserve한다.
- 불명확하면 preserve한다.

예:

```text
ㄱ -> 기역
ㄱㄴㄷ -> 기역 니은 디귿
ㅏㅑㅓ -> 아 야 어
AㄱB -> preserve 또는 mixed token owner가 명시될 때만 처리
```


### 7.6 Bracket Handling Policy

괄호 처리는 이 시스템의 핵심 원칙에 따른 명시 예외다. 내부 처리 중에는 사용자가 입력한 괄호와 괄호 안 텍스트를 보존한다. 최종 출력 단계에서만 괄호 유형별로 다른 elision/protection 정책을 적용한다.

#### 7.6.1 Parentheses `(...)`

사용자가 입력한 `(...)` 괄호는 모든 normalization, render, validation이 끝난 후 최종 출력 단계에서 괄호와 괄호 안 텍스트를 모두 삭제한다.

원칙:

- 내부 처리 과정에서는 `(...)`와 내부 텍스트를 유지한다.
- parenthesis 내부 텍스트는 괄호 내부 surface를 처리할 때만 context로 사용할 수 있다.
- 괄호 바깥 surface의 gate/context 판단에는 parenthesis 내부 token을 사용하지 않는다.
- shadow validation은 최종 parenthesis elision 이전 render piece stream을 기준으로 수행한다.
- 최종 출력 단계에서 parenthesis elision을 적용한다.
- parenthesis 삭제로 인해 생긴 중복 공백만 제한적으로 1칸으로 정리한다.
- 원래 존재하던 한글-한글 `SPACE_LOCK` span은 절대 collapse하지 않는다.

위 제한은 다음 오동작을 막기 위한 것이다.

```text
회의는 13:05(시작)에 열린다
```

`시작`은 최종 출력에서 삭제되므로, `13:05`의 time gate를 통과시키는 근거로 사용하면 안 된다.

현재 large-unit 결정:

- parenthesis 내부 context는 괄호 바깥 time owner gate 근거로 사용할 수 없다.
- 단, parenthesis 외부 문맥이 time owner gate를 독립적으로 충족하면 time reading을 허용한다.
- `회의는 13:05(시작)에 열린다`에서 `시작`은 gate 근거가 아니지만, 외부 문맥 `회의는 ... 에 열린다`가 time owner gate를 충족한다.
- final parenthesis elision은 `(시작)`을 제거한다.

canonical:

```text
회의는 13:05(시작)에 열린다 -> 회의는 십삼시 오분에 열린다
13:05 -> 13:05
```

예:

```text
입력: 비용은 (약) 3만원입니다
중간 render: 비용은 (약) 삼만 원입니다
최종 출력: 비용은 삼만 원입니다
```

#### 7.6.2 Square Brackets `[...]`

사용자가 입력한 `[...]` 괄호는 입력한 그대로 보호하여 출력하기 위한 용도다.

원칙:

- square bracket protection은 Phase 1 tokenization 직후, Surface Claim Phase 시작 전에 수행한다.
- well-formed outermost `[...]` 구간 전체를 `PROTECTED_LITERAL_SURFACE`로 claim한다.
- 이 claim은 `reentry_allowed=False`이며 내부 token은 parser scan 대상에서 제외한다.
- `[...]` 내부는 normalization 대상에서 제외한다.
- 내부 숫자, 단위, 영문, 기호도 변환하지 않는다.
- 최종 bracket filter에서는 해당 surface의 raw 내부 텍스트만 출력하고 `[`, `]` 기호만 삭제한다.
- 내부 텍스트와 내부 공백은 입력한 그대로 출력한다.

예:

```text
입력: 가격은 [3kg]입니다
출력: 가격은 3kg입니다
```

이 예시에서 `3kg`는 unit parser로 들어가면 안 된다.

#### 7.6.3 중첩 괄호

중첩 괄호는 가장 바깥쪽 괄호 기준으로 판단한다.

```text
(...[...]) -> 바깥쪽이 (...) 이므로 전체 삭제
[...(...)...] -> 바깥쪽이 [...] 이므로 내부 전체를 그대로 출력하고 [ ]만 삭제
```

예:

```text
입력: 문장(임시[확인])입니다
최종 출력: 문장입니다

입력: 가격은 [3kg(확인)]입니다
최종 출력: 가격은 3kg(확인)입니다
```

불완전 괄호는 그대로 보존하여 출력한다.

```text
입력: 문장(임시 입니다
출력: 문장(임시 입니다

입력: 가격은 [3kg입니다
출력: 가격은 [3kg입니다
```

#### 7.6.4 Final Bracket Filter 공백 정리

Final Bracket Filter 후 공백 정리는 다음 경우에만 적용한다.

1. 삭제된 parenthesis span의 직전 출력 조각과 직후 출력 조각 사이에 공백이 2개 이상 새로 인접한 경우
2. 그 공백들이 parenthesis 삭제 boundary에서 새로 만난 경우
3. 원래 raw_text에서 존재하던 한글-한글 `SPACE_LOCK` span이 아닌 경우

예:

```text
문장 (임시) 입니다 -> 문장 입니다
문장  (임시)  입니다 -> 문장 입니다
전문  가(임시) 유지 -> 전문  가 유지
```

#### 7.6.5 Bracket Filter와 Shadow Validation의 관계

- Shadow Validation은 bracket filter 이전에 수행한다.
- Final Bracket Filter는 `ORIGINAL_BOUNDARY` piece 중 bracket delimiter만 삭제할 수 있다.
- Square bracket 내부의 `ORIGINAL_KOREAN`, `ORIGINAL_SPACE`, `ORIGINAL_PUNCT`는 삭제하거나 수정하면 안 된다.
- Parenthesis filter는 parenthesis span 내부의 모든 piece를 삭제할 수 있는 명시 예외다.

## 8. Phase 2## 8. Phase 2 — Shadow Buffer 생성

### 8.1 목적

최종 출력에서 원본 보존 대상이 훼손되지 않았는지 검사하기 위한 기준 데이터를 만든다.

### 8.2 Shadow 대상

- 원본 한글 literal
- 원본 한글-한글 공백
- 원본 한글 뒤 punctuation
- 원본 조사로 attach된 한글

### 8.3 Shadow 대상이 아닌 것

- 시스템이 숫자를 변환해 생성한 한글 reading
- acronym reading
- unit reading
- currency reading
- event reading
- generated range reading

예:

```text
입력: FTA은 21명
base render: 에프티에이은 스물한 명
final render after Safe particle exception: 에프티에이는 스물한 명
```

Shadow 대상:

```text
은  # Safe particle exception consumed span으로 표시
명
원본 공백
```

Generated 대상:

```text
에프티에이
스물한
```

Shadow Buffer는 render 이후 `RenderPiece` provenance와 비교된다.

### 8.4 ShadowUnit 생성 pseudo-code

```python
def build_shadow_buffer(tokens: list[SpanToken]) -> list[ShadowUnit]:
    shadow: list[ShadowUnit] = []
    for token in tokens:
        if token.kind == "KOREAN_LITERAL":
            shadow.append(ShadowUnit("KOREAN_LITERAL", token.raw, token.span))
        elif token.kind == "SPACE_LOCK":
            shadow.append(ShadowUnit("KOREAN_SPACE", token.raw, token.span))
        elif token.kind == "PUNCT_LOCK":
            shadow.append(ShadowUnit("KOREAN_PUNCT", token.raw, token.span))
    return shadow
```

### 8.5 Particle Shadow 처리

particle은 tokenizer 단계에서 일반 한글 literal과 동일하게 보존된다. 다만 surface claim 단계에서 trailing_particle로 attach되면 validation을 더 명확히 하기 위해 `PARTICLE_LITERAL` shadow를 추가할 수 있다.

```python
def mark_particle_shadow(surface: Surface, shadow: list[ShadowUnit]) -> None:
    if surface.trailing_particle and surface.trailing_particle_span:
        shadow.append(ShadowUnit(
            kind="PARTICLE_LITERAL",
            raw=surface.trailing_particle,
            span=surface.trailing_particle_span,
        ))
```

주의할 점은 같은 span이 `KOREAN_LITERAL`과 `PARTICLE_LITERAL`로 중복 검증될 수 있다는 것이다. 구현에서는 중복을 허용하되, validation report에서는 같은 span의 중복 fail을 하나로 합치는 것이 좋다.

### 8.6 Generated Hangul과 Original Hangul의 구분

Shadow Validation에서 가장 흔한 오류는 출력 문자열 전체에서 한글을 다시 추출하여 원본 한글과 비교하는 것이다. 이 방식은 잘못이다.

예:

```text
입력: 21명
출력: 스물한 명
```

출력 문자열 기준 한글은 `스물한명`이지만, 원본 보존 대상은 `명`뿐이다. 따라서 validation은 문자열 전체가 아니라 `RenderPiece.provenance`를 기준으로 수행해야 한다.

## 9. Phase 3 — Surface Claim Phase

이 단계는 발음 변환이 아니다. 어떤 원문 구간이 어떤 owner에게 속하는지 먼저 점유하는 단계다.

핵심 원칙:

- Claim before Parse
- Owner before Rewrite
- No Reentry after Claim
- Preserve claim also blocks unsafe fallback

### 9.1 Surface Claim 우선순위

아래 순서대로 claim을 시도한다. 이 표는 실제 `claim_scanner.py`의 scanner 호출 순서와 맞춘 implementation order다. 문서용 snapshot은 `claim_scanner.CLAIM_ORDER_DOC`를 따른다.

`square bracket protection`은 Surface Claim Phase 진입 전에 bracket owner로 excluded range를 만든다. URL/path/email/file-like protected literal은 claim phase 안에서 `preserve` owner와 `PROTECTED_LITERAL_SURFACE`로 선점된다.

| 우선순위 | Claim 대상 | 대표 예 | owner |
|---:|---|---|---|
| 0 | square bracket protection | `[12.3]`, `[3kg]`, `[2025/13/03]` | `bracket` |
| 1 | URL/path/email/protected literal | `docs/2025/01/03`, `https://example.com/2026/04/17`, `user@example.com`, `v1.2.3-beta` | `preserve` (`PROTECTED_LITERAL_SURFACE`) |
| 2 | dictionary / fixed lexical | `K-POP`, `KOSPI`, `AI`, `FTA` | `dictionary` |
| 3 | K-Hangul lexical prefix | `K-푸드`, `K-뷰티`, `K-팝` | `k_hangul_lexical` |
| 4 | lexical compound | `AI·반도체`, `ISO·IEC` | `lexical_compound` |
| 5 | single-letter uppercase alnum code | `A-1`, `K1`, `F-15C`, `A-10C` | `single_letter_alnum_code` |
| 6 | two-block hyphen code | `B-2.5`, `x-3` | `two_block_hyphen_code` |
| 7 | mixed alnum code separator | `A1·B2` | `mixed_alnum_code_separator` |
| 8 | uppercase acronym fallback | `NASA`, `CPU` | `acronym_fallback` |
| 9 | large unit atomic/numeric surface | `1억`, `2,345억`, `25.50억`, `2천8백28억` | `large_unit_atomic` |
| 10 | currency symbol/code | `€50`, `$100`, `USD 20`, `€1,234.56` | `currency` |
| 11 | date format | `2025.01.03`, `2025-01-03`, `2025/01/03` | `date` |
| 12 | time format | `13:05에`, `오전 3시` | `time` |
| 13 | N:M semantic pair | `1:2 비율`, `3:1 승리` | `colon_semantic_pair` |
| 14 | fixed event / event keyword | `5·18 민주화운동`, `12.12 사태`, `12.3 비상계엄` | `event` |
| 15 | emergency number context | `긴급번호 112는`, `119에 신고` | `emergency` |
| 16 | spaced separator preserve | `12 .3`, `12. 3`, `12 · 3`, `1 / 3` | `preserve` |
| 17 | spaced hyphen numeric blocks | `1 - 2`, `12 - 34` | `spaced_hyphen_numeric_blocks` |
| 18 | range with unit / shared suffix range | `3~8cm`, `1∼11월` | `range`, `range_with_unit` |
| 19 | percent point | `3%p` | `percent_point` |
| 20 | duration | `3시간`, `20분` | `duration` |
| 21 | unit contamination preserve | `45m3abc`, `90km/hour` | `preserve` |
| 22 | fraction | `1/2` | `fraction` |
| 23 | signed temperature | `-2.5℃` | `signed_temperature` |
| 24 | signed degree | `+3°` | `signed_degree` |
| 25 | signed number | `-5.2` | `signed_number` |
| 26 | pH prefix | `pH 7.4`, `pH7.4test` | `ph`, `preserve` |
| 27 | compound slash unit | `90km/h`, `15.2km/L` | `compound_slash_unit` |
| 28 | compound exact unit | `1kWh` | `compound_exact_unit` |
| 29 | special unit | `10Hz`, `45㎡` | `special_unit` |
| 30 | simple unit | `50kg`, `3km` | `simple_unit` |
| 31 | numeric suffix / prefixed ordinal | `제5차`, `제 15권`, `3번` | `numeric_suffix` |
| 32 | decimal fallback | `12.3`, `7.25` | `decimal` |
| 33 | middle-dot numeric fallback | `12·3`, `7·25`, `1·2·3` | `middle_dot_numeric` |
| 34 | public number | `국민콜 110에`, `1339는` | `public_number` |
| 35 | counter noun | `21명`, `112명`, `119건` | `counter_noun` |
| 36 | phone | `123-456-7890` | `phone` |
| 37 | hyphen digit blocks | `12-34-56`, `1-1-9` | `hyphen_digit_blocks` |
| 38 | JAMO surface | `ㄱ`, `ㄱㄴㄷ` | `jamo` |
| 39 | administrative suffix | `종로3가`, `역삼동 12번지` | `administrative_suffix` |
| 40 | general number | `123`, `2025` | `number` |

주의:

- 이 표는 탐지/점유 순서다.
- 최종 render 순서나 prosody 순서가 아니다.
- 앞선 owner가 claim한 `reentry_allowed=False` span은 뒤 owner가 재진입할 수 없다.
- `K-푸드` 계열은 lexical compound가 아니라 `k_hangul_lexical` owner가 처리한다.
- `single_letter_alnum_code`는 `B-2.5`, `x-3` 같은 two-block hyphen code보다 먼저 안전한 full-consume 후보만 claim한다.
- `event`는 decimal/middle-dot numeric fallback보다 먼저 claim해야 한다.
- `date`는 decimal/hyphen/slash numeric fallback보다 먼저 claim해야 한다.
- `large_unit_atomic`, `currency`, `signed_*`, `range`, `duration`, `ph`, `compound_*_unit`, `special_unit`, `simple_unit`은 decimal fallback보다 먼저 claim해야 한다.
- `decimal`은 event/date/ph/unit/currency/range 계열 owner가 모두 실패한 뒤에만 fallback으로 claim한다.
- `middle_dot_numeric`은 event/date/lexical compound 계열 owner가 모두 실패한 뒤에만 fallback으로 claim한다.
- `public_number`는 `counter_noun`보다 먼저 claim하지만, `112명`, `119건`처럼 emergency digit reading 대상이 아닌 explicit counter는 counter fallback을 허용한다.
- spaced separator preserve는 full consume rewrite owner가 아니라 unsafe partial rewrite를 막는 preserve owner다.

#### 9.1.1 URL/path/email/protected code context와 CODE_SEPARATOR_BLOCK_SURFACE의 경계

`URL/path/email/protected code context`는 모든 code-like token을 broad하게 보호하는 owner가 아니다. 이 owner는 다음 경우만 보호한다.

1. URL 내부
2. path 내부
3. email 내부
4. 파일명/확장자/path-like token
5. version/log/model/code context가 명시된 token
6. alphabetic prefix/suffix가 붙어 full consume이 불가능한 token
7. mixed separator 또는 unsupported separator가 포함되어 code separator block으로 full consume할 수 없는 token
8. 단위/온도/통화/date-like 후보에 invalid alphabetic tail이 붙은 token

보호 예:

```text
docs/2025/01/03/report.md -> preserve
https://example.com/2026/04/17 -> preserve
user.a.b@example.com -> preserve
A12.3B -> preserve
2025-13-03B -> preserve
v1.2.3-beta -> preserve
model-A-10C -> preserve
30ºCtest -> preserve
45㎡abc -> preserve
5Hzabc -> preserve
```

다음 입력은 protected code context가 아니라 `CODE_SEPARATOR_BLOCK_SURFACE` 후보로 넘긴다.

```text
A-1
A-B-C
01-02
1234-5678
123-456-7890
1-1-9
12-34-56
12/34/56
12.34.56
```

금지:

```text
A-1 -> A-1
A-B-C -> A-B-C
123-456-7890 -> 123-456-7890
```

### 9.2 Claim phase pseudo-code

```python
CLAIM_ORDER = [
    bracket_excluded_range_preclaim,
    protected_literal_claim,
    dictionary_claim,
    k_hangul_lexical_claim,
    lexical_compound_claim,
    single_letter_alnum_code_claim,
    two_block_hyphen_code_claim,
    mixed_alnum_code_separator_claim,
    acronym_fallback_claim,
    currency_claim,
    date_claim,
    time_claim,
    colon_semantic_pair_claim,
    event_claim,
    emergency_claim,
    spaced_separator_preserve_claim,
    spaced_hyphen_numeric_claim,
    range_claim,
    percent_point_claim,
    duration_claim,
    unit_contamination_preserve_claim,
    fraction_claim,
    signed_temperature_claim,
    signed_degree_claim,
    signed_number_claim,
    ph_claim,
    compound_slash_unit_claim,
    compound_exact_unit_claim,
    special_unit_claim,
    simple_unit_claim,
    numeric_suffix_claim,
    decimal_claim,
    middle_dot_numeric_claim,
    public_number_claim,
    counter_claim,
    phone_claim,
    hyphen_digit_blocks_claim,
    jamo_claim,
    large_unit_atomic_claim,
    administrative_suffix_claim,
    general_number_claim,
]

def claim_surfaces(tokens: list[SpanToken], registry: SurfaceClaimRegistry) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    for claim_fn in CLAIM_ORDER:
        for candidate in claim_fn.scan(tokens):
            if registry.can_claim(candidate.core_span, candidate.owner):
                registry.claim(ClaimedRange(
                    span=candidate.core_span,
                    owner=candidate.owner,
                    claim_type="surface",
                    surface_type=candidate.surface_type,
                    reason=candidate.reason,
                    reentry_allowed=False,
                ))
                candidates.append(candidate)
            else:
                handle_claim_collision(candidate, registry)
    return candidates
```

### 9.3 Dictionary / Acronym Claim

가장 먼저 고정 lexical 데이터를 claim한다.

대상:

```text
AI
FTA
MFN
KOSPI
KOSDAQ
S&P
```

원칙:

- dictionary longest match 우선
- dictionary가 safe acronym fallback보다 우선
- mixed-case는 safe acronym fallback 금지
- alnum/hyphen 형태는 safe acronym fallback 금지
- unit token과 충돌하면 unit owner 판단을 우선 검토하되, dictionary fixed surface가 있으면 dictionary가 이긴다.

예:

```text
AI -> 에이아이
FTA -> 에프티에이
OpenAI -> preserve 또는 dictionary 있을 때만 처리
USB3 -> generic acronym fallback 금지
A-1 -> acronym fallback 금지
```
#### 9.3.1 General Alphabet Fallback

General alphabet fallback은 dictionary/acronym owner와 CODE_SEPARATOR_BLOCK_SURFACE가 처리하지 못한 영문 입력을 제한적으로 읽기 위한 마지막 계층이다.

원칙:

1. dictionary에 등록된 약어와 fixed term은 dictionary reading을 우선한다.
2. CODE_SEPARATOR_BLOCK_SURFACE 내부의 영문은 항상 알파벳 한 글자씩 읽는다.
3. 단독 영문 1글자는 URL/path/email/code protection 내부가 아니면 알파벳 이름으로 읽을 수 있다.
4. 연속 대문자 block은 dictionary에 없더라도 알파벳 한 글자씩 읽을 수 있다.
5. mixed-case token은 dictionary에 없으면 preserve한다.
6. alnum mixed token은 명시 owner가 없으면 preserve한다.
7. alphabetic contamination이 있는 currency/unit/date/code-like token은 preserve한다.

canonical output:

```text
A -> 에이
B -> 비
ABC -> 에이 비 씨
A-B-C -> 에이 비 씨
A / B -> 에이 / 비
A - B -> 에이 - 비
```

dictionary output:

```text
AI -> 에이아이
USB -> 유에스비
OECD -> 오이시디
S&P -> 에스앤피
```

preserve output:

```text
OpenAI -> OpenAI
USB300 -> USB300
A12.3B -> A12.3B
EURA 300 -> EURA 300
300EURabc -> 300EURabc
5Hzabc -> 5Hzabc    
```

금지:

```text
USB300 -> 유에스비 삼백
A12.3B -> 에이십이쩜삼비
EURA 300 -> 유로 삼백
300EURabc -> 삼백 유로abc
```


#### 9.3.1.1 Hyphen / middle-dot mixed alnum code reading

문자와 숫자가 공백 없이 결합된 block들이 hyphen 또는 middle-dot 계열 구분자로 연결된 경우, dictionary/fixed lexical claim이 먼저 실패한 뒤 CODE_SEPARATOR_BLOCK_SURFACE가 code reading을 적용할 수 있다.

지원 구분자:

```text
-
−
－
·
ㆍ
∙
```

원칙:

- dictionary/fixed term이 항상 우선한다.
- `K-POP`, `Wi-Fi`처럼 고정어가 있으면 dictionary reading을 사용한다.
- dictionary가 없고 각 block이 ASCII letter/digit 조합이면 block 내부를 코드식으로 읽는다.
- URL/path/email/code-like 보호 구간 내부는 Absolute Preserve이다.
- unsafe tail이나 mixed-case word-like token은 Terminal Fallback Preserve로 원문 출력한다.

canonical output:

```text
K-POP -> 케이팝
A1-B2 -> 에이 일 비 이
A1·B2 -> 에이 일 비 이
USB3-LOG2 -> 유에스비 삼 엘 오 지 이
```

금지:

```text
K-POP -> 케이 피오피
K-POP -> 케이-팝
```

#### 9.3.2 Dictionary Schema and Managed Lexicon

모든 사전 기반 교정 용어는 문서 목록으로 관리하고 코드 구현과 테스트에 반영한다. 사전 항목은 broad fallback보다 우선한다.

```python
@dataclass
class LexiconEntry:
    surface: str
    reading: str
    entry_type: Literal[
        "acronym",
        "fixed_term",
        "event",
        "organization",
        "unit_alias",
        "technical_term",
        "public_number",
        "address_anchor",
    ]
    case_sensitive: bool = True
    priority: int = 100
    allow_particle_attach: bool = True
    allow_inside_compound: bool = False
    aliases: list[str] = field(default_factory=list)
    domains: set[str] = field(default_factory=set)
```

#### 방송·미디어·TTS 도메인 약어

| surface | reading |
|---|---|
| `KBS` | `케이비에스` |
| `MBC` | `엠비씨` |
| `SBS` | `에스비에스` |
| `EBS` | `이비에스` |
| `JTBC` | `제이티비씨` |
| `tvN` | `티비엔` |
| `OTT` | `오티티` |
| `VOD` | `브이오디` |
| `TTS` | `티티에스` |
| `STT` | `에스티티` |
| `ASR` | `에이에스알` |
| `NLP` | `엔엘피` |
| `AI` | `에이아이` |
| `API` | `에이피아이` |
| `UI` | `유아이` |
| `UX` | `유엑스` |

#### 영상·방송 기술 단위

| surface | reading |
|---|---|
| `HD` | `에이치디` |
| `FHD` | `에프에이치디` |
| `UHD` | `유에이치디` |
| `4K` | `포케이` |
| `8K` | `에이트케이` |
| `HDR` | `에이치디알` |
| `SDR` | `에스디알` |
| `fps` | `에프피에스` |
| `FPS` | `에프피에스` |
| `bitrate` | `비트레이트` |
| `kbps` | `킬로비피에스` |
| `Mbps` | `메가비피에스` |
| `Gbps` | `기가비피에스` |

#### 웹·파일·개발 포맷

| surface | reading |
|---|---|
| `URL` | `유알엘` |
| `URI` | `유알아이` |
| `HTML` | `에이치티엠엘` |
| `CSS` | `씨에스에스` |
| `JS` | `제이에스` |
| `JSON` | `제이슨` |
| `XML` | `엑스엠엘` |
| `YAML` | `야믈` |
| `CSV` | `씨에스브이` |
| `PDF` | `피디에프` |
| `DOCX` | `디오씨엑스` |
| `XLSX` | `엑스엘에스엑스` |
| `PPTX` | `피피티엑스` |
| `SQL` | `에스큐엘` |
| `REST` | `레스트` |
| `gRPC` | `지알피씨` |

#### 하드웨어·네트워크

| surface | reading |
|---|---|
| `CPU` | `씨피유` |
| `GPU` | `지피유` |
| `NPU` | `엔피유` |
| `RAM` | `램` |
| `ROM` | `롬` |
| `SSD` | `에스에스디` |
| `HDD` | `에이치디디` |
| `USB` | `유에스비` |
| `HDMI` | `에이치디엠아이` |
| `Wi-Fi` | `와이파이` |
| `LTE` | `엘티이` |
| `5G` | `파이브지` |
| `IP` | `아이피` |
| `DNS` | `디엔에스` |
| `VPN` | `브이피엔` |

#### 경제·정책·뉴스 용어

| surface | reading |
|---|---|
| `KOSPI` | `코스피` |
| `KOSDAQ` | `코스닥` |
| `NASDAQ` | `나스닥` |
| `S&P` | `에스앤피` |
| `GDP` | `지디피` |
| `CPI` | `씨피아이` |
| `PPI` | `피피아이` |
| `FOMC` | `에프오엠씨` |
| `OECD` | `오이시디` |
| `IMF` | `아이엠에프` |
| `WTO` | `더블유티오` |
| `WHO` | `더블유에이치오` |
| `UN` | `유엔` |
| `EU` | `이유` |

#### 긴급·공공번호 후보

긴급·공공번호는 bare number로 읽지 않는다. 반드시 context + allowed tail gate를 통과해야 한다.

| number | context 예 | reading |
|---|---|---|
| `112` | 경찰, 신고, 긴급번호 | `일일이` |
| `119` | 화재, 구급, 소방, 신고 | `일일구` |
| `110` | 국민콜, 민원, 상담 | `일일공` |
| `120` | 다산콜, 지자체 콜센터 | `일이공` |
| `117` | 학교폭력, 신고 | `일일칠` |
| `118` | 사이버, 신고, 상담 | `일일팔` |
| `1339` | 질병, 응급의료, 상담 | `일삼삼구` |
| `182` | 경찰민원 | `일팔이` |
| `125` | 밀수 신고 | `일이오` |

#### 사건형 날짜 사전

| surface/context | reading |
|---|---|
| `3·1절` | `삼일절` |
| `4·19 혁명` | `사일구 혁명` |
| `5·18 민주화운동` | `오일팔 민주화운동` |
| `6·25 전쟁` | `육이오 전쟁` |
| `8·15 광복` | `팔일오 광복` |
| `9·11 테러` | `구일일 테러` |
| `10·29 참사` | `십이구 참사` |
| `12.12 사태` | `십이십이 사태` |

Bare form은 preserve한다. event keyword immediate adjacency일 때만 event reading을 허용한다.

현재 large-unit 결정:

- bare `5·18`은 keyword 없는 fixed event shortcut으로 강제하지 않는다.
- bare `5·18`에는 middle-dot numeric block fallback을 적용한다.
- event keyword/profile이 인접한 `5·18 민주화운동`은 event owner가 처리한다.

canonical:

```text
5·18 -> 오 일팔
5·18 민주화운동 -> 오일팔 민주화운동
```

#### 주소/행정 suffix anchor 사전

행정 suffix owner는 address anchor 없이는 broad parse하지 않는다.

```text
시, 도, 군, 구, 동, 읍, 면, 리
로, 길, 번길, 대로, 가, 번지, 호
서울, 부산, 대구, 인천, 광주, 대전, 울산, 세종
강남, 종로, 역삼, 여의도, 마포, 상암, 목동
```

사전 항목은 모두 dictionary smoke test에 포함한다. 충돌 가능성이 있는 항목은 dictionary collision test에도 포함한다.

#### 9.3.3 Dictionary와 Unit Parser 충돌 정책

사전 항목과 unit/compound unit parser는 충돌할 수 있다. 특히 `fps`, `Mbps`, `Gbps`, `IP`, `5G`, `4K`, `8K`, `REST`, `RAM`, `ROM`은 문맥에 따라 dictionary, unit alias, acronym으로 볼 수 있다.

entry_type별 우선순위:

1. `fixed_term` / `event` / `organization`
2. `technical_term`
3. `unit_alias`
4. `acronym fallback`

규칙:

- `unit_alias`는 숫자 prefix가 있으면 unit/compound_unit owner가 우선한다.
- 숫자 prefix가 없으면 dictionary fixed reading을 사용할 수 있다.
- fixed_term, event, organization은 broad fallback보다 우선한다.

예:

```text
60fps -> 육십 에프피에스
fps가 낮다 -> 에프피에스가 낮다
10Mbps -> 십 메가비피에스
Mbps 기준 -> 메가비피에스 기준
```

### 9.4 Lexical Compound Claim

대상:

```text
AI·반도체
ISO·IEC
K-푸드
```

원칙:

- 숫자 parser보다 먼저 claim한다.
- middle dot, hyphen을 일반 기호로 분해하지 않는다.
- lexical 조건을 충족하지 않으면 preserve한다.
- lexical compound 내부의 한글 literal은 original provenance로 보존한다.

#### 9.4.0 K-Hangul lexical prefix policy

`K-` prefix handling is owner-scoped. `K-` followed by a complete Korean lexical token may be normalized to `케이` + original Hangul token when the owner can fully consume the token. If the token contains unsafe or non-Hangul tail material, this owner must not partially rewrite it; the token is left for subsequent owners/fallbacks and is only preserved if no later safe rule applies.

K- + 완성형 한글 lexical token은 `케이` + 원문 한글 token으로 읽는다. 이 규칙은 K-한글 owner가 전체 token을 안전하게 full consume할 수 있을 때만 적용한다. unsafe tail 또는 code-like tail이 붙으면 `K-` 부분만 변환하지 않는다. 해당 token은 다음 owner/fallback으로 넘기고, 최종까지 안전한 규칙이 없으면 원문 유지한다.

canonical examples:

```text
K-푸드 -> 케이푸드
K-뷰티 -> 케이뷰티
K-컬처 -> 케이컬처
K-콘텐츠 -> 케이콘텐츠
K-방산 -> 케이방산
K-드라마 -> 케이드라마
K-팝 -> 케이팝
K-POP -> 케이팝
```

non-target / fallback examples:

```text
AK-푸드 -> AK-푸드
model-K-푸드 -> model-K-푸드
K-푸드-v2 -> K-푸드-v2
K-2024 -> K-2024
K-ABC -> K-ABC
K-pop -> K-pop
https://example.com/K-푸드 -> preserve
docs/K-푸드/report.md -> preserve
```

위 비대상 예시는 K-한글 owner가 처리하지 않는다는 뜻이다. 다음 owner/fallback이 별도 안전 규칙으로 처리할 수 있으면 그 규칙을 따르고, 현재 정책에 그런 규칙이 없으면 원문 유지한다.

### 9.4.1 Hangul Middle-dot Literal Policy

완성형 한글 또는 한글 lexical token 사이의 middle dot `·`는, 명시적인 `event`, `middle_dot_numeric_block`, `lexical_compound` owner가 claim하지 않는 한 원문 그대로 보존한다.

이 정책은 한글 compound의 의미 경계 보존을 위한 것이다. middle dot를 공백으로 치환하거나 삭제하는 broad rewrite는 금지한다.

preserve examples:

```text
자동차·부품 -> 자동차·부품
원목·제재목 -> 원목·제재목
산업·공급망 -> 산업·공급망
정치적·선별 -> 정치적·선별
훈·포장 -> 훈·포장
미국표준협회·표준기술원 -> 미국표준협회·표준기술원
```

lexical compound examples:

```text
AI·반도체 -> 에이아이·반도체
ISO·IEC -> 아이에스오·아이이씨
```

event examples:

```text
4·19 혁명 -> 사일구 혁명
5·18 민주화운동 -> 오일팔 민주화운동
12·3 비상계엄 -> 십이삼 비상계엄
```

numeric fallback examples:

```text
12·3 -> 십이 삼
7·25 -> 칠 이오
1·2·3 -> 일 이 삼
```

금지:

```text
자동차·부품 -> 자동차 부품
원목·제재목 -> 원목 제재목
산업·공급망 -> 산업 공급망
정치적·선별 -> 정치적 선별
AI·반도체 -> 에이아이 반도체
ISO·IEC -> 아이에스오 아이이씨
```
### 9.5 Acronym + Lexical Suffix Claim

대상:

```text
FTA율
AI기반
MFN조항
```

원칙:

- suffix full consume 필요
- suffix는 사용자 입력 한글 literal로 보존
- acronym body만 reading 생성
- suffix를 분리하거나 공백 삽입 금지
- suffix가 조사인지 lexical suffix인지 owner가 분명해야 한다.

예:

```text
FTA율 -> 에프티에이율
AI기반 -> 에이아이기반
```

금지:

```text
FTA율 -> 에프티에 이율
MFN율 -> 엠에프엔 율
```

### 9.6 Event Claim

대상:

```text
12.12 사태
5·18 민주화운동
12.3 비상계엄
12·3 비상계엄
```

Event keyword whitelist는 strong keyword와 weak keyword로 나눈다.

Strong event keywords:

- `비상계엄`
- `계엄`
- `사태`
- `혁명`
- `민주화 운동`
- `민주화운동`
- `전쟁`
- `항쟁`
- `참사`
- `테러`
- `기념일`

Weak event keywords:

- `운동`
- `사건`
- `정책`
- `대책`
- `사고`
- `선거`

원칙:

- one-digit right block은 preserve 사유가 아니다.
- 숫자 표면은 가능한 한 의미 있는 owner로 먼저 해석한다.
- event keyword immediate adjacency 필요 (공백 또는 하이픈 허용)
- sentence-level semantic inference 금지
- `M.D`, `M·D` 형태는 event/date 후보로 먼저 평가한다.
- event/date 조건을 만족하면 EVENT_SURFACE로 처리한다.
- event/date 조건을 만족하지 못하면 numeric fallback을 적용한다.
- hyphen-linked event (`12.3-비상계엄`)도 event candidate로 보며, hyphen은 ORIGINAL_BOUNDARY로 보존한다.
- fixed dictionary event surface가 있으면 dictionary가 먼저 이긴다.

Strong keyword는 immediate adjacency만 충족하면 event gate를 통과할 수 있다.

Weak keyword는 immediate adjacency만으로는 부족하며, 다음 중 하나 이상을 추가로 만족해야 한다.

1. fixed event dictionary surface와 일치한다.
2. 정책/역사/사회 사건 도메인 profile이 활성화되어 있다.
3. 좌우 문맥에 사건, 역사, 정책, 발표, 대책, 부동산, 선거, 참사, 기념, 항쟁 등 event anchor가 있다.
4. 표면이 event dictionary의 alias 또는 known event pattern에 포함된다.

canonical output:

```text
12.3 비상계엄 -> 십이삼 비상계엄
12·3 비상계엄 -> 십이삼 비상계엄
12.12 사태 -> 십이십이 사태
4.19 혁명 -> 사일구 혁명
5·18 민주화운동 -> 오일팔 민주화운동
6.27 부동산대책 -> 육이칠 부동산대책
```

fallback examples:

```text
3.14 운동 -> 삼쩜일사 운동  # weak keyword만 있고 event anchor가 없으면 decimal fallback
7.25 정책 -> 칠쩜이오 정책  # dot 표면은 event gate 실패 시 decimal fallback
7·25 정책 -> 칠 이오 정책  # middle-dot 표면은 event gate 실패 시 numeric block fallback
12.3수치 -> 십이쩜삼수치
12·3수치 -> 십이 삼수치
```

예:

```text
12.12 사태 -> 십이십이 사태
5·18 민주화운동 -> 오일팔 민주화운동
12.3 비상계엄 -> 십이삼 비상계엄
12·3 비상계엄 -> 십이삼 비상계엄
12.3-비상계엄 -> 십이삼-비상계엄
12.3 -> 십이쩜삼 (decimal fallback)
12·3 -> 십이 삼 (middle-dot fallback)
```

### 9.7 Date / Time Claim

날짜와 시간은 분리한다.

#### Date

대상:

```text
2025-01-03
2025/01/03
2025.01.03
```

원칙:
* exact date format 우선
* 지원 date-like full format은 `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY.MM.DD` 세 가지다.
* year-month short dotted form은 별도 정책 없으면 preserve한다.
* `4-2-2` date-like pattern은 구분자가 `-`, `/`, `.` 중 하나이고 동일 구분자가 공백 없이 반복될 때 `date_time.date` owner가 우선 claim한다.
* calendar-valid이면 날짜로 읽는다.
* calendar-invalid이면 기본 preserve가 아니라, 아래 조건을 모두 만족할 때 `CODE_SEPARATOR_BLOCK_SURFACE` fallback을 허용한다.
  1. pure numeric 3-block이다.
  2. 각 block은 `4-2-2` 형태를 유지한다.
  3. 모든 구분자가 동일하다.
  4. 구분자 좌우에 공백이 없다.
  5. URL/path/email 내부가 아니다.
  6. alphabetic tail이 붙지 않았다.
  7. square bracket 보호 구간 내부가 아니다.
  8. version/log/model/code context가 아니다.
* 위 조건 중 하나라도 실패하면 preserve한다.
* invalid date fallback은 날짜 reading이 아니며, code separator block reading이다.
* `-` `/`는 구분자를 생략하고 block 사이 공백으로 렌더링한다.
* `.`는 각 구분자를 `쩜 `으로 렌더링한다.

#### Short slash date non-goal

현재 정책은 `M/D`, `MM/DD`, `M/DD`, `MM/D` 형태의 short slash date를 지원하지 않는다. `1/2`, `01/02`, `10/25`는 date owner가 아니라 slash fraction owner 후보로 본다. 날짜로 읽으려면 현재 정책상 `YYYY/MM/DD` 형태가 필요하다.

```text
1/2 -> 이분의 일
10/25 -> 이십오분의 십
2025/01/02 -> 이천이십오년 일월 이일
docs/2025/01/02/report.md -> preserve
1/2일 -> future/review
1/2 일정 -> future/review
1/2부터 -> future/review
```

예:
```text
2025-01-03 -> 이천이십오년 일월 삼일
2025/01/03 -> 이천이십오년 일월 삼일
2025.01.03 -> 이천이십오년 일월 삼일
2025-13-03 -> 이공이오 일삼 공삼
2025/13/03 -> 이공이오 일삼 공삼
2025.13.03 -> 이공이오쩜 일삼쩜 공삼
2025-01-32 -> 이공이오 공일 삼이
2025/02/30 -> 이공이오 공이 삼공
2025.02.30 -> 이공이오쩜 공이쩜 삼공
2025.01 -> preserve
```

Version/log/model/code context는 calendar-valid 여부와 무관하게 full date-like token을 preserve한다.

preserve examples:

```text
버전 2025.01.03 -> 버전 2025.01.03
버전 2025.13.03 -> 버전 2025.13.03
로그 2025.02.30 -> 로그 2025.02.30
모델 2025-13-03 -> 모델 2025-13-03
코드 2025/13/03 -> 코드 2025/13/03
ID 2025.13.03 -> ID 2025.13.03
```

date reading examples:

```text
행사는 2025.01.03에 열린다 -> 행사는 이천이십오년 일월 삼일에 열린다
일정은 2026/04/17로 잡혔다 -> 일정은 이천이십육년 사월 십칠일로 잡혔다
```

invalid fallback examples:

```text
2025-13-03 -> 이공이오 일삼 공삼
2025/13/03 -> 이공이오 일삼 공삼
2025.13.03 -> 이공이오쩜 일삼쩜 공삼
```


#### Date render special case: Arabic `6월` and `10월`

날짜 owner 또는 날짜/시간 shared-suffix range owner가 Arabic `6` + `월` 또는 Arabic `10` + `월`을 날짜 월 단위로 렌더링할 때는 각각 `유월`, `시월`로 읽는다. 한글 원문 `유월`, `십월`은 ORIGINAL_KOREAN literal이므로 바꾸지 않는다.

```text
6월 -> 유월
10월 -> 시월
2026년 6월 17일 -> 이천이십육년 유월 십칠일
2026-06-17 -> 이천이십육년 유월 십칠일
2026/06/17 -> 이천이십육년 유월 십칠일
2026년 10월 1일 -> 이천이십육년 시월 일일
2026년 10월 21일 -> 이천이십육년 시월 이십일일
6월부터 -> 유월부터
10월부터 -> 시월부터
6월까지 -> 유월까지
10월까지 -> 시월까지
6개월 -> 육개월
10개월 -> 십개월
유월 -> 유월
십월 -> 십월
```

#### Time

대상:

```text
13:05에
오전 3시
3시 20분
```

Time prefix tokens:

- `오전`
- `오후`
- `새벽`
- `아침`
- `정오`
- `밤`
- `저녁`

Time event/context tokens:

- `출발`
- `도착`
- `시작`
- `종료`
- `마감`
- `개시`
- `오픈`
- `폐장`
- `예약`
- `탑승`
- `발차`
- `상영`
- `회의`
- `수업`
- `진료`
- `시각`
- `시간`

Time postpositions:

- `에`
- `까지`
- `부터`
- `경`
- `쯤`
- `정각`

Time claim table:

| 입력 형태 | owner | context read 필요 | 허용 조건 | 차단 조건 | preserve 조건 |
|---|---|---:|---|---|---|
| `HH:MM:SS` | `date_time.time_colon` | 낮음 | `try_parse_time()` 성공 시 독립 clock pattern 허용 | 값 범위 오류 | 값 범위 오류면 preserve |
| `HH:MM` | `date_time.time_colon` | 높음 | time prefix, time postposition, time-event keyword, 한국어 날짜 좌문맥 중 하나 | 단독 전체 입력, 다중 colon, score/ratio, 값 범위 오류 | gate 실패 시 preserve |
| `H시` | `date_time.time_hour_korean` | 중간 | 좌우에 붙은 단어가 없고 독립 token 경계 | `3시리즈` 같은 attached word | gate 실패 시 preserve |
| `H시 M분` | `date_time` | 낮음 | exact local parse 성공 | 값 범위 오류 | 실패 시 preserve |
| `오전/오후 + H시` | `date_time` | 중간 | 앞 time prefix 허용 | attached word, 값 범위 오류 | 실패 시 preserve |

예:

```text
회의는 13:05에 시작한다 -> 회의는 십삼시 오분에 시작한다
13:05 -> preserve
score 12:30 -> preserve
```

### 9.8 Currency Claim

대상:

```text
$100
€50
₩1200
USD 20
KRW1000
1,000원
1,000 KRW
```

Currency inventory:

| 종류 | 입력 표면 | reading | guard |
|---|---|---|---|
| symbol | `$`, `＄`, `﹩` | `달러` | valid signed decimal-aware numeric required |
| symbol | `€` | `유로` | valid signed decimal-aware numeric required |
| symbol | `₩`, `￦` | `원` | valid signed decimal-aware numeric required |
| symbol | `¥`, `￥` | `엔` | valid signed decimal-aware numeric required |
| symbol | `£` | `파운드` | valid signed decimal-aware numeric required |
| code | `USD` | `달러` | valid signed decimal-aware numeric required |
| code | `KRW` | `원` | valid signed decimal-aware numeric required |
| code | `EUR` | `유로` | valid signed decimal-aware numeric required |
| code | `JPY` | `엔` | valid signed decimal-aware numeric required |
| code | `GBP` | `파운드` | valid signed decimal-aware numeric required |
| Korean suffix | `원` | `원` | valid signed decimal-aware numeric required |
| Korean suffix | `달러` | `달러` | valid signed decimal-aware numeric required |
| Korean suffix | `유로` | `유로` | valid signed decimal-aware numeric required |
| Korean suffix | `엔` | `엔` | valid signed decimal-aware numeric required |
| Korean fallback code | `유에스디` | `달러` | post-rule normalization |
| Korean fallback code | `케이알더블유` | `원` | post-rule normalization |
| Korean fallback code | `이유알` | `유로` | post-rule normalization |

원칙:

- Registry-backed symbol/code/suffix forms with the same currency and numeric
  value share the same canonical output.
- Prefix forms support no-space or one ASCII-space marker-to-number attachment:
  `KRW1000`, `KRW 1,000`, `₩1,000`.
- Suffix forms support no-space or one ASCII-space number-to-marker attachment:
  `1,000원`, `1,000 원`, `1,000KRW`, `1,000 KRW`, `1,000$`.
- Signs are part of the valid numeric block for suffix/code forms and may appear
  before or after a registered prefix symbol: `KRW+1,000`, `₩+1,000`,
  `+₩1,000`.
- Two or more spaces, tabs, and newlines do not form one currency surface.
- Invalid numeric blocks and repeated/conflicting sign surfaces are preserved.
- Invalid alphabetic contamination 있으면 preserve
- trailing Korean tail은 context로 읽을 수 있으나 rewrite 금지
- currency owner는 general number owner보다 우선한다.

예:

```text
€1,234.56 -> 천이백삼십사쩜오육 유로
₩1200 -> 천이백 원
1,000원 / KRW1000 / ₩1,000 / 1,000KRW -> 천 원
1,000.50원 / KRW1,000.50 / ₩1,000.50 / 1,000.50KRW -> 천쩜오영 원
1,000  원 -> preserve
01.5원 -> preserve
```


#### Large-unit numeric surface coverage

Large-unit numeric surfaces use the existing numeric reading canonical. The
policy expands input coverage without changing the canonical output.

Supported large-unit suffix contexts include registered large-unit suffixes such
as `만`/`억`/`조`. Valid comma integer, signed decimal, and mixed
Arabic-Hangul large-unit surfaces are full-claimed by the large-unit owner.

```text
2,345억 -> 이천삼백사십오억
25.50억 -> 이십오쩜오영 억
+25.50억 -> 플러스 이십오쩜오영 억
2천8백28억 -> 이천팔백이십팔억
2천8백28.5억 -> 이천팔백이십팔쩜오 억
```

Decimal large-unit surfaces read the numeric surface as written and keep the
large-unit suffix as a suffix, separated by one space. They are not converted to
semantic currency amounts.

```text
25.50억 -> 이십오쩜오영 억
25.50억 원 -> 이십오쩜오영 억 원
3.5만 원 -> 삼쩜오 만 원
```

Hangul tails after a valid large-unit core are separated with a space unless the
tail is an existing attached particle/ending form.

```text
2천8백28억테스트 -> 이천팔백이십팔억 테스트
2,345억테스트 -> 이천삼백사십오억 테스트
```

English tail literal preservation applies after reading a valid large-unit core:
the core is read, and the following English tail is kept literally without
inserted spacing. Code-like English prefixes before a large-unit core are
preserved as whole surfaces.

```text
2천8백28억abc -> 이천팔백이십팔억abc
2,345억abc -> 이천삼백사십오억abc
25.50억abc -> 이십오쩜오영 억abc
v2천8백28억 -> v2천8백28억
SKU2천8백28억 -> SKU2천8백28억
```

Invalid numeric surfaces are preserved and must not be partially rewritten.

```text
2,34억 -> 2,34억
+.5억 -> +.5억
25..50억 -> 25..50억
2천8백.28억 -> 2천8백.28억
```

### 9.9 Unit-bound Claim

단위는 일반 숫자보다 반드시 먼저 claim한다.

대상:

```text
50kg
10Hz
45㎡
90km/h
15.2km/L
```

분류:

```text
compound_unit: 90km/h, 15.2km/L
simple_unit: 50kg, 10Hz
special_unit: 45㎡
```

Simple Unit Inventory:

| token | reading | guard |
|---|---|---|
| `mm` | `밀리미터` | numeric prefix 필요 |
| `cm` | `센티미터` | numeric prefix 필요 |
| `m` | `미터` | numeric prefix 필요 |
| `km` | `킬로미터` | numeric prefix 필요 |
| `mg` | `밀리그램` | numeric prefix 필요 |
| `g` | `그램` | numeric prefix 필요 |
| `kg` | `킬로그램` | numeric prefix 필요 |
| `t` | `톤` | live simple-unit skip |
| `mL` | `밀리리터` | numeric prefix 필요 |
| `L` | `리터` | numeric prefix 필요 |
| `V` | `볼트` | ambiguous single-letter guard |
| `A` | `암페어` | ambiguous single-letter guard |
| `W` | `와트` | numeric prefix 필요 |
| `kW` | `킬로와트` | numeric prefix 필요 |
| `MW` | `메가와트` | numeric prefix 필요 |
| `Wh` | `와트시` | numeric prefix 필요 |
| `kWh` | `킬로와트시` | numeric prefix 필요 |
| `MWh` | `메가와트시` | numeric prefix 필요 |
| `Hz`, `hz` | `헤르츠` | numeric prefix 필요 |
| `dB` | `데시벨` | numeric prefix 필요 |
| `bit` | `비트` | numeric prefix 필요 |
| `Byte` | `바이트` | numeric prefix 필요 |
| `KB` | `킬로바이트` | numeric prefix 필요 |
| `MB` | `메가바이트` | numeric prefix 필요 |
| `GB` | `기가바이트` | numeric prefix 필요 |
| `TB` | `테라바이트` | numeric prefix 필요 |
| `PB` | `페타바이트` | numeric prefix 필요 |
| `kHz`, `khz` | `킬로헤르츠` | numeric prefix 필요 |
| `MHz`, `mhz` | `메가헤르츠` | numeric prefix 필요 |
| `GHz`, `Ghz`, `ghz` | `기가헤르츠` | numeric prefix 필요 |
| `Gbps` | `기가비피에스` | numeric prefix 필요 |
| `Tbps` | `테라비피에스` | numeric prefix 필요 |
| `도` | `도` | numeric prefix 필요 |

Special Unit Inventory:

| token | reading |
|---|---|
| `㎜` | `밀리미터` |
| `㎝` | `센티미터` |
| `㎙` | `미터` |
| `㎞` | `킬로미터` |
| `㎎` | `밀리그램` |
| `㎏` | `킬로그램` |
| `㎖` | `밀리리터` |
| `ℓ` | `리터` |
| `㎐` | `헤르츠` |
| `㏈` | `데시벨` |
| `㎡` | `제곱미터` |
| `㎥` | `세제곱미터` |
| `%` | `퍼센트` |
| `％` | `퍼센트` |
| `‰` | `퍼밀` |
| `°` | `도` |

Area / Volume Unit Inventory:

| token | reading | guard |
|---|---|---|
| `m²` | `제곱미터` | numeric prefix 필요 |
| `m2` | `제곱미터` | numeric prefix 필요 |
| `cm²` | `제곱센티미터` | numeric prefix 필요 |
| `cm2` | `제곱센티미터` | numeric prefix 필요 |
| `km²` | `제곱킬로미터` | numeric prefix 필요 |
| `km2` | `제곱킬로미터` | numeric prefix 필요 |
| `m³` | `세제곱미터` | numeric prefix 필요 |
| `m3` | `세제곱미터` | numeric prefix 필요 |
| `cm³` | `세제곱센티미터` | numeric prefix 필요 |
| `cm3` | `세제곱센티미터` | numeric prefix 필요 |

canonical output:

```text
45㎡ -> 사십오 제곱미터
45m² -> 사십오 제곱미터
45m2 -> 사십오 제곱미터
45㎥ -> 사십오 세제곱미터
45m³ -> 사십오 세제곱미터
45m3 -> 사십오 세제곱미터
```

금지:

```text
45m² -> 사십오 미터²
45m2 -> 사십오 미터이
45m3 -> 사십오 미터삼
45㎥ -> 사십오 ㎥
```

Slash Compound Unit Reading Inventory:

복합 단위 `A/B`는 원칙적으로 `(뒷단위 한글표기)당 (숫자) (앞단위 한글표기)`로 읽는다. 단, `시속`, `분속`, `초속`처럼 한국어에서 더 자연스러운 고정 표현이 있는 경우에는 아래 목록의 reading template을 우선한다. 하나의 단위에 복수 reading을 두지 않는다. 새 예외가 필요하면 이 표에 한 줄씩 추가한 뒤 코드와 테스트에 반영한다.

| token | reading template | owner note |
|---|---|---|
| `km/h`, `㎞/h` | `시속 {number} 킬로미터` | speed family |
| `m/h` | `시속 {number} 미터` | speed family |
| `km/min`, `㎞/min` | `분속 {number} 킬로미터` | speed family |
| `m/min` | `분속 {number} 미터` | speed family |
| `km/s`, `㎞/s` | `초속 {number} 킬로미터` | speed family |
| `m/s` | `초속 {number} 미터` | speed family |
| `cm/s` | `초속 {number} 센티미터` | speed family |
| `mm/s` | `초속 {number} 밀리미터` | speed family |
| `km/L`, `km/l`, `km/ℓ`, `㎞/L`, `㎞/l`, `㎞/ℓ` | `리터당 {number} 킬로미터` | efficiency family |
| `m/L`, `m/l`, `m/ℓ` | `리터당 {number} 미터` | efficiency family, numeric required |
| `mg/dL` | `데시리터당 {number} 밀리그램` | medical/scientific fixed Korean reading |
| `g/dL` | `데시리터당 {number} 그램` | medical/scientific fixed Korean reading |
| `mg/L` | `리터당 {number} 밀리그램` | concentration family |
| `g/L` | `리터당 {number} 그램` | concentration family |
| `kg/m3` | `세제곱미터당 {number} 킬로그램` | density family |
| `MB/s` | `초당 {number} 메가바이트` | data throughput family |
| `GB/s` | `초당 {number} 기가바이트` | data throughput family |
| `Mbps` | `{number} 메가비피에스` | lexicalized compound, slash 없음 |
| `Gbps` | `{number} 기가비피에스` | lexicalized compound, slash 없음 |
| `bps` | `{number} 비피에스` | lexicalized compound, slash 없음 |
| `rpm`, `㏘` | `{number} 알피엠` | lexicalized compound |
| `fps` | `{number} 에프피에스` | lexicalized compound |
| `ppm` | `{number} 피피엠` | lexicalized compound |
| `dBi` | `{number} 디비아이` | lexicalized compound |

원칙:

- number + unit 전체 full consume
- invalid slash tail이면 preserve
- URL/path-like context면 unit parser 진입 금지
- 단위 residue를 남기는 partial consume 금지
- ambiguous single-letter unit `A`, `V`는 broad parse 금지
- scientific notation `1e6`, `3.2E-4`는 현재 명시 지원 parser가 없으므로 preserve
- higher-priority unit/temperature candidate가 invalid alphabetic tail 때문에 실패한 경우, 해당 candidate token 전체에 preserve claim을 등록한다.
- 이 preserve claim은 general number fallback이 앞 숫자만 소비하지 못하도록 막아야 한다.

invalid tail preserve examples:

```text
30ºCtest -> 30ºCtest
40℉abc -> 40℉abc
45㎡abc -> 45㎡abc
5Hzabc -> 5Hzabc
5hzabc -> 5hzabc
15.2km/La -> 15.2km/La
15.2km/lab -> 15.2km/lab
3km/speed -> 3km/speed
90km/hour -> 90km/hour
250m/Lite -> 250m/Lite
```


#### Decimal simple unit and numeric Korean suffix claim

명시 owner가 소유한 숫자+단위 또는 숫자+한글 suffix는 숫자가 소수/valid comma decimal이어도 preserve하지 않고 full consume한다. 숫자 core는 generated reading으로 바꾸고, 한글 suffix는 원문 literal을 유지한다.

원칙:

- 숫자와 단위/suffix 사이에는 공백 없음 또는 ASCII space 한 칸만 허용한다.
- `0.8초`처럼 한글 suffix가 붙은 경우 suffix 자체는 원문 한글 literal이므로 rewrite하지 않는다.
- `2,645.35선`, `제15권`처럼 숫자 앞뒤에 한글 anchor가 있는 경우 숫자 core만 변환한다.
- 한글 prefix/suffix에 공백 없이 붙은 숫자는 별도 고유어 counter 정책 또는 아래 `제+숫자+등록된 한글표기단위` 정책이 명확히 적용되는 경우가 아니면 기본 한자어 숫자로 읽는다.
- `제` followed by an integer and a registered Hangul counter/suffix is normalized as an ordinal-like prefixed numeric suffix.
- The numeric part is always read in Sino-Korean.
- The canonical output is `제 ` + Sino-Korean number + suffix.
- This applies to both `제N+suffix` and `제 N+suffix`.
- This rule is limited to the engine's registered Hangul counter/suffix inventory and does not apply to arbitrary Hangul strings.
- `제` 뒤에 숫자와 엔진에 등록된 한글표기단위가 붙으면 ordinal-like prefixed numeric suffix로 처리한다.
- 숫자는 counter의 고유어/hybrid 정책과 관계없이 항상 한자어로 읽는다.
- 출력은 `제 ` + 한자어 숫자 + 단위로 통일한다.
- `제N+단위`와 `제 N+단위` 모두 같은 canonical로 처리한다.
- 대상은 등록된 한글표기단위로 제한하며 임의의 모든 한글 문자열로 확장하지 않는다.
- 숫자와 단위 사이가 띄어져 있거나 ASCII/code-like prefix가 붙은 경우는 이 collapse 대상이 아니다. unsafe tail은 preserve한다.
- unsupported suffix는 즉시 Absolute Preserve하지 않고 generic numeric+suffix owner 후보로 평가할 수 있다.
- unsafe tail, ASCII identifier-left context, invalid comma는 Absolute Preserve 또는 Terminal Fallback Preserve로 처리한다.

canonical output:

```text
1.2km -> 일쩜이 킬로미터
1.2 km -> 일쩜이 킬로미터
0.8초 -> 영쩜팔초
2.5kg -> 이쩜오 킬로그램
1,250m -> 천이백오십 미터
1,250 m -> 천이백오십 미터
2,645.35선 -> 이천육백사십오쩜삼오선
제5차 -> 제 오차
제 5차 -> 제 오차
제15권 -> 제 십오권
제 15권 -> 제 십오권
제12권 -> 제 십이권
제 12권 -> 제 십이권
제62회 -> 제 육십이회
제 62회 -> 제 육십이회
제4과 -> 제 사과
제 4과 -> 제 사과
제2편 -> 제 이편
제 2편 -> 제 이편
제2판 -> 제 이판
제 2판 -> 제 이판
제2줄 -> 제 이줄
제 2줄 -> 제 이줄
제2칸 -> 제 이칸
제 2칸 -> 제 이칸
제2차례 -> 제 이차례
제 2차례 -> 제 이차례
2문항 -> 두 문항
제2문항 -> 제 이문항
제 2문항 -> 제 이문항
2항목 -> 두 항목
제2항목 -> 제 이항목
2대 -> 두 대
제2대 -> 제 이대
A제5차 -> A제5차
A제 5차 -> A제 5차
제2문항abc -> 제2문항abc
제2문항A -> 제2문항A
제2-문항 -> 제2-문항
제5G -> 제5G
제5abc -> 제5abc
제5-차 -> 제5-차
```

Terminal Fallback Preserve examples:

```text
1.2kmabc -> 1.2kmabc
abc1.2km -> abc1.2km
1,25m -> 1,25m
2,645.35선abc -> 2,645.35선abc
A2,645.35선 -> A2,645.35선
```

금지:

```text
30ºCtest -> 삼십ºCtest
40℉abc -> 사십℉abc
45㎡abc -> 사십오㎡abc
5Hzabc -> 오Hzabc
15.2km/La -> 십오쩜이km/La
3km/speed -> 삼 킬로미터/speed
50kg -> 오십kg
10Hz -> 십Hz
3~8cm -> 삼에서 팔cm
```

### 9.10 Range Claim

대상:

```text
3~8cm
1∼11월
2~5시
5~7쪽
8∼12장
3에서 8cm
```

원칙:

- 양쪽 numeric-like 필요
- range owner는 내부 숫자를 number owner가 먼저 부분 변환하지 못하게 막아야 한다.
- range-with-unit claim은 simple/special unit claim보다 먼저 실행한다.
- simple_unit scanner는 더 큰 range-with-unit 후보 내부의 `8cm` 같은 부분을 독립 claim하면 안 된다.
- range alias는 owner-local로만 처리한다: `~`, `∼`, `～`, `〜`.
- hyphen range는 `Numeric-delimited two-block fallback blocking` addendum에 따라 처리한다.
  단독/ambiguous `N-M`은 range로 확장하지 않고 internal numeric fallback을 막으며,
  `N-M + range-compatible unit`만 range로 claim한다.

#### Generic physical-unit shared suffix range

날짜/시간이 아닌 physical unit은 기존 shared-suffix reading을 유지한다. 오른쪽 숫자에만 suffix reading을 붙인다.

```text
3~8cm -> 삼에서 팔 센티미터
3∼8cm -> 삼에서 팔 센티미터
3~5km -> 삼에서 오 킬로미터
8~12cm -> 팔에서 십이 센티미터
```

#### Date shared suffix range

날짜 단위 `년`, `월`, `일`은 양쪽 숫자에 날짜 단위 reading을 적용한다.

```text
2024~2026년 -> 이천이십사년에서 이천이십육년
1~11월 -> 일월에서 십일월
1∼11월 -> 일월에서 십일월
10~12월 -> 시월에서 십이월
3~5일 -> 삼일에서 오일
```

현재 정책에서 `주`, `개월`, `분기`, `상반기`, `하반기`, `주년`, `일간`, `년간`은 date shared suffix range로 추가하지 않는다.

#### Time shared suffix range

Shared suffix range는 suffix type을 따른다. Clock hour `시`와 duration `시간`은 서로 다른 suffix owner이며, 절대 같은 owner로 섞어 처리하지 않는다.

Clock hour range에서 `시`는 clock hour reading을 양쪽에 적용한다. `1~12시`는 고유어 hour form, `13~24시`는 한자어 clock hour form을 쓴다.

```text
2~3시 -> 두 시에서 세 시
10~12시 -> 열 시에서 열두 시
13~15시 -> 십삼 시에서 십오 시
20~22시 -> 이십 시에서 이십이 시
10~30분 -> 십분에서 삼십분
3~8초 -> 삼초에서 팔초
```

Duration range에서 `시간`은 duration reading을 양쪽에 적용한다. `1~23시간`은 고유어 duration form, `24시간` 이상은 한자어 duration form을 쓴다.

```text
7~9시간 -> 일곱 시간에서 아홉 시간
20~22시간 -> 스무 시간에서 스물두 시간
24~48시간 -> 이십사 시간에서 사십팔 시간
```

금지:

```text
7~9시간 -> 칠시에서 구시간
7~9시간 -> 칠시에서 아홉 시간
```

현재 정책에서 `분간`, `초간`, `개월`, `년간`은 duration range로 추가하지 않는다.

#### Korean page/document counter tilde range

한글 단위 `쪽`, `장`은 tilde/range alias가 있을 때만 range로 처리한다. 숫자는 한자어로 읽고 suffix는 원문 literal로 유지한다.

```text
5~7쪽 -> 오에서 칠쪽
8∼12장 -> 팔에서 십이장
```

hyphen form은 `N-M + range-compatible unit`일 때만 range owner canonical 대상이다.
단독/ambiguous `N-M`은 Absolute Preserve가 아니라 policy-deferred Owner Fallback Candidate이며,
다른 owner가 처리하지 못하면 internal numeric fallback 없이 원문 출력한다.

```text
12-15장 -> 십이에서 십오 장
1-2쪽 -> 1-2쪽
1-2 -> 1-2
```

금지:

```text
3~8cm -> 삼~8cm
1∼11월 -> 일∼십일월
1∼11월 -> 일에서 십일월
5~7쪽 -> 5~7쪽
12-15장 -> 십이에서 십오장
1-2 -> 일-이
```

### 9.11 Hyphen Routing Claim

hyphen은 가장 위험한 기호 중 하나다. 넓은 “전화번호/모델명 등” 처리를 금지하고, `CODE_SEPARATOR_BLOCK_SURFACE`와 date owner의 우선순위에 따라 명시 routing table로만 처리한다.

분기:

1. exact `4-2-2` hyphen date-like pattern
   - `date_time.date` owner가 우선 claim한다.
   - calendar-valid이면 날짜로 읽는다.
   - calendar-invalid이면 code separator fallback guard를 평가한다.
   - fallback guard를 모두 통과하면 `CODE_SEPARATOR_BLOCK_SURFACE`로 digit-by-digit block reading한다.
   - fallback guard 실패 시 preserve한다.
2. 세 블럭 이상 hyphen code separator
   - 블럭 수 3개 이상, 동일 구분자 `-`, 공백 없음, 각 블럭 non-empty이면 `CODE_SEPARATOR_BLOCK_SURFACE`로 처리한다.
   - 숫자/영문/완성형 한글/한글 자모 혼합을 허용한다.
3. 두 블럭 hyphen
   - 공백이 있으면 code separator owner를 적용하지 않고 다음 owner로 넘긴다.
   - 공백 없이 붙어 있고 한쪽이라도 숫자 이외 문자가 있으면 code separator reading을 적용한다.
   - 두 블럭이 모두 숫자이면, 한쪽이라도 `0`으로 시작하거나 4자리 이상이면 code separator reading을 적용한다.
   - 두 블럭이 모두 숫자이고 위 조건에 해당하지 않으면 원문 그대로 유지한다.
4. URL/path/email, square bracket 내부, 더 구체적인 owner가 선점한 span은 hyphen code separator owner가 claim하지 않는다.

#### Calendar-invalid hyphen fallback and Non-Reentry

calendar-invalid `YYYY-MM-DD` fallback은 code separator scanner의 독립 재진입이 아니다.

- 최초 claim owner는 항상 `date_time.date`다.
- `CODE_SEPARATOR_BLOCK_SURFACE` scanner는 exact `4-2-2` date-like pattern을 최초 claim하지 않는다.
- calendar-invalid fallback은 `date_time.date` gate/parser 내부의 제한적 fallback action으로 실행한다.
- fallback output은 code separator block reading을 사용하되, trace에는 `original_owner=date_time.date`, `fallback_owner=code_separator_block`, `fallback_reason=calendar_invalid_date_like`를 기록한다.
- 이 fallback은 `ClaimedRange(reentry_allowed=False)` 원칙을 깨는 재진입이 아니다.

Hyphen Code Separator Routing Table:

| 입력 패턴 | owner | 처리 | preserve 조건 | canonical output |
|---|---|---|---|---|
| calendar-valid `YYYY-MM-DD` exact `4-2-2` | `date_time.date` | date owner가 우선 claim하고 날짜로 render | year range 또는 date gate 실패 시 preserve. 단, calendar-invalid만 아래 fallback 행으로 routing 가능 | `2025-01-03 -> 이천이십오년 일월 삼일` |
| calendar-invalid `YYYY-MM-DD` exact `4-2-2` | `date_time.date -> code_separator_block fallback` | date owner가 먼저 claim한 뒤, calendar validity 실패가 확인되면 fallback guard 통과 시 code separator block reading | pure numeric 3-block 아님, `4-2-2` shape 불일치, URL/path/email 내부, alphabetic tail, square bracket 보호 구간 내부이면 preserve | `2025-13-03 -> 이공이오 일삼 공삼` |
| `123-456-7890` | `code_separator_block` | pure numeric 3+ blocks digit-by-digit block reading | block routing 실패 시 preserve | `일이삼 사오육 칠팔구공` |
| `010-1234-5678` | `code_separator_block` | pure numeric 3+ blocks digit-by-digit block reading | preserve 없음 | `공일공 일이삼사 오육칠팔` |
| `1-1-9` | `code_separator_block` | emergency parser가 아니라 code separator block route | block routing 실패 시 preserve | `일 일 구` |
| `A-1-2` | `code_separator_block` | 3-block alpha-mixed code separator reading | URL/path/email, square bracket 내부이면 preserve | `에이 일 이` |
| `A-B-C` | `code_separator_block` | 3-block alpha code separator reading | URL/path/email, square bracket 내부이면 preserve | `에이 비 씨` |
| `가-나-다` | `code_separator_block` | 3-block completed Hangul code separator reading | URL/path/email, square bracket 내부이면 preserve | `가 나 다` |
| `ㄱ-ㄴ-ㄷ` | `code_separator_block` | 3-block jamo code separator reading | URL/path/email, square bracket 내부이면 preserve | `기역 니은 디귿` |
| `A-1` | `single_letter_alnum_code` | single-letter uppercase alnum code | URL/path/email, square bracket 내부이면 preserve | `에이 원` |
| `가-3` | `code_separator_block` | two-block hyphen, non-numeric character included | URL/path/email, square bracket 내부이면 preserve | `가 삼` |
| `ㄱ-2` | `code_separator_block` | two-block hyphen, non-numeric character included | URL/path/email, square bracket 내부이면 preserve | `기역 이` |
| `01-02` | `code_separator_block` | two-block numeric hyphen, leading zero condition | URL/path/email, square bracket 내부이면 preserve | `공일 공이` |
| `1234-5678` | `code_separator_block` | two-block numeric hyphen, 4+ digit condition | URL/path/email, square bracket 내부이면 preserve | `일이삼사 오육칠팔` |
| `1-2` | preserve | two-block numeric hyphen, no leading zero and no 4+ digit block | 항상 preserve | `1-2` |
| `12-15` | preserve | two-block numeric hyphen, no leading zero and no 4+ digit block | 항상 preserve | `12-15` |
| `123-456` | preserve | two-block numeric hyphen, no leading zero and no 4+ digit block | 항상 preserve | `123-456` |
| `1 - 2 - 3` | no code separator owner | spaced numeric hyphen multi-block, 다음 owner로 위임 | code separator owner 미적용 | `일 - 이 - 삼` 또는 일반 규칙 결과 |


### 9.12 Emergency Claim

대상:

```text
긴급번호 112는
화재가 나면 119에
```

Emergency context keywords:

- `긴급번호`
- `긴급`
- `신고`
- `응급`
- `구조`
- `출동`
- `경찰`
- `소방`
- `화재`
- `구급`
- `재난`
- `범죄`

Allowed tails:

- ``
- `은`
- `는`
- `이`
- `가`
- `을`
- `를`
- `에`
- `에서`
- `에게`
- `로`
- `으로`
- `와`
- `과`
- `도`
- `만`
- `부터`
- `까지`
- `처럼`

Disallowed suffix 예:

- `명`
- `건`
- `번`
- `호`
- alphabetic tail 전반

원칙:

- emergency context keyword 필요
- allowed tail 필요
- 둘 중 하나라도 없으면 emergency reading 금지
- `112명`, `119건`은 emergency digit reading 금지. 단, `명`/`건`은 explicit counter이므로 emergency gate fail 이후 counter policy를 적용한다.
- `1-1-9`는 emergency owner가 아니라 code separator block owner

Canonical reading table:

| 입력 표면 | context 필요 | allowed tail 필요 | canonical output |
|---|---:|---:|---|
| `긴급번호 112는` | 예 | 예 | `긴급번호 일일이는` |
| `화재가 나면 119에` | 예 | 예 | `화재가 나면 일일구에` |
| bare `112` | 아니오 | 해당 없음 | `백십이` |
| bare `119` | 아니오 | 해당 없음 | `백십구` |
| `112명` | 예여도 불가 | 아니오 | `백십이 명` |
| `119건` | 예여도 불가 | 아니오 | `백십구 건` |
| `112abc` | 아니오 | 아니오 | preserve |

#### 9.12.1 Public Number subtype

`public_number`는 `emergency` owner의 하위 subtype으로 구현한다. 공공번호도 bare number와 digit-by-digit reading을 구분해야 하므로 context gate를 통과해야 한다.

대상 후보:

| 번호 | 대표 context |
|---|---|
| `110` | `국민콜`, `정부민원`, `민원`, `상담` |
| `120` | `다산콜`, `시정`, `지자체`, `콜센터`, `상담` |
| `117` | `학교폭력`, `신고`, `상담` |
| `118` | `사이버`, `해킹`, `개인정보`, `신고`, `상담` |
| `1339` | `질병`, `감염병`, `응급의료`, `상담`, `문의` |
| `182` | `경찰민원`, `민원`, `경찰` |
| `125` | `밀수`, `관세`, `신고` |

원칙:

- number별 context whitelist를 가진다.
- gate 통과 시 digit-by-digit reading을 사용한다.
- gate 실패 시 general number fallback을 허용한다.
- alphabetic contamination이 있으면 preserve한다.

예:

```text
국민콜 110에 문의 -> 국민콜 일일공에 문의
110명 참석 -> 백십명 참석
다산콜 120은 -> 다산콜 일이공은
120명 -> 백이십명
질병 상담 1339에 문의 -> 질병 상담 일삼삼구에 문의
1339에 문의 -> 천삼백삼십구에 문의
```

### 9.13 Counter Claim

대상:

```text
21명
3개
2개월
21층
```

원칙:

- counter noun을 context로 읽는다.
- counter noun literal은 변경하지 않는다.
- counter table에 없는 noun은 broad native conversion 금지
- emergency ambiguity `112`, `119`는 counter override 대상에서 제외

Counter Policy Table:

| counter | mode | threshold | 예시 | 특이사항 |
|---|---|---:|---|---|
| `사람` | native_only | - | `두 사람` | 1~99 native path |
| `살` | native_only | - | `열세 살` | 1~99 native path |
| `개` | hybrid | 39 | `39개 -> 서른아홉 개` | 40부터 sino |
| `권` | hybrid | 39 | `39권 -> 서른아홉 권` | 40부터 sino |
| `장` | hybrid | 39 | `39장 -> 서른아홉 장` | 40부터 sino |
| `명` | hybrid | 39 | `39명 -> 서른아홉 명` | 40부터 sino |
| `마리` | hybrid | 39 | `39마리 -> 서른아홉 마리` | 40부터 sino |
| `그루` | hybrid | 39 | `39그루 -> 서른아홉 그루` | 40부터 sino |
| `송이` | hybrid | 39 | `39송이 -> 서른아홉 송이` | 40부터 sino |
| `자루` | hybrid | 39 | `39자루 -> 서른아홉 자루` | 40부터 sino |
| `알` | hybrid | 39 | `39알 -> 서른아홉 알` | 40부터 sino |
| `벌` | hybrid | 39 | `39벌 -> 서른아홉 벌` | 40부터 sino |
| `켤레` | hybrid | 39 | `39켤레 -> 서른아홉 켤레` | 40부터 sino |
| `그릇` | hybrid | 39 | `39그릇 -> 서른아홉 그릇` | 40부터 sino |
| `공기` | hybrid | 39 | `39공기 -> 서른아홉 공기` | 40부터 sino |
| `잔` | hybrid | 39 | `39잔 -> 서른아홉 잔` | 40부터 sino |
| `병` | hybrid | 39 | `39병 -> 서른아홉 병` | 40부터 sino |
| `조각` | hybrid | 39 | `39조각 -> 서른아홉 조각` | 40부터 sino |
| `차례` | hybrid | 39 | `39차례 -> 서른아홉 차례` | 40부터 sino |
| `건` | hybrid | 39 | `39건 -> 서른아홉 건` | 40부터 sino |
| `곳` | hybrid | 39 | `39곳 -> 서른아홉 곳` | 40부터 sino |
| `팀` | hybrid | 39 | `39팀 -> 서른아홉 팀` | 40부터 sino |
| `쌍` | hybrid | 39 | `39쌍 -> 서른아홉 쌍` | 40부터 sino |
| `상자` | hybrid | 39 | `39상자 -> 서른아홉 상자` | 40부터 sino |
| `봉지` | hybrid | 39 | `39봉지 -> 서른아홉 봉지` | 40부터 sino |
| `통` | hybrid | 39 | `39통 -> 서른아홉 통` | 40부터 sino |
| `묶음` | hybrid | 39 | `39묶음 -> 서른아홉 묶음` | 40부터 sino |
| `편` | hybrid | 39 | `39편 -> 서른아홉 편` | 40부터 sino |
| `판` | hybrid | 39 | `39판 -> 서른아홉 판` | 40부터 sino |
| `줄` | hybrid | 39 | `39줄 -> 서른아홉 줄` | 40부터 sino |
| `칸` | hybrid | 39 | `39칸 -> 서른아홉 칸` | 40부터 sino |
| `대` | hybrid | 39 | `39대 -> 서른아홉 대` | 40부터 sino |
| `석` | hybrid | 39 | `39석 -> 서른아홉 석` | 40부터 sino |
| `표` | hybrid | 39 | `39표 -> 서른아홉 표` | 40부터 sino |
| `매` | hybrid | 39 | `39매 -> 서른아홉 매` | 40부터 sino |
| `문항` | hybrid | 39 | `39문항 -> 서른아홉 문항` | 40부터 sino |
| `문제` | hybrid | 39 | `39문제 -> 서른아홉 문제` | 40부터 sino |
| `곡` | hybrid | 39 | `39곡 -> 서른아홉 곡` | 40부터 sino |
| `장면` | hybrid | 39 | `39장면 -> 서른아홉 장면` | 40부터 sino |
| `세트` | hybrid | 39 | `39세트 -> 서른아홉 세트` | 40부터 sino |
| `팩` | hybrid | 39 | `39팩 -> 서른아홉 팩` | 40부터 sino |
| `봉` | hybrid | 39 | `39봉 -> 서른아홉 봉` | 40부터 sino |
| `종류` | hybrid | 39 | `39종류 -> 서른아홉 종류` | 40부터 sino |
| `항목` | hybrid | 39 | `39항목 -> 서른아홉 항목` | 40부터 sino |
| `사례` | hybrid | 39 | `39사례 -> 서른아홉 사례` | 40부터 sino |
| `층` | sino_only | - | `21층 -> 이십일 층` | native 금지 |
| `호` | sino_only | - | `21호 -> 이십일 호` | native 금지 |
| `동` | sino_only | - | `21동 -> 이십일 동` | native 금지 |
| `년` | sino_only | - | `21년 -> 이십일년` | native 금지 |
| `월` | sino_only | - | `01월 -> 일월` | leading zero override |
| `일` | sino_only | - | `03일 -> 삼일` | leading zero override |
| `개월` | sino_only | - | `2개월 -> 이개월` | native 금지 |
| `원` | sino_only | - | `21원 -> 이십일 원` | currency-like label |
| `도` | sino_only | - | `21도 -> 이십일도` | degree-like label |
| `미터` | sino_only | - | `3미터 -> 삼 미터` | structured unit path와 연동 |
| `킬로그램` | sino_only | - | `3킬로그램 -> 삼 킬로그램` | structured unit path와 연동 |
| `학년` | sino_only | - | `2학년 -> 이학년` | native 금지 |
| `학기` | sino_only | - | `2학기 -> 이학기` | native 금지 |
| `회` | sino_only | - | `제62회 -> 제 육십이회` | numeric prefixed noun과 연동 |

Counter 100+ Sino policy:

- Counter number reading applies native/hybrid/sino behavior only for `1~99`.
- For all counters, if the numeric value is `100` or greater, the entire number is read in Sino-Korean.
- No tail-native reading is applied for `100+` counter values.
- Large counter numbers follow the large-number group spacing policy first; the counter literal is then appended with one space unless that counter is explicitly spaceless.

숫자+counter에서 `1~99`는 기존 counter별 고유어/native, hybrid threshold 39, 한자어 정책을 따른다. 하지만 `100` 이상은 counter 종류와 관계없이 숫자 전체를 한자어로 읽는다. `100` 이상에서는 마지막 두 자리만 고유어로 읽는 tail-native 방식을 사용하지 않는다.

아래 단위는 hybrid counter로 처리한다. `1~39`는 고유어 관형형, `40` 이상은 한자어로 읽는다. `100` 이상은 기존 100+ Sino counter policy에 따라 전체 숫자를 한자어로 읽는다.

```text
대, 석, 표, 매, 문항, 문제, 곡, 장면, 세트, 팩, 봉, 종류, 항목, 사례
```

이번 단위 추가는 counter reading만 확장한다. `제N+단위` ordinal explicit target은 확장하지 않는다. `쪽`, `부`는 이번 hybrid counter 추가 대상에서 제외한다.

예:

```text
21명 -> 스물한 명
31명 -> 서른한 명
39명 -> 서른아홉 명
40명 -> 사십 명
99명 -> 구십구 명
100명 -> 백 명
101명 -> 백일 명
112명 -> 백십이 명
119건 -> 백십구 건
139명 -> 백삼십구 명
140명 -> 백사십 명
31권 -> 서른한 권
39권 -> 서른아홉 권
40권 -> 사십 권
31장 -> 서른한 장
39장 -> 서른아홉 장
40장 -> 사십 장
31개 -> 서른한 개
39개 -> 서른아홉 개
40개 -> 사십 개
39마리 -> 서른아홉 마리
40마리 -> 사십 마리
39그루 -> 서른아홉 그루
40그루 -> 사십 그루
39송이 -> 서른아홉 송이
40송이 -> 사십 송이
39자루 -> 서른아홉 자루
40자루 -> 사십 자루
39알 -> 서른아홉 알
40알 -> 사십 알
39벌 -> 서른아홉 벌
40벌 -> 사십 벌
39켤레 -> 서른아홉 켤레
40켤레 -> 사십 켤레
39그릇 -> 서른아홉 그릇
40그릇 -> 사십 그릇
39공기 -> 서른아홉 공기
40공기 -> 사십 공기
39잔 -> 서른아홉 잔
40잔 -> 사십 잔
39병 -> 서른아홉 병
40병 -> 사십 병
39조각 -> 서른아홉 조각
40조각 -> 사십 조각
2차례 -> 두 차례
20차례 -> 스무 차례
30차례 -> 서른 차례
31차례 -> 서른한 차례
39차례 -> 서른아홉 차례
40차례 -> 사십 차례
2 차례 -> 두 차례
20 차례 -> 스무 차례
31 차례 -> 서른한 차례
40사람 -> 마흔 사람
99사람 -> 아흔아홉 사람
100사람 -> 백 사람
101사람 -> 백일 사람
139사람 -> 백삼십구 사람
140사람 -> 백사십 사람
40살 -> 마흔 살
99살 -> 아흔아홉 살
100살 -> 백 살
101살 -> 백일 살
139살 -> 백삼십구 살
140살 -> 백사십 살
2건 -> 두 건
39건 -> 서른아홉 건
40건 -> 사십 건
99건 -> 구십구 건
100건 -> 백 건
101건 -> 백일 건
139건 -> 백삼십구 건
140건 -> 백사십 건
2곳 -> 두 곳
39곳 -> 서른아홉 곳
40곳 -> 사십 곳
2팀 -> 두 팀
39팀 -> 서른아홉 팀
40팀 -> 사십 팀
2쌍 -> 두 쌍
39쌍 -> 서른아홉 쌍
40쌍 -> 사십 쌍
2상자 -> 두 상자
40상자 -> 사십 상자
2봉지 -> 두 봉지
40봉지 -> 사십 봉지
2통 -> 두 통
40통 -> 사십 통
2묶음 -> 두 묶음
40묶음 -> 사십 묶음
2편 -> 두 편
40편 -> 사십 편
101차례 -> 백일 차례
101편 -> 백일 편
101권 -> 백일 권
101장 -> 백일 장
101개 -> 백일 개
12,345명 -> 만 이천삼백사십오 명
123,456명 -> 십이만 삼천사백오십육 명
12,345,678,901,234명 -> 십이조 삼천사백오십육억 칠천팔백구십만 천이백삼십사 명
2판 -> 두 판
40판 -> 사십 판
2줄 -> 두 줄
40줄 -> 사십 줄
2칸 -> 두 칸
40칸 -> 사십 칸
2대 -> 두 대
39대 -> 서른아홉 대
40대 -> 사십 대
101대 -> 백일 대
2항목 -> 두 항목
39항목 -> 서른아홉 항목
40항목 -> 사십 항목
101항목 -> 백일 항목
2사례 -> 두 사례
39사례 -> 서른아홉 사례
40사례 -> 사십 사례
101사례 -> 백일 사례
2종류 -> 두 종류
39종류 -> 서른아홉 종류
40종류 -> 사십 종류
101종류 -> 백일 종류
2항목abc -> 2항목abc
2사례test -> 2사례test
2종류A -> 2종류A
A2항목 -> A2항목
model-2대 -> model-2대
21층 -> 이십일 층
2개월 -> 이개월
```

### 9.14 Administrative Suffix Claim

이것은 새로 추가하는 보강 owner다.

대상:

```text
종로3가
역삼동 12번지
강남대로 21길
```

owner:

```text
administrative_suffix
```

허용 조건:

- 좌측에 지명/주소 후보가 있어야 한다.
- 숫자와 행정 suffix가 붙어 있거나 주소 패턴으로 full consume되어야 한다.
- suffix는 whitelist에 있어야 한다.
- suffix 뒤 boundary가 안전해야 한다.
- 조사로 해석될 가능성이 크면 preserve 또는 다른 owner로 fallback한다.
- counter/sino label owner와 충돌하면 더 명시적인 문맥이 있는 owner를 선택한다.

suffix whitelist 후보:

```text
가
동
로
길
번지
호
```

예:

```text
종로3가 -> 종로삼가
역삼동 12번지 -> 역삼동 십이번지
```

주의 케이스:

```text
3가 맞다
21호
12로 나누다
```

이들은 행정 suffix로 무조건 처리하면 안 된다. 정책 결정 전까지 preserve 또는 기존 counter/sino path를 따른다.

### 9.15 Mathematical Numeric Claim

수학적 수치는 필요하지만 event/date/unit보다 앞서면 안 된다.

대상:

```text
1/2
3.14
+10
-5.2
```

순서:

```text
date / time / event / unit / currency / pH / compound unit 이후
general number 이전
```

원칙:

- full consume 필요
- unsupported notation preserve
- scientific notation은 지원 전까지 preserve
- event dotted form이나 date dotted form을 decimal로 먼저 소비하지 않는다.

예:

```text
3.14 -> 삼쩜일사
1/2 -> 이분의 일
1e6 -> preserve
3.2E-4 -> preserve
```


### 9.16 Dotted Decimal Fallback

`M.D`, `MM.D`, `M.DD`, `MM.DD` 형태는 event/date 조건을 만족하지 않을 경우 decimal numeric으로 처리한다.

원칙:

- `.`은 decimal point로 읽는다.
- 숫자 core만 변환하고 한글 tail은 보존한다.
- contamination으로 간주하지 않는다.

예:

12.3 -> 십이쩜삼
7.25 -> 칠쩜이오
10.5 -> 십쩜오
3.14 -> 삼쩜일사
12.03 -> 십이쩜영삼
0.125 -> 영쩜일이오

12.3수치 -> 십이쩜삼수치
3.14값 -> 삼쩜일사값
7.25자료 -> 칠쩜이오자료
12.3-수치 -> 십이쩜삼-수치


### 9.17 Middle-dot Numeric Block Fallback

`M·D` 형태는 decimal이 아니라 numeric block separator로 처리한다.

원칙:

- 각 block은 digit-sequence reading으로 읽는다.
- block 사이에 공백을 둔다.
- middle dot 자체는 GENERATED_READING으로 출력하지 않는다.

예:

12·3 -> 십이 삼
7·25 -> 칠 이오
10·5 -> 십 오
1·2·3 -> 일 이 삼
123·456 -> 일이삼 사오육

12·3수치 -> 십이 삼수치
7·25자료 -> 칠 이오자료
12·3-수치 -> 십이 삼-수치


### 9.18 Spaced Separator Handling

숫자와 separator 사이에 공백이 있는 경우 event/date/decimal/middle-dot full consume을 적용하지 않는다. 그러나 이것은 항상 Absolute Preserve를 의미하지 않는다. 공백 separator surface는 다음 후보 owner 또는 일반 fallback으로 넘길 수 있으며, 최종적으로 어떤 owner도 처리하지 못할 때만 Terminal Fallback Preserve로 원문 출력한다.

원칙:

- 두 블럭 spaced separator는 separator와 공백을 원문 그대로 유지하고 각 token을 독립 fallback으로 평가한다.
- 세 블럭 이상 spaced hyphen numeric block은 `9.24.6`의 spaced hyphen numeric multi-block 정책을 우선 적용한다.
- URL/path/email/code-like 내부의 spaced separator는 Absolute Preserve이다.

예:

```text
12 .3 -> 십이 .삼
12. 3 -> 십이. 삼
12 · 3 -> 십이 · 삼
12 · 3 수치 -> 십이 · 삼 수치
010 - 1234 - 5678 -> 공일공 천이백삼십사 오천육백칠십팔
```

금지:

```text
12 . 3 -> 십이쩜삼
1 / 3 -> 삼분의 일
```

### 9.19 General Number Claim

모든 특수 owner가 실패한 뒤 마지막으로 순수 숫자를 처리한다.

대상:

```text
123
2025
0012
```

원칙:

- general fallback은 최후순위
- 이전 owner가 Absolute Preserve claim한 구간에는 재진입 금지
- 이전 owner가 Owner Fallback Candidate로 넘긴 구간은 다음 후보 owner 또는 general fallback이 평가할 수 있다
- multi-digit integer가 `0`으로 시작하면 일반 수량 숫자로 읽지 않고 code digit reading 후보로 넘긴다
- leading zero 정책은 별도 table로 명시
- owner가 불분명한 mixed token은 general number가 일부만 소비하면 안 된다.


### 9.20 Claim Conflict Algorithm

`더 좁고 명시적인 owner 우선` 원칙은 다음 함수 계약으로 구현한다.

```python
ClaimPriority = int
SpecificityScore = int
TieBreakPolicy = Literal["preserve", "earlier_owner", "longer_span"]
```

`can_claim(span, owner)` 규칙:

1. lock/shadow overlap이면 reject한다.
2. existing Absolute Preserve claim overlap이면 reject한다.
3. existing surface claim overlap이면 priority를 비교한다.
4. 새 claim priority가 더 높고 기존 claim이 reentry를 허용하면 교체할 수 있다.
5. priority가 같으면 Terminal Fallback Preserve로 처리하거나 필요한 경우 Absolute Preserve claim으로 대체한다.
6. nested claim은 parent가 `allow_reentry=True`일 때만 허용한다.
7. generated surface 내부에는 새 claim을 만들 수 없다.
8. claim 교체가 발생하면 collision_log에 남긴다.

기본 priority는 Surface Claim 우선순위 표를 따른다. 동일 owner 내부에서는 longer span을 우선하되, unsafe partial consume 가능성이 있으면 preserve한다.

### 9.21 Signed Temperature / Signed Degree Claim

주의: bare Korean `도` 입력의 문맥 추론은 현재 정책 범위가 아니다. `서울 -1.3도`처럼 기상 문맥상 `영하`가 자연스러워도, `℃/℉/ºC/ºF/º` 같은 명시 signed temperature/degree surface가 아니면 broad weather inference를 적용하지 않는다.


signed temperature / signed degree는 `math_numeric` 또는 `unit`에 흡수하지 않고 별도 owner로 claim한다.

대상:

```text
-2.5℃
+3℃
-2.5º
+3º
-3°
+3°
```

원칙:

- sign + number + degree/temperature symbol 전체 full consume
- sign은 숫자와 붙어 있을 때만 signed temperature / signed degree로 본다.
- signed temperature / signed degree surface의 claim 대상은 sign부터 degree/temperature symbol까지의 core span이다. 앞에 붙은 한글 label은 generated reading으로 덮어쓰지 않고 ORIGINAL_KOREAN으로 보존한다.
- signed temperature / signed degree는 문장 시작, 공백, 한글, 일반 문장부호 또는 일반 delimiter 뒤에서 claim할 수 있다.
- signed temperature / signed degree는 ASCII 영문자, ASCII 숫자, code-like token body 바로 뒤에서는 claim하지 않는다. 이 경우 code/model/identifier 일부일 수 있으므로 preserve한다.
- sign이 없으면 온도/각도 모두 `영상`, `영하`, `플러스`, `마이너스` prefix를 붙이지 않는다.
- temperature 계열 `℃`, `ºC`, `°C`에 붙은 `-`는 `영하`로 읽는다.
- temperature 계열 `℃`, `ºC`, `°C`에 붙은 `+`는 `영상`으로 읽는다.
- bare `º`는 signed case에서 temperature-like bare degree로 보아 `영상/영하 ...도`로 읽는다.
- angle degree `°`에 붙은 `-`는 기존 signed degree 정책대로 `마이너스 ...도`로 읽는다.
- angle degree `°`에 붙은 `+`는 기존 signed degree 정책대로 `플러스 ...도`로 읽는다.
- sign과 number 사이에 공백이 있으면 signed temperature / signed degree surface가 아니다.
- invalid decimal length 또는 trailing contamination이면 preserve한다.
- full consume 실패 후 숫자만 변환하고 원래 degree/temperature symbol을 남기는 partial rewrite는 금지한다.

예:

```text
25º -> 이십오도
25° -> 이십오도
-2.5℃ -> 영하 이쩜오도
온도-2.5℃ -> 온도영하 이쩜오도
값은 -2.5℃다 -> 값은 영하 이쩜오도다
+3℃ -> 영상 삼도
-2.5º -> 영하 이쩜오도
+3º -> 영상 삼도
- 3° -> - 삼도
+3ºCat -> +3ºCat
A-2.5º -> A-2.5º
A-2.5℃ -> A-2.5℃
x-2.5℉ -> x-2.5℉
A-2.5º -> A-2.5º
온도-2.5℃ -> 온도-이쩜오℃  [forbidden]
```

### 9.22 JAMO_SURFACE Claim

`JAMO_SURFACE`는 단독 compatibility jamo 또는 연속 compatibility jamo를 표준 자모 명칭으로 읽기 위한 owner다.

Claim 위치:

- dictionary/acronym 이후
- mathematical/general number 이전

원칙:

- 단독 compatibility jamo 또는 연속 compatibility jamo만 claim한다.
- 완성형 한글 음절은 자모 분해하지 않는다.
- mixed token 내부 자모는 preserve한다.
- 모델명, 코드, emoticon, placeholder 일부로 보이면 preserve한다.

예:

```text
ㄱ -> 기역
ㄱㄴㄷ -> 기역 니은 디귿
AㄱB -> preserve
```

### 9.23 Large Unit Atomic Claim

Large unit owner는 숫자 + 대단위 결합을 atomic하게 처리한다.

대상:

```text
1만
1억
10조
3경
1억 원
10조원
```

원칙:

- Arabic number surface에서 생성된 large unit reading만 처리한다.
- 한글로 입력된 `이 억` 같은 표현은 원문 보존한다.
- 한글-한글 공백 repair를 하지 않는다.
- partial consume으로 `육천사백이 억` 같은 signature를 만들면 안 된다.

예:

```text
1억 -> 일억
10조 -> 십조
1억 원 -> 일억 원
이 억 -> 이 억
```

현재 large-unit 결정은 bare large-unit lexical form뿐 아니라 valid comma
integer, signed decimal, mixed Arabic-Hangul numeric surface까지 확장한다.
KRW `원` currency noun이 붙어도 large-unit numeric core를 먼저 읽고 `원`은
뒤따르는 일반 noun/tail로 둔다.

- decimal large-unit lexical form은 semantic amount로 확장하지 않는다.
- `3.5만`과 `3.5만 원`은 numeric surface를 그대로 읽고 suffix 앞을 띄운다.
- semantic expansion `3.5만 -> 삼만 오천`은 여전히 범위 밖이다.

canonical:

```text
3.5만 -> 삼쩜오 만
3.5만 원 -> 삼쩜오 만 원
1.2억 원 -> 일쩜이 억 원
3.5만 -> 삼만 오천  # 금지: 원 currency noun 없는 bare form은 semantic expansion 대상 아님
```

### 9.23.1 Mixed Large Unit Counter / Currency Surface

대상:

```text
2만 3,000명
1억 2,500만 원
3조 4,000억 원
6,402억 달러
8만 9천 개
```

원칙:

1. Arabic number + large unit chunk와 following numeric chunk가 하나의 수량 표현을 구성하면 전체를 하나의 numeric quantity surface로 claim할 수 있다.
2. counter, currency, unit, noun suffix가 뒤따르면 partial consume을 금지한다.
3. 앞 large unit chunk만 preserve하고 뒤 숫자만 변환하는 출력은 금지한다.
4. 원문에 존재하는 한글 large unit literal과 공백은 provenance를 유지해야 한다.
5. generated reading과 original Korean suffix/counter는 RenderPiece로 분리한다.
6. full consume에 실패하면 전체 preserve 또는 더 작은 안전 owner로 fallback하되, raw residue를 남기면 안 된다.

canonical output:

```text
2만 3,000명 -> 이만 삼천 명
1억 2,500만 원 -> 일억 이천오백만 원
3조 4,000억 원 -> 삼조 사천억 원
6,402억 달러 -> 육천사백이억 달러
8만 9천 개 -> 팔만 구천 개
```

금지:

```text
2만 3,000명 -> 2만 삼천 명
1억 2,500만 원 -> 일억 2,500만 원
3조 4,000억 원 -> 삼조 4,000억 원
6,402억 달러 -> 육천사백이 억 달러
8만 9천 개 -> 8만 구천 개
```

### 9.24 Code Separator Block Surface

`CODE_SEPARATOR_BLOCK_SURFACE`는 숫자/영문/완성형 한글/한글 자모가 `-`, `.`, `/`로 결합된 코드형 표기를 읽기 위한 owner다. 이 owner는 실사용 TTS에서 코드형 블럭을 적극적으로 읽기 위한 정책이며, 특히 invalid full date-like token의 기존 preserve 방침을 확장한다.

#### 9.24.1 지원 구분자

지원 구분자는 다음 3개다.

```text
-
.
/
```

`#`는 이 owner의 대상이 아니다.

#### 9.24.2 날짜형 3종 우선

다음 형식은 항상 날짜 owner가 먼저 검사한다.

```text
####-##-##
####/##/##
####.##.##
```

유효 날짜이면 날짜로 읽는다.

```text
2026-04-17 -> 이천이십육년 사월 십칠일
2026/04/17 -> 이천이십육년 사월 십칠일
2026.04.17 -> 이천이십육년 사월 십칠일
```

유효 날짜가 아니면 `CODE_SEPARATOR_BLOCK_SURFACE` fallback을 평가한다. 이 정책은 기존 invalid date preserve 방침을 변경한다.

```text
2025-13-03 -> 이공이오 일삼 공삼
2025/13/03 -> 이공이오 일삼 공삼
2025.13.03 -> 이공이오쩜 일삼쩜 공삼
```

단, square bracket 내부, URL/path/email/code 보호 구간, alphabetic tail, mixed separator, 구분자 주변 공백이 있으면 이 fallback은 적용하지 않는다.

#### 9.24.3 세 블럭 이상

세 블럭 이상이 동일 구분자로 공백 없이 연결되어 있으면 `CODE_SEPARATOR_BLOCK_SURFACE`를 적용한다.

조건:

1. 블럭 수가 3개 이상이다.
2. 모든 구분자가 동일하다.
3. 구분자 좌우에 공백이 없다.
4. 각 블럭은 비어 있지 않다.
5. 각 블럭은 숫자/영문/완성형 한글/한글 자모를 혼합할 수 있다.
6. 블럭 길이는 달라도 된다.
7. 한 글자 블럭도 허용한다.
8. 전체 token을 full consume해야 한다.
9. URL/path/email, square bracket 내부가 아니다.
10. 더 구체적인 owner가 있으면 그 owner가 우선한다.

읽기 원칙:

- 숫자, 영문, 자모는 한 글자씩 읽는다.
- 완성형 한글은 원문 literal을 그대로 출력한다.
- `-`와 `/`는 출력하지 않고 블럭 사이를 공백으로 렌더링한다.
- `.`는 각 구분자를 `쩜 `으로 렌더링한다.
- code separator owner가 소비한 separator span은 trace 또는 RenderPiece provenance에 반드시 기록한다.

예:

```text
12-34-56 -> 일이 삼사 오육
12/34/56 -> 일이 삼사 오육
12.34.56 -> 일이쩜 삼사쩜 오육
1.2.3 -> 일쩜 이쩜 삼
A-B-C -> 에이 비 씨
가-나-다 -> 가 나 다
ㄱ-ㄴ-ㄷ -> 기역 니은 디귿
A1-ㄱ2-나B3 -> 에이 일 기역 이 나 비 삼
```

separator provenance / trace:

1. `-`와 `/`
   - 원본 separator는 normalized_text에 출력하지 않는다.
   - 해당 source span은 `SEPARATOR_CONSUMED`로 기록한다.
   - block 사이에 생성되는 공백은 `GENERATED_BOUNDARY` 또는 `GENERATED_READING`으로 기록할 수 있다.
   - 이 소비는 원본 boundary 누락이 아니라 `code_separator_block` owner의 명시 변환이다.

2. `.`
   - 원본 separator source span은 `GENERATED_READING("쩜 ")` piece로 대응한다.
   - owner는 `code_separator_block`으로 기록한다.

예:

A-B-C
-> A: GENERATED_READING("에이")
-> -: SEPARATOR_CONSUMED
-> B: GENERATED_READING("비")
-> -: SEPARATOR_CONSUMED
-> C: GENERATED_READING("씨")
-> output: 에이 비 씨

12.34.56
-> 12: GENERATED_READING("일이")
-> .: GENERATED_READING("쩜 ")
-> 34: GENERATED_READING("삼사")
-> .: GENERATED_READING("쩜 ")
-> 56: GENERATED_READING("오육")
-> output: 일이쩜 삼사쩜 오육


#### 9.24.4 두 블럭: `.` 또는 `/`

두 블럭에서 구분자가 `.` 또는 `/`이면 `CODE_SEPARATOR_BLOCK_SURFACE`로 바로 처리하지 않고 다음 owner 판단으로 넘긴다.

- `.` 두 블럭은 decimal, event gate, 단위, 일반 숫자 등 더 구체적인 규칙이 먼저 판단한다.
- `/` 두 블럭은 fraction, unit, path protection 등 더 구체적인 규칙이 먼저 판단한다.
- 어느 규칙에도 걸리지 않으면 숫자/한글/영어/자모는 일반 규칙대로 읽고, 구분자는 원문 그대로 유지한다.
- 구분자 주변에 공백이 있으면 decimal/fraction/code separator owner를 적용하지 않고 부분별 일반 규칙으로 넘긴다.

예:

```text
3.14 -> 삼쩜일사
12 . 3 -> 십이 . 삼
12. 3 -> 십이. 삼
12 .3 -> 십이 .삼
1/3 -> 삼분의 일
4/7 -> 칠분의 사
1 / 3 -> 일 / 삼
A / B -> 에이 / 비
가 / 나 -> 가 / 나
```

#### 9.24.5 두 블럭: `-`

두 블럭 하이픈은 가장 애매하므로 별도 조건을 둔다.

공백이 있으면 code separator owner를 적용하지 않고 다음 규칙으로 넘긴다. 전체 preserve claim도 하지 않는다.

```text
1 - 2 -> 일 - 이
A - 3 -> 에이 - 삼
A - B -> 에이 - 비
ㄱ - ㄴ -> 기역 - 니은
가 - 나 -> 가 - 나
```

#### 9.24.5.0 Single-letter uppercase alnum code policy

Single-letter uppercase alnum code handling is owner-scoped. A token of the form one uppercase letter, optional hyphen, integer digits, and optional uppercase alphabet tail of one or two letters may be normalized when the owner can fully consume the token and both boundaries are safe. The first letter is read as a Korean alphabet name. The numeric part is read with English digit names for 1-9 and Sino-Korean numbers for 10 and above. A final uppercase tail of one or two letters is read letter-by-letter. The owner must not partially rewrite unsafe/code-like tails.

A~Z 한 글자 뒤에 optional hyphen과 정수가 붙은 code token은 안전한 boundary에서 전체 token을 소비할 수 있을 때 교정한다. 숫자가 1~9이면 영어식 숫자명으로 읽고, 10 이상이면 한자어 숫자로 읽는다. 숫자 뒤 uppercase alphabet tail 1~2자는 한 글자씩 읽는다. unsafe tail, lowercase tail, multi-letter prefix, URL/path/email 내부는 이 owner가 claim하지 않는다. 우측에 완성형 한글 조사/어미가 바로 이어지는 경우에는 code token 자체만 full consume하고 한글 suffix는 원문 한글로 보존한다.

대상 형식:

```text
^[A-Z]-?[0-9]+[A-Z]{0,2}$
```

canonical output:

```text
K-1 -> 케이 원
K1 -> 케이 원
K-9 -> 케이 나인
K9 -> 케이 나인
K-10 -> 케이 십
K10 -> 케이 십
K-21 -> 케이 이십일
K21 -> 케이 이십일

A-1 -> 에이 원
A1 -> 에이 원
A-10 -> 에이 십
A10 -> 에이 십

B-1 -> 비 원
B1 -> 비 원
B-10 -> 비 십
B10 -> 비 십

K-1A -> 케이 원 에이
K1A -> 케이 원 에이
K-21B -> 케이 이십일 비
K21B -> 케이 이십일 비
F-15C -> 에프 십오 씨
F15C -> 에프 십오 씨
K-21BC -> 케이 이십일 비씨
A-10C -> 에이 십 씨
장비는 F-15C입니다 -> 장비는 에프 십오 씨입니다
```

preserve / non-target examples:

```text
AA-10 -> AA-10
AB10 -> AB10
A-10CAT -> A-10CAT
A10CAT -> A10CAT
A-3kg -> A-3kg
A3kg -> A3kg
APIv2 -> APIv2
GPU2X -> GPU2X
USB300 -> USB300
model-X200 -> model-X200
X-200-beta -> X-200-beta
R2D2 -> R2D2
K-2024 -> K-2024
K-ABC -> K-ABC
K-pop -> K-pop
https://example.com/K-1 -> preserve
docs/K-1/report.md -> preserve
```

정책 충돌 결정:

- `A-10C`는 이번 정책으로 preserve에서 교정 대상으로 바뀐다.
- `A-3kg`는 lowercase/unit-like tail이므로 preserve한다.
- `K-2024`는 K-year/code preserve 결정을 유지한다.
- `K-한글` owner와 `K-POP` fixed dictionary는 기존대로 유지한다.

공백 없이 붙어 있고 두 블럭 중 하나라도 한글, 영문, 자모 등 숫자 이외 문자를 포함하면 코드 읽기를 적용한다. 이때 `-`는 출력하지 않고 블럭 사이 공백으로 렌더링한다.

```text
A-1 -> 에이 원
A-나 -> 에이 나
가-3 -> 가 삼
ㄱ-2 -> 기역 이
A1-B2 -> 에이 일 비 이
가1-나2 -> 가 일 나 이
AB-12 -> 에이 비 일이
12-AB -> 일이 에이 비
```

두 블럭이 모두 숫자이고 공백 없이 붙어 있을 때는 아래 조건 중 하나라도 만족하면 코드 읽기를 적용한다.

조건 A: 한 블럭이라도 `0`으로 시작한다.

```text
01-02 -> 공일 공이
001-23 -> 공공일 이삼
12-034 -> 일이 공삼사
00-10 -> 공공 일공
```

조건 B: 한 블럭이라도 4자리 이상이다.

```text
1234-56 -> 일이삼사 오육
12-3456 -> 일이 삼사오육
1234-5678 -> 일이삼사 오육칠팔
2026-0417 -> 이공이육 공사일칠
```

두 블럭이 모두 숫자이고 위 조건에 해당하지 않으면 원문 그대로 유지한다. 이 케이스들은 범위, 점수, 빼기, 장-절, 모델 코드 등으로 자주 겹치기 때문이다.

```text
1-2 -> 1-2
3-2 -> 3-2
12-15 -> 12-15
10-20 -> 10-20
123-456 -> 123-456
```

#### 9.24.5.1 Two-block hyphen decimal-containing block policy

두 블럭 hyphen에서 공백 없이 붙어 있고, 한쪽 block에 숫자 이외 문자(영문, 완성형 한글, 한글 자모)가 포함되어 있으며, 다른쪽 block이 정수 또는 소수이면 `CODE_SEPARATOR_BLOCK_SURFACE`를 적용한다.

이때 오른쪽 또는 왼쪽의 decimal-containing numeric block은 하나의 block 내부 reading으로 허용한다.

원칙:

1. 두 블럭 hyphen이다.
2. 구분자 `-` 좌우에 공백이 없다.
3. 두 블럭 중 한쪽 이상에 숫자 이외 문자(영문, 완성형 한글, 한글 자모)가 포함된다.
4. 다른쪽 block은 정수 또는 소수일 수 있다.
5. decimal-containing block은 `쩜`을 사용해 읽는다.
6. `-`는 출력하지 않고 block 사이 공백으로 렌더링한다.
7. 전체 token을 full consume해야 한다.
8. URL/path/email/code protection 내부이면 적용하지 않는다.
9. alphabetic tail 또는 단위/온도 tail이 붙어 full consume이 불가능하면 preserve한다.

canonical output:
```text
B-2.5 -> 비 이쩜오
A-3.14 -> 에이 삼쩜일사
x-3 -> 엑스 삼
ㄱ-2.5 -> 기역 이쩜오
가-3.14 -> 가 삼쩜일사
```


preserve output:
```text
B-2.5beta -> B-2.5beta
x-2.5℉ -> x-2.5℉
A-3kg -> A-3kg
```

금지:

```text
B-2.5 -> B-2.5
B-2.5 -> 비-이쩜오
B-2.5 -> 비 이.5
x-2.5℉ -> 엑스 화씨 이쩜오도
```
#### 9.24.6 공백 있는 구분자

공백 있는 구분자는 기본적으로 해당 code separator owner를 적용하지 않는다. 다만 현재 정책에서 `숫자 - 숫자 - 숫자` 형태의 세 블럭 이상 spaced hyphen numeric block은 별도 owner-local 정책으로 처리한다.

##### 기본 공백 separator fallback

두 블럭이거나 숫자 세 블럭 조건을 만족하지 않는 경우, 구분자와 공백은 원문 그대로 유지하고 다음 owner와 일반 fallback이 각각 판단한다. 이 상태는 Absolute Preserve가 아니라 Owner Fallback Candidate이다. 단, URL/path/email/code-like 내부이면 Absolute Preserve이다.

canonical output:

```text
12 . 3 -> 십이 . 삼
1 / 3 -> 일 / 삼
12 - 34 -> 십이 - 삼십사
A - B -> 에이 - 비
A - 3 -> 에이 - 삼
ㄱ - ㄴ -> 기역 - 니은
가 - 나 -> 가 - 나
```

금지:

```text
A - B -> A - B
A - 3 -> A - 삼
12 . 3 -> 십이쩜삼
1 / 3 -> 삼분의 일
```

##### Spaced hyphen numeric multi-block

세 블럭 이상이고 모든 블럭이 pure numeric 또는 decimal numeric이면 spaced hyphen numeric multi-block으로 처리한다. 이 처리는 전화번호 추론이 아니라 숫자 블럭 읽기 정책이다.

원칙:

- 블럭 수는 3개 이상이어야 한다.
- separator는 `-`, `−`, `－` 중 owner-local 허용 범위만 사용한다.
- separator 좌우 ASCII space는 허용한다.
- block이 `0`으로 시작하는 pure digit이면 code digit reading으로 읽는다.
- 그 외 pure digit block은 일반 숫자 reading으로 읽는다.
- decimal block은 decimal reading을 따른다.
- separator는 출력하지 않고 블럭 사이를 공백으로 렌더링한다.
- unsafe tail, alphabetic contamination, URL/path/email/code-like context는 Absolute Preserve 또는 Terminal Fallback Preserve로 처리한다.

canonical output:

```text
010 - 1234 - 5678 -> 공일공 천이백삼십사 오천육백칠십팔
001 - 23 - 456 -> 공공일 이십삼 사백오십육
0.5 - 1.2 - 3 -> 영쩜오 일쩜이 삼
```

Terminal Fallback Preserve examples:

```text
010 - ABC - 5678 -> 010 - ABC - 5678
010 - 1234 - 5678abc -> 010 - 1234 - 5678abc
```

#### 9.24.7 구분자가 섞인 경우

한 token 안에서 구분자가 섞이면 code separator owner는 적용하지 않는다. 다음 규칙으로 넘기고, 해당되는 owner가 없으면 구분자는 그대로 유지한다.

```text
12-34.56
A-B/C
1.2/3
2025-13/03
```

#### 9.24.8 보호 owner 우선

다음 owner는 `CODE_SEPARATOR_BLOCK_SURFACE`보다 항상 먼저 처리한다.

```text
1. square bracket protection
2. URL/path/email/protected code context
3. fixed dictionary / lexical compound
4. event owner
5. date owner
```

예:

```text
[12-34-56] -> 12-34-56
[2025-13-03] -> 2025-13-03
https://example.com/2026/04/17 -> preserve
docs/2026/04/17/report.md -> preserve
A12.3B -> A12.3B
2025-13-03B -> 2025-13-03B
```

주의:
* `square bracket protection`은 claim phase 전에 등록되므로 URL/path/email보다도 먼저 내부 재진입을 차단한다.
* `URL/path/email/protected code context`는 모든 code-like token을 broad하게 보호하는 owner가 아니다.
* `A-1`은 protected code context가 선점하지 않고 `single_letter_alnum_code` 후보로 넘긴다. `A-B-C`, `01-02`, `1234-5678`, `123-456-7890`, `1-1-9`는 protected code context가 선점하지 않고 `CODE_SEPARATOR_BLOCK_SURFACE` 후보로 넘긴다.


#### 9.24.9 최종 요약

```text
1. ####-##-##, ####/##/##, ####.##.##는 날짜 owner가 먼저 검사한다.
2. 유효 날짜이면 날짜로 읽고, 유효하지 않으면 코드형 블럭 읽기로 fallback한다.
3. 세 블럭 이상 + 동일 구분자(-, ., /) + 공백 없음이면 CODE_SEPARATOR_BLOCK_SURFACE 적용.
4. 세 블럭 이상에서 '-'와 '/'는 구분자를 생략하고 블럭 사이 공백으로 렌더링한다.
5. 세 블럭 이상에서 '.'는 각 구분자를 '쩜 '으로 렌더링한다.
6. 블럭 내부는 숫자/영문/완성형 한글/자모 혼합 가능하며 길이 제한 없음.
7. 숫자·영문·자모는 한 글자씩 읽고, 완성형 한글은 원문 그대로 출력한다.
8. 두 블럭에서 '.'와 '/'는 CODE_SEPARATOR_BLOCK 대상이 아니며 다음 owner로 넘긴다.
9. 두 블럭 '-'는 공백 없이 붙어 있고, 한쪽이라도 숫자 외 문자 포함이면 코드 읽기.
10. 두 블럭 '-'가 모두 숫자이면, 한쪽이라도 0으로 시작하거나 4자리 이상이면 코드 읽기.
11. 두 블럭 '-'가 모두 숫자이고 위 조건에 해당하지 않으면 원문 그대로 유지한다.
12. 구분자 주변에 공백이 있으면 code separator owner만 미적용하고 다음 owner로 넘긴다.
13. 어느 규칙에도 걸리지 않으면 숫자/영문/한글/자모는 일반 규칙대로 읽고, 구분자와 공백은 원문 그대로 유지한다.
```
## 10. Phase 4 — Owner-first Gate Routing

Claim이 끝나면 각 surface는 owner를 갖는다. 이후 parser는 owner에 따라 gate를 통과해야 한다.

### 10.1 GateDecision

```python
@dataclass
class GateDecision:
    passed: bool
    gate_name: str
    owner: str
    span: SourceSpan
    reason: str
    action_on_fail: Literal[
        "preserve",
        "fallback_to_number",
        "fallback_to_owner",
        "fallback_to_code_separator_block",
        "fallback_to_next_candidate",
        "terminal_preserve",
        "block_reentry",
    ]
    metadata: dict[str, Any] = field(default_factory=dict)
```

`fallback_to_code_separator_block`는 일반 owner 재진입이 아니다.  
`date_time.date`가 우선 claim한 `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY.MM.DD` exact `4-2-2` span에 대해, calendar validity 실패가 확인되고 fallback guard를 모두 통과한 경우에만 date gate/parser 내부에서 실행하는 제한적 fallback action이다.

### 10.2 Gate Registry

```python
class GateRegistry:
    def evaluate(
        self,
        gate_name: str,
        candidate: SurfaceCandidate,
        context: ParseContext,
    ) -> GateDecision:
        ...
```

Gate는 parser 내부 조건문이 아니라 registry에서 관리한다.

필수 gate:

- `date_hyphen_yyyy_mm_dd_gate`
- `date_slash_yyyy_mm_dd_gate`
- `date_dotted_yyyy_mm_dd_gate`
- `time_colon_context`
- `time_hour_korean_context`
- `event_keyword_gate`
- `emergency_context_tail_gate`
- `counter_policy_gate`
- `hyphen_routing_gate`
- `currency_safe_tail_gate`
- `unit_safe_boundary_gate`
- `range_full_consume_gate`
- `administrative_suffix_gate`
- `math_numeric_gate`

`date_hyphen_yyyy_mm_dd_gate`는 calendar-valid date render와 calendar-invalid hyphen digit fallback을 모두 분기한다.  
`date_slash_yyyy_mm_dd_gate`와 `date_dotted_yyyy_mm_dd_gate`는 invalid date에서 fraction/path/unit/decimal fallback은 허용하지 않고, 보호 owner와 URL/path 차단 조건을 통과한 경우 `CODE_SEPARATOR_BLOCK_SURFACE` fallback만 허용한다.

새 설계에서는 기존 gate registry 방향을 유지하되, 중복 평가를 claim registry로 줄인다.

### 10.3 Gate 실패 시 동작

Gate 실패는 모두 같은 의미가 아니다. 구현자는 실패를 `Absolute Preserve`, `Owner Fallback Candidate`, `Terminal Fallback Preserve`로 구분해야 한다.

| 실패 유형 | 동작 |
|---|---|
| code-like / URL / email / path / JSON / shell context | Absolute Preserve, owner 재진입 금지 |
| square bracket internal boundary | Absolute Preserve, owner 재진입 금지 |
| unsafe alphabetic / identifier tail | Absolute Preserve 또는 Terminal Fallback Preserve |
| ambiguous same-priority owner collision | Terminal Fallback Preserve |
| owner mismatch before claim | fallback_to_next_candidate |
| event keyword/gate 실패 dotted numeric | dotted decimal owner fallback |
| event keyword/gate 실패 middle-dot numeric | middle-dot numeric block fallback |
| emergency context 없음 | general number fallback 가능 |
| time context 없음 | preserve 또는 time fallback 정책에 따름 |
| calendar-invalid full date-like `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY.MM.DD` | code separator guard 통과 시 `CODE_SEPARATOR_BLOCK_SURFACE` fallback, 실패 시 Terminal Fallback Preserve |
| date URL/path/email/code context fail | Absolute Preserve |
| date alphabetic tail fail | Terminal Fallback Preserve |
| date square bracket protected fail | Absolute Preserve |
| invalid range/value after owner claim | Terminal Fallback Preserve |
| parser full consume 실패 | Terminal Fallback Preserve |
| validation 실패 | 운영 기본값은 전체 Terminal Fallback Preserve |

예:

```text
13:05 -> time gate fail -> Terminal Fallback Preserve
112는 -> emergency gate fail -> number fallback -> 백십이는
12.3-수치 -> event gate fail -> decimal fallback -> 십이쩜삼-수치
13.3 비상계엄 -> event gate fail -> decimal fallback -> 십삼쩜삼 비상계엄
12·3수치 -> event gate fail -> middle-dot fallback -> 십이 삼수치
```

### 10.4 Gate 평가 pseudo-code

```python
def evaluate_gates(candidates, tokens, registry):
    decisions = []
    for candidate in candidates:
        gate_name = gate_for_owner(candidate.owner)
        if gate_name is None:
            decisions.append(GateDecision(True, "none", candidate.owner, candidate.core_span, "no_gate", "fallback_to_owner"))
            continue

        context = build_parse_context(tokens, candidate.full_span)
        decision = GATE_REGISTRY.evaluate(gate_name, candidate, context)
        decisions.append(decision)

        if not decision.passed:
            apply_gate_failure(decision, registry)

    return decisions
```

### 10.5 ParseContext

Parser와 Gate는 한글 context를 읽을 수 있지만, rewrite할 수 없다. 이를 명시하기 위해 context object는 읽기 전용이어야 한다.

```python
@dataclass(frozen=True)
class ParseContext:
    raw_text: str
    tokens: tuple[SpanToken, ...]
    left_tokens: tuple[SpanToken, ...]
    right_tokens: tuple[SpanToken, ...]
    candidate_span: SourceSpan
    claim_registry: SurfaceClaimRegistry
```

금지:

```python
context.tokens[i].raw = "수정된한글"
```

허용:

```python
right = context.right_tokens[0].raw
if right in TIME_POSTPOSITIONS:
    pass_gate()
```

## 11. Phase 5 — Structured Parser / Typed Surface Generation

Gate를 통과한 surface만 parser가 처리한다.

### 11.1 Parser 공통 계약

모든 parser는 다음을 지켜야 한다.

1. owner가 있어야 한다.
2. gate가 필요한 경우 gate를 통과해야 한다.
3. full consume해야 한다.
4. raw residue를 남기면 안 된다.
5. 한글 literal을 rewrite하면 안 된다.
6. 실패하면 preserve 또는 명시 fallback만 허용한다.
7. parser 결과는 `Surface`로 생성한다.
8. parser 결과는 provenance를 유지할 수 있어야 한다.

### 11.2 ParserResult

```python
@dataclass
class ParserResult:
    success: bool
    surface: Surface | None = None
    render_pieces: list[RenderPiece] | None = None
    failure_reason: str | None = None
    fallback_action: str | None = None
```

### 11.3 Full Consume 예시

허용:

```text
3~8cm
-> entire raw "3~8cm" consumed
-> reading "삼에서 팔 센티미터"
```

금지:

```text
3~8cm
-> "3~8"만 변환
-> "cm" residue 남김
-> 삼에서 팔cm
```

공통 규칙:

- 의미가 불명확하면 변환하지 않는다.
- full consume가 아니면 변환하지 않는다.
- 일부만 바꾸고 raw residue를 남기는 partial consume은 금지한다.
- unsupported slash, tilde, dotted chain, invalid alphabetic contamination은 preserve한다.

### 11.4 Parser 실행 pseudo-code

```python
def parse_gated_surfaces(gate_results, registry):
    results = []
    for decision in gate_results:
        if not decision.passed:
            results.append(handle_failed_gate(decision))
            continue

        parser = PARSER_BY_OWNER[decision.owner]
        result = parser.parse(decision)

        if result.success and result.surface:
            assert result.surface.span == decision.span
            assert result.surface.owner == decision.owner
            assert result.surface.protected is True
            results.append(result)
        else:
            results.append(handle_parser_failure(result, decision, registry))
    return results
```

### 11.5 Parser family별 full-consume rule

| parser family | full consume 요구 | 실패 시 동작 |
|---|---|---|
| mixed token | 전체 표면 consume 필요 | preserve |
| currency | symbol/code + number + safe tail 전체 consume 필요 | preserve |
| unit | number + unit + safe boundary 전체 consume 필요 | preserve |
| emergency | context + allowed tail 모두 충족 필요 | general number 또는 preserve |
| pH | prefix + number 전체 match 필요 | preserve |
| event numeric surface | immediate event keyword adjacency 필요 | gate pass 시 event, gate fail 시 dotted/middle-dot numeric fallback |
| code separator block | 동일 구분자, 블럭 수, 공백, owner 우선순위, full consume 조건 충족 필요 | preserve 또는 다음 owner stage |
| tilde range | 양쪽 numeric-like와 optional suffix 전체 consume 필요 | preserve |
| administrative suffix | 주소 context + suffix whitelist + boundary 필요 | preserve 또는 existing owner |
| math numeric | notation 전체 consume 필요 | preserve |

## 12. Phase 6 — Restricted Helper / Boundary Smoothing

이 단계는 가장 조심해야 한다. 기존 helper를 유지하더라도 한글 literal rewrite가 가능한 경로를 제거해야 한다.

### 12.1 Helper 분류

| helper 종류 | 허용 | 금지 |
|---|---|---|
| structured helper | owner 있는 surface 안정화 | 한글 rewrite |
| typed promotion helper | surface 등록 | plain rewrite |
| boundary smoothing | surface 경계 처리 | 조사 교정 |
| generic helper | 비한글 plain cleanup | 한글 포함 segment 수정 |

### 12.2 Boundary-only Smoothing

허용 대상:

- system-generated surface 내부
- surface reading과 원문 particle의 경계 정보 읽기
- 숫자 reading 내부의 발음 안정화
- owner가 명확한 typed surface 내부 normalization

금지 대상:

- `ORIGINAL_KOREAN` RenderPiece 수정
- `ORIGINAL_SPACE` 이동/삭제
- `ORIGINAL_PUNCT` 이동/삭제
- particle correction
- broad Hangul particle correction

예:

```text
허용: 13:05에 -> 십삼시 오분에
```

여기서 `에`는 원문 그대로다.

금지:

```text
AI이 -> 에이아이가
제4과 -> 제사와
종로3가 -> 종로삼이
```

### 12.3 Generic Helper skip_hangul

generic helper는 한글이 포함된 plain segment를 건드리지 않는다.

```python
if segment.contains_korean_literal:
    skip_generic_helper()
```

다만 structured parser는 한글 context를 읽을 수 있다.

```text
generic helper:
- 한글 포함 plain string rewrite 금지

structured parser:
- 한글 context read 허용
- 한글 rewrite 금지
```

### 12.4 Restricted Helper 순서

기존 helper 순서를 유지하되, object/span 기반에서는 적용 대상을 명확히 제한한다.

1. `_adjust_number_noun_particles`
2. `_fix_numeric_postpositions` with `skip_hangul=True`
3. `_fix_josa_number_spacing` with `skip_hangul=True`
4. `_fix_decimal_reading_spacing` with `skip_hangul=True`
5. `_fix_numeric_label_suffix_spacing` with `skip_hangul=True`
6. `_fix_residual_integer_degrees` with `skip_hangul=True`
7. `_fix_standalone_jo` with `skip_hangul=True`
8. `_fix_standalone_eok` with `skip_hangul=True`
9. `_fix_residual_english_units`
10. `_fix_compact_date_counter_spacing` with `skip_hangul=True`
11. `_apply_phonetic_smoothing`
12. `_protect_post_rule_surface_matches`

새 구조에서는 위 helper 중 조사 교정으로 해석될 수 있는 helper는 boundary-only 또는 generated-only로 축소해야 한다. `ORIGINAL_KOREAN` provenance를 수정하는 helper는 금지한다.

### 12.5 helper 적용 pseudo-code

```python
def apply_restricted_helpers(parse_results):
    pieces_or_surfaces = parse_results
    for helper in RESTRICTED_HELPERS:
        pieces_or_surfaces = helper.apply(
            pieces_or_surfaces,
            policy=HelperPolicy(
                prohibit_original_korean_rewrite=True,
                prohibit_original_space_rewrite=True,
                prohibit_original_punct_rewrite=True,
                generated_only=True,
            ),
        )
    return pieces_or_surfaces
```

## 13. Phase 7 — Typed Surface Render

Render는 surface를 최종 문자열 조각으로 바꾸는 단계다.

### 13.1 Render 원칙

- surface reading은 `GENERATED_READING` provenance
- trailing particle은 `ORIGINAL_KOREAN` provenance
- 원본 공백은 `ORIGINAL_SPACE` provenance
- 원본 punctuation은 `ORIGINAL_PUNCT` provenance
- 원본 boundary literal은 `ORIGINAL_BOUNDARY` provenance
- surface 내부에 prosody 삽입 금지
- render 단계에서 한글 literal rewrite 금지

### 13.2 Particle Attach

attach는 원문 조사 재결합만 의미한다.

```python
def render_surface(surface: Surface) -> list[RenderPiece]:
    pieces = [
        RenderPiece(
            text=surface.reading,
            provenance="GENERATED_READING",
            source_span=surface.span,
            owner=surface.owner,
        )
    ]

    if surface.trailing_particle:
        pieces.append(
            RenderPiece(
                text=surface.trailing_particle,
                provenance="ORIGINAL_KOREAN",
                source_span=surface.trailing_particle_span,
                owner=surface.owner,
            )
        )

    return pieces
```

예:

```text
FTA는
-> GENERATED_READING("에프티에이")
-> ORIGINAL_KOREAN("는")
-> 에프티에이는

FTA은
-> GENERATED_READING("에프티에이")
-> ORIGINAL_KOREAN("은")
-> base render: 에프티에이은
-> Safe particle exception final render: 에프티에이는
```

### 13.3 RenderPiece Assembly

최종 문자열은 `RenderPiece.text`를 순서대로 결합한 결과다. 단, 결합 전 shadow validation을 위한 provenance와 source_span이 유지되어야 한다.

```python
rendered_text = "".join(piece.text for piece in pieces)
```

결합 전후에 다음을 금지한다.

- generated reading과 original particle을 보고 particle을 교정하기
- original space를 collapse하기
- original punctuation을 이동하기
- protected surface 내부에 쉼표 삽입하기

### 13.4 원문 token render

surface가 아닌 원문 token은 provenance를 보존하여 render한다.

```python
def render_token(token: SpanToken) -> RenderPiece:
    if token.kind == "KOREAN_LITERAL":
        return RenderPiece(token.raw, "ORIGINAL_KOREAN", token.span)
    if token.kind == "SPACE_LOCK":
        return RenderPiece(token.raw, "ORIGINAL_SPACE", token.span)
    if token.kind == "PUNCT_LOCK":
        return RenderPiece(token.raw, "ORIGINAL_PUNCT", token.span)
    if token.kind == "BOUNDARY_LITERAL":
        return RenderPiece(token.raw, "ORIGINAL_BOUNDARY", token.span)
    return RenderPiece(token.raw, "ORIGINAL_BOUNDARY", token.span)
```


### 13.4 Safe Post-Surface Particle Exception

조사 보존은 기본 원칙이다. 그러나 숫자/단위/영문/기호 등 교정 처리대상 surface 뒤에 바로 붙은 일부 이형태 조사는, 오독 방지를 위해 제한적으로 교정할 수 있다. 이 규칙은 일반 한글 조사 교정이 아니라 `generated surface + trailing Hangul particle` 형태에만 적용되는 post-surface 예외다.

#### 13.4.1 실행 위치

Safe Post-Surface Particle Exception은 Phase 7 Typed Surface Render 내부의 마지막 sub-step으로 실행한다. 정확한 순서는 다음과 같다.

1. surface reading 생성
2. original trailing_particle attach 후보 생성
3. Safe 조사 예외 판정
4. 예외 적용 시 original particle piece를 출력하지 않고 해당 span을 `PARTICLE_EXCEPTION_CONSUMED`로 trace에 기록
5. 교정된 조사는 `GENERATED_PARTICLE` provenance로 출력
6. 이후 Shadow Validation 실행

즉, Safe 조사 예외는 Shadow Validation 이전에 끝나야 한다.

#### 13.4.2 처리 대상

처리 대상은 다음 형태다.

```text
(숫자/단위/영문/기호 등 owner가 확정된 generated surface) + trailing_particle
```

적용 조건:

1. 앞 조각이 `GENERATED_READING` 또는 generated surface의 마지막 render piece일 것
2. 뒤 조사가 원문 trailing_particle로 분석되었을 것
3. 조사 span이 `attach_span` 또는 `trailing_particle_span`으로 분리되어 있을 것
4. 앞 조각이 `ORIGINAL_KOREAN`이면 적용하지 않을 것
5. 마지막 non-space 한글 음절의 종성 판정이 가능할 것

예:

```text
3를
10은
AI이
FTA는
€50을
3kg으로
```

단, 한글 lexical token 뒤의 조사는 이 규칙의 대상이 아니다. 일반 한글 문장의 조사 교정은 하지 않는다.

```text
유로을 -> 유로을
# 유로가 사용자가 직접 입력한 ORIGINAL_KOREAN이면 교정 금지

€50을 -> 오십 유로를
# 유로가 currency surface에서 생성된 GENERATED_READING이면 Safe 을/를 교정 허용
```

#### 13.4.3 조사 분류 및 처리 가이드라인

| 분류 | 대상 항목 | 처리 방식 |
|---|---|---|
| A1. 교정 허용군 | `은/는`, `을/를`, `으로` | surface reading의 마지막 음절 종성 유무에 따라 조사 형태를 교정 |
| A2. 보존 허용군 | `이` | generated surface 뒤에서 원문 그대로 attach. `이 -> 가` 변환 금지 |
| B. 교정 금지군 Risky | `가`, `로`, `과`, `와`, `도` | 조사 형태 수정 금지, 원문 그대로 출력 |
| C. 일반 단위/명사군 | `회`, `차`, `과`, `세`, `명`, `건`, `호`, `동`, `가`, `로`, `길`, `번지` 등 | 조사 교정 대상에서 제외, 원문 그대로 출력 |

`가`, `로`, `과`, `와`, `도`는 지명, 도로명, 단위, 서수, 고유명사와 충돌 위험이 크므로 교정하지 않는다.

#### 13.4.4 Safe 조사 교정표

| 입력 조사 | surface reading 종성 있음 | surface reading 종성 없음 | 비고 |
|---|---|---|---|
| `은` | `은` | `는` | A1 |
| `는` | `은` | `는` | A1 |
| `을` | `을` | `를` | A1 |
| `를` | `을` | `를` | A1 |
| `으로` | `으로` | `로` | A1. 단, 마지막 음절 종성이 `ㄹ`이면 `로` |
| `이` | `이` | `이` | A2. `가`로 바꾸지 않음 |

주의:

- 입력이 `로`이면 `으로`로 교정하지 않는다. `로`는 Risky 금지군이다.
- 입력이 `가`이면 `이`로 교정하지 않는다. `가`는 Risky 금지군이다.
- 입력이 `과` 또는 `와`이면 서로 교정하지 않는다.
- 입력이 `도`이면 어떤 경우에도 수정하지 않는다.
- `이`는 Safe 계열에 포함되지만 실제 교정 대상이 아니다. `AI이 -> 에이아이이`가 canonical output이다.

#### 13.4.5 받침 판정 기준

Safe 조사 예외의 종성 판정은 generated reading 문자열의 마지막 non-space 한글 음절을 기준으로 한다. 마지막 non-space 문자가 완성형 한글 음절이 아니면 Safe 조사 예외를 적용하지 않고 원문 조사를 보존한다.

```python
def final_hangul_syllable(text: str) -> str | None:
    for ch in reversed(text.strip()):
        if "\uAC00" <= ch <= "\uD7A3":
            return ch
    return None

def jongseong_index(ch: str) -> int:
    return (ord(ch) - 0xAC00) % 28

def has_jongseong(ch: str) -> bool:
    return jongseong_index(ch) != 0
```

`으로` 처리에서는 마지막 음절이 ㄹ 받침이면 `로`를 선택한다.

#### 13.4.6 Algorithm

1. owner가 확정된 generated surface와 바로 뒤 한글 tail을 탐지한다.
2. tail이 A1/A2 조사군에 속하는지 확인한다.
3. tail이 A1/A2가 아니면 원문 tail을 그대로 결합한다.
4. tail이 A2 `이`이면 원문 그대로 attach하고 `가`로 바꾸지 않는다.
5. tail이 A1이면 generated reading의 마지막 non-space 한글 음절을 찾는다.
6. 마지막 한글 음절이 없으면 원문 tail을 그대로 결합한다.
7. A1 교정표에 따라 교정된 조사를 선택한다.
8. 교정된 조사는 `GENERATED_PARTICLE` provenance로 출력한다.
9. 원문 조사와 교정 조사 사이의 대응 관계를 trace에 남긴다.
10. shadow validation에서는 이 규칙으로 소비된 원문 조사를 `PARTICLE_EXCEPTION_CONSUMED`로 표시하여 일반 particle preservation failure로 보지 않는다.

#### 13.4.7 Examples

교정 허용:

```text
사과 3를 먹었다 -> 사과 삼을 먹었다
10는 많다 -> 십은 많다
AI이 적용됐다 -> 에이아이이 적용됐다
FTA은 적용됐다 -> 에프티에이는 적용됐다
€50을 냈다 -> 오십 유로를 냈다
3kg으로 이동 -> 삼 킬로그램으로 이동
8km으로 이동 -> 팔 킬로미터로 이동
```

교정 금지:

```text
유로을 입력했다 -> 유로을 입력했다
종로3가역으로 오세요 -> 종로삼가역으로 오세요
테헤란로 8길 -> 테헤란로 팔길
제4과 본문 읽기 -> 제 사과 본문 읽기
3가 맞다 -> 삼가 맞다
12로 나누다 -> 십이로 나누다
```

위 예시에서 `가`, `로`, `과`는 교정하지 않는다. 의미 훼손 위험이 조사 어색함보다 크기 때문이다.

#### 13.4.8 Validation Interaction

Safe 조사 예외가 적용된 조사는 원본 보존 실패가 아니다. 단, 이 예외는 다음 조건을 모두 만족해야 한다.

- 앞 구간이 generated surface일 것
- tail이 A1 교정 허용군 또는 A2 보존 허용군일 것
- owner trace에 particle exception 또는 no-op attach가 기록될 것
- Risky 조사군이 아닐 것
- 일반 한글 lexical token 뒤 조사가 아닐 것

조건을 만족하지 않는데 조사가 바뀌면 validation fail이다.

#### 13.4.9 Particle Exception Clarification

Safe Post-Surface Particle Exception은 partial rewrite가 아니다. generated surface core는 owner가 full consume한다. trailing particle은 raw residue가 아니라 `trailing_particle_span`으로 분리된 attach metadata다. 예외 적용 시 원문 조사 span은 `PARTICLE_EXCEPTION_CONSUMED`로 기록하고, 출력 조사는 `GENERATED_PARTICLE` provenance로 생성한다.

`ORIGINAL_KOREAN` lexical token 뒤 조사는 이 예외의 대상이 아니다. owner가 없는 plain string 또는 한글 literal 내부에서 조사를 바꾸는 것은 partial rewrite이며 금지한다.

```text
€50을 -> 오십 유로를
유로을 -> 유로을
AI이 -> 에이아이이
AI이 -> 에이아이가  # 금지
```

## 14. Phase 8## 14. Phase 8 — Shadow Validation

Shadow Validation은 이 설계의 핵심 안전장치다.

### 14.1 Validation 대상

검사 대상:

- 원본 한글 literal
- 원본 한글-한글 공백
- 원본 한글 뒤 punctuation
- 원본 조사
- protected surface non-reentry

검사 제외:

- 시스템이 생성한 숫자 reading
- acronym reading
- unit reading
- currency reading
- event reading
- generated boundary smoothing result

### 14.2 Validation 규칙

#### Rule 1. Original Korean Literal Preservation

모든 `ShadowUnit(kind="KOREAN_LITERAL")`은 출력의 `ORIGINAL_KOREAN` piece로 동일하게 존재해야 한다.

```text
raw == rendered_original_piece.text
span == rendered_original_piece.source_span
```

#### Rule 2. Korean Space Preservation

한글과 한글 사이 원본 공백은 동일해야 한다.

```text
전문  가 -> 전문  가
```

금지:

```text
전문  가 -> 전문 가
전문 가 -> 전문가
```

#### Rule 3. Korean Punctuation Preservation

한글 뒤 punctuation은 그대로 있어야 한다.

```text
안녕하세요, -> 안녕하세요,
안녕하세요 , 반갑습니다 -> 안녕하세요 , 반갑습니다
```

금지:

```text
안녕하세요 , 반갑습니다 -> 안녕하세요, 반갑습니다
```

#### Rule 4. Particle Preservation and Safe Exception

입력 조사는 기본적으로 그대로 유지되어야 한다. 단, Safe post-surface particle exception이 적용된 조사는 일반 particle preservation failure가 아니다. 이 경우 원문 조사 span은 `PARTICLE_EXCEPTION_CONSUMED`로 기록되고, 교정된 조사는 `GENERATED_PARTICLE` provenance로 출력되어야 한다.

```text
FTA은 -> 에프티에이는     # Safe: 은/는 교정
AI이 -> 에이아이이        # Safe 대상이지만 가로 교정하지 않음
제4과 -> 제 사과           # canonical numeric suffix output
종로3가 -> 종로삼가       # Risky: 가 보존
```

금지:

```text
AI이 -> 에이아이가
제4과 -> 제사와
종로3가 -> 종로삼이
```

#### Rule 5. Non-Reentry Validation

`ClaimedRange(reentry_allowed=False)`로 등록된 구간은 다른 owner에 의해 재처리되면 안 된다.

예:

```text
[12.3]
-> bracket protection claim
-> decimal/event parser가 처리하면 validation fail
```

### 14.3 Validation pseudo-code

```python
def validate_shadow(pieces: list[RenderPiece], shadow: list[ShadowUnit], registry: SurfaceClaimRegistry) -> ValidationResult:
    by_span = {(p.source_span.start, p.source_span.end, p.provenance): p for p in pieces if p.source_span}
    logs = []

    for unit in shadow:
        provenance = expected_provenance(unit.kind)
        key = (unit.span.start, unit.span.end, provenance)
        piece = by_span.get(key)
        if piece is None:
            if registry.is_particle_exception_consumed(unit.span):
                logs.append(ValidationLog(unit.kind, True, unit.raw, "PARTICLE_EXCEPTION_CONSUMED", unit.span))
                continue
            logs.append(ValidationLog(unit.kind, False, unit.raw, None, unit.span))
            continue
        if piece.text != unit.raw:
            logs.append(ValidationLog(unit.kind, False, unit.raw, piece.text, unit.span))

    logs.extend(validate_non_reentry(pieces, registry))
    passed = all(log.passed for log in logs)
    return ValidationResult(passed=passed, logs=logs)
```

### 14.4 Validation 실패 시 동작

운영 정책은 두 가지 중 하나로 선택한다.

권장 기본값:

```text
Validation fail -> 해당 입력 전체 preserve
```

개발/debug 모드:

```text
Validation fail -> exception + owner trace 출력
```

운영 환경에서 일부만 preserve하는 것은 위험하다. validation 실패는 구조적 불변성 위반이므로, 부분 복구가 더 큰 오작동을 만들 수 있다.

## 15. Phase 9 — Prosody / Paragraph Split

Prosody는 normalization 이후에만 실행한다.

### 15.1 Prosody 원칙

- insert-only
- 기존 punctuation 제거 금지
- 기존 punctuation 이동 금지
- 기존 공백 이동 금지
- surface 내부 쉼표 삽입 금지
- particle 경계를 쉼표 후보로 재사용 금지
- protected surface 내부 삽입 금지
- token 내부 삽입 금지
- midpoint fallback 금지

### 15.2 Prosody 입력

Prosody는 raw string이 아니라 render piece stream을 받는 것이 이상적이다.

```python
def insert_commas(pieces: list[RenderPiece]) -> list[RenderPiece]:
    ...
```

Prosody는 다음 provenance를 건드릴 수 없다.

- `ORIGINAL_KOREAN`
- `ORIGINAL_SPACE`
- `ORIGINAL_PUNCT`
- `GENERATED_READING` inside protected surface

쉼표 삽입 가능 위치:

- whitespace boundary
- protected surface 바깥
- punctuation conflict 없는 곳
- threshold 통과한 곳

### 15.3 Prosody Threshold Table

| feature | threshold / rule | effect |
|---|---|---|
| short sentence guard | `len(eojeols) < 3` or `char_len < 12` | leading connector 외에는 기본 no-comma |
| existing comma | `existing_comma_count > 0` | hard block |
| existing strong punct | `;` or `:` count > 0 | hard block |
| risky list-like | `numeric_or_protected_count >= 3` and no strong connector | hard block |
| numeric density | `numeric_like_ratio >= 0.35` | score 감소, budget 축소 |
| protected coverage | `protected_coverage >= 0.5` | budget 축소 |
| candidate score cutoff | `score >= 0.6` | cutoff 미만 candidate 제거 |
| high-confidence budget | `char_len >= 28` and any candidate `>= 0.9` | 최대 2개 |
| protected edge touch | non-leading-connector candidate에서 감점 또는 차단 | boundary 억제 |
| punctuation conflict | boundary 사이 punctuation 존재 | candidate 차단 |
| no whitespace boundary | eojeol boundary에 whitespace 없음 | candidate 차단 |

strong connectors:

- `그리고`
- `하지만`
- `그러나`
- `그래서`
- `또한`
- `다만`
- `즉`
- `반면`
- `대신`
- `한편`
- `따라서`

### 15.4 Prosody insertion pseudo-code

```python
def insert_commas_insert_only(pieces: list[RenderPiece]) -> list[RenderPiece]:
    candidates = find_whitespace_boundaries(pieces)
    accepted = []
    for candidate in candidates:
        if touches_protected_surface(candidate, pieces):
            continue
        if crosses_original_punct(candidate, pieces):
            continue
        if no_whitespace_boundary(candidate, pieces):
            continue
        if score_candidate(candidate, pieces) < 0.6:
            continue
        accepted.append(candidate)

    return insert_comma_pieces(pieces, accepted)
```

새로 삽입되는 쉼표는 source_span이 없고 provenance는 generated punctuation으로 둘 수 있다. 다만 기존 schema에 provenance enum을 추가하지 않는다면 owner metadata에 `generated_prosody=True`를 둔다.

### 15.5 Paragraph Split

Paragraph split도 기존 사용자 개행 block을 먼저 존중한다.

원칙:

- 사용자 개행 보존
- 너무 짧은 문단 split 금지
- quote 내부 split 금지
- 지시어 시작 split 억제
- 비전환 나열 구조 split 억제
- long text에서만 conservative split

Paragraph Split Threshold Table:

| constant | value | role |
|---|---:|---|
| `MIN_PARAGRAPH_LEN` | `20` | 새 문단 최소 길이 |
| `SOFT_LIMIT` | `250` | soft split 기준 |
| `HARD_LIMIT` | `300` | hard split 기준 |
| `INTERNAL_PAUSE_COMMA_THRESHOLD` | `2` | 내부 pause 충분 조건 |
| `COMMA_COOP_THRESHOLD` | `80` | comma cooperation length |
| `COMMA_COOP_MIN_COUNT` | `1` | cooperative comma 최소 개수 |
| `PAUSE_HARD_SPLIT_BUFFER_LIMIT` | `240` | pause-rich hard split buffer |
| `PAUSE_CONDITIONAL_SENTENCE_THRESHOLD` | `4` | pause-rich sentence count 기준 |
| `CONSERVATIVE_SPLIT_LENGTH_THRESHOLD` | `200` | conditional split length |
| `CONSERVATIVE_SPLIT_SENTENCE_THRESHOLD` | `3` | conditional split sentence count |
| `SHORT_TAIL_THRESHOLD` | `2` | sentence 수가 너무 적으면 split 생략 |
| `SHORT_TEXT_PAUSE_BUDGET_LIMIT` | `1` | 짧은 텍스트 pause budget |
| `MEDIUM_TEXT_PAUSE_BUDGET_LIMIT` | `2` | 중간 텍스트 pause budget |
| `LONG_TEXT_PAUSE_BUDGET_LIMIT` | `3` | 긴 텍스트 pause budget |
| `MEDIUM_TEXT_LENGTH_THRESHOLD` | `80` | medium 판정 기준 |
| `LONG_TEXT_LENGTH_THRESHOLD` | `160` | long 판정 기준 |

## 16. Priority, Conflict Resolution, Fallback Rules

### 16.1 최상위 우선순위

1. Core Invariance Principle
2. Shadow lock / immutable span token
3. Surface claim / non-reentry registry
4. typed surface protection
5. context-readable structured parser
6. dictionary safe output
7. owner-first gate routing
8. structured parser full consume
9. restricted helper / boundary-only smoothing
10. typed surface render
11. shadow validation
12. prosody comma
13. paragraph split

### 16.2 규칙 충돌 해소 원칙

- parser owner가 더 좁고 명시적이면 먼저 적용한다.
- fixed dictionary surface는 broad fallback보다 우선한다.
- event gate는 generic decimal보다 우선한다.
- date/time owner는 general number보다 우선한다.
- unit/currency owner는 generic number owner보다 우선한다.
- range owner는 내부 number partial consume보다 우선한다.
- counter owner는 bare number owner보다 우선한다.
- final tilde range는 broad number fallback 이후 authority를 갖지만, claim은 미리 등록되어 partial consume을 막는다.
- 동일 priority 충돌은 preserve한다.

### 16.3 Fallback 위치와 제한

- safe acronym fallback은 dictionary 이후에만 허용한다.
- generic number fallback은 모든 특수 owner 실패 이후에만 허용한다.
- Absolute Preserve claim이 등록된 segment는 재진입 금지다.
- Owner Fallback Candidate는 preserve claim이 아니며 다음 후보 owner 평가를 허용한다.
- Terminal Fallback Preserve는 모든 후보 owner가 실패하거나 full consume/validation이 실패한 뒤 최종적으로만 적용한다.
- calendar-invalid `YYYY-MM-DD` hyphen date fallback은 일반 generic fallback이 아니다.
  - `date_time.date` owner가 exact `4-2-2` pattern을 먼저 claim한 뒤,
  - calendar validity 실패가 확인되고,
  - fallback guard를 모두 통과한 경우에만
  - `CODE_SEPARATOR_BLOCK_SURFACE` fallback을 허용한다.
- final tilde range fallback은 range claim이 없는 임의 문자열에 적용하면 안 된다.
- typed surface가 생성된 segment는 legacy helper 대상이 아니다.
- event owner 실패 dotted numeric은 decimal owner fallback으로 넘길 수 있다.
- event owner 실패 middle-dot numeric은 middle-dot numeric block fallback으로 넘길 수 있다.
- generic numeric+Korean suffix surface는 한글 suffix를 rewrite하지 않고 숫자 core만 변환하는 후보 owner로 평가할 수 있다.

### 16.4 대표 충돌 시나리오

| 충돌 | 먼저 적용돼야 할 규칙 | preserve 조건 |
|---|---|---|
| 사건형 숫자 vs 일반 소수 | event keyword gate > dotted decimal fallback | event keyword gate 통과 시 event, 실패 시 dotted decimal fallback |
| 시간 vs 일반 colon 패턴 | time gate 통과 시에만 time | score/ratio/general colon이면 preserve |
| 하이픈 날짜 vs 하이픈 digit block | exact `4-2-2`는 `date_time.date`가 우선 claim. calendar-invalid일 때만 조건부 `hyphen_digit_blocks` fallback | pure numeric 3-block 아님, `4-2-2` shape 불일치, URL/path/email 내부, alphabetic tail, square bracket 보호 구간 내부이면 preserve |
| 하이픈 범위 vs 전화번호 | hyphen routing owner 결정 후 exact phone only | two-block non-phone이면 preserve 가능 |
| range vs minus number | temperature/signed-degree owner > range | owner 실패 시 preserve |
| acronym vs lexical tail | acronym lexical suffix claim > generic acronym fallback | tail full consume 실패 시 preserve |
| 단위 vs 일반 숫자 | unit owner > number owner | invalid tail이면 preserve |
| 통화 vs 일반 숫자 | currency owner > number owner | invalid code/suffix면 preserve |
| 긴급번호 vs 일반 숫자 | emergency owner only with context+tail | 실패 시 general number 가능 |
| 행정 suffix vs 일반 숫자/조사 | administrative gate 통과 시만 행정 owner | 주소 context 없으면 preserve 또는 기존 owner |

## 17. Stage Ownership Matrix

| 입력 패턴 | owner stage | context read 필요 | typed surface 생성 시점 | fallback 허용 위치 | preserve 조건 | canonical output |
|---|---|---:|---|---|---|---|
| `2025-01-03` | `date_time.date` | 아니오 | parse phase | 없음 | year range fail, boundary fail, URL/path/email/code context면 preserve | `이천이십오년 일월 삼일` |
| `2025-13-03` | `date_time.date -> code_separator_block fallback` | 아니오 | date gate/parser fallback phase | calendar-invalid + code separator guard pass | code separator guard 실패, URL/path/email 내부, alphabetic tail, square bracket 내부이면 preserve | `이공이오 일삼 공삼` |
| `2025.13.03` | `date_time.date -> code_separator_block fallback` | 아니오 | date gate/parser fallback phase | calendar-invalid + code separator guard pass | URL/path/email, alphabetic tail, square bracket 내부이면 preserve | `이공이오쩜 일삼쩜 공삼` |
| `2025/13/03` | `date_time.date -> code_separator_block fallback` | 아니오 | date gate/parser fallback phase | calendar-invalid + code separator guard pass | URL/path-like, alphabetic tail, square bracket 내부이면 preserve | `이공이오 일삼 공삼` |
| `3~8cm` | `range claim -> range parser` | 예 | parse phase | owner 실패 시 preserve | 양쪽 numeric-like 아니면 preserve | `삼에서 팔 센티미터` |
| `1∼11월` | `range claim -> range parser` | 예 | parse phase | range owner 내부 | date shared-suffix range 조건 실패 시 Terminal Fallback Preserve | `일월에서 십일월` |
| `12.3 비상계엄` | `event claim -> event parser` | 예 | parse phase | 없음 | event keyword gate 실패 시 fallback | `십이삼 비상계엄` |
| `21명` | `counter_noun` | 예 | parse phase | number보다 먼저 counter 판단 | unsupported counter면 later number path | `스물한 명` |
| `FTA율` | `acronym_suffix` | 예 | claim/parse phase | generic acronym fallback 금지 | suffix full consume 실패 시 preserve | `에프티에이율` |
| `K-푸드` | `k_hangul_lexical` | 예 | claim/parse phase | dictionary/fixed lexical 이후 | full consume 실패 또는 unsafe tail이면 다음 owner/fallback | `케이푸드` |
| `13:05` | `date_time.time_colon` | 예 | parse phase | time gate 실패 시 preserve | context gate 실패 시 preserve | `13:05` |
| `13:05에` | `date_time.time_colon` | 예 | parse phase | 없음 | 값 범위 오류면 preserve | `십삼시 오분에` |
| `긴급번호 112는` | `emergency` | 예 | parse phase | emergency 실패 시 number | context/tail 둘 다 필요 | `긴급번호 일일이는` |
| `112는` 일반 문맥 | `number` | 예 | parse phase | 없음 | emergency context 없으면 number | `백십이는` |
| `112명` | `counter_noun` | 예 | parse phase | emergency gate fail 이후 explicit counter 적용 | disallowed suffix면 emergency digit reading 금지 | `백십이 명` |
| `123-456-7890` | `code_separator_block` | 아니오 | parse phase | 없음 | block routing 실패 시 preserve | `일이삼 사오육 칠팔구공` |
| `1-1-9` | `code_separator_block` | 아니오 | parse phase | 없음 | emergency owner 아님. code separator block route | `일 일 구` |
| `pH 7.4` | `special.ph` | 아니오 | parse phase | 없음 | trailing contamination이면 preserve | `피에이치 칠쩜사` |
| `90km/h` | `compound_unit` | 아니오 | parse phase | unit family 내부 | invalid slash tail이면 preserve | `시속 구십 킬로미터` |
| `15.2km/L` | `compound_unit` | 아니오 | parse phase | compound unit 내부 | invalid slash tail이면 preserve | `리터당 십오쩜이 킬로미터` |
| `45㎡` | `special_unit` | 아니오 | parse phase | special unit 내부 | unsafe tail이면 preserve | `사십오 제곱미터` |
| `-2.5℃` | `temperature/signed_degree` | 아니오 | parse phase | temperature parse 내부 | invalid decimal length면 preserve | `영하 이쩜오도` |
| `종로3가` | `administrative_suffix` | 예 | parse phase | gate 실패 시 preserve 또는 number | 주소 context 없으면 broad parse 금지 | `종로삼가` |

## 18. 주요 입력별 처리 예시

### 18.1 `회의는 13:05에 시작한다`

처리:

1. `회의는`, `에`, `시작한다`는 `KOREAN_LITERAL`
2. `13:05`는 time candidate
3. 뒤 tail `에` context read
4. time gate pass
5. reading = `십삼시 오분`
6. `에`는 original particle로 attach

출력:

```text
회의는 십삼시 오분에 시작한다
```

### 18.2 `13:05`

처리:

1. `13:05` = time candidate
2. 단독 `HH:MM`
3. time gate fail
4. Terminal Fallback Preserve

출력:

```text
13:05
```

### 18.3 `12.12 사태`

처리:

1. `12.12` = dotted event candidate
2. immediate event keyword `사태` 확인
3. event gate pass
4. reading = `십이십이`
5. `사태`는 original Korean literal

출력:

```text
십이십이 사태
```

### 18.4 `12.3 비상계엄`

처리:

1. `12.3` = event candidate
2. keyword `비상계엄` 확인
4. event gate pass
5. `12.3` reading = `십이삼`

출력:

```text
십이삼 비상계엄
```

### 18.5 `긴급번호 112는`

처리:

1. `112` = emergency candidate
2. context `긴급번호` 확인
3. tail `는` allowed
4. emergency gate pass
5. `112` reading = `일일이`
6. tail `는` original attach

출력:

```text
긴급번호 일일이는
```

### 18.6 `112명`

처리:

1. `112` = emergency candidate 가능
2. tail `명` disallowed
3. emergency gate fail
4. counter policy path
5. `명`은 explicit counter literal

출력:

```text
백십이 명
```

### 18.7 `21명`

처리:

1. `21 + 명` = counter candidate
2. counter table에서 `명` = hybrid threshold 39
3. `21 <= 39`
4. native reading
5. `명` original literal

출력:

```text
스물한 명
```

### 18.8 `31명`

처리:

1. `명` = hybrid threshold 39
2. `31 <= 39`
3. native reading

출력:

```text
서른한 명
```

### 18.9 `FTA은`

처리:

1. `FTA` = acronym surface
2. `은` = Safe post-surface particle candidate
3. acronym reading = `에프티에이`
4. base render에서는 `은`이 original particle로 attach될 수 있다.
5. Safe particle exception 단계에서 `에프티에이`는 마지막 음절 종성이 없으므로 `은`을 `는`으로 교정한다.
6. 교정된 `는`은 `GENERATED_PARTICLE` provenance로 출력하고 trace에 원문 span을 남긴다.

출력:

```text
에프티에이는
```

금지:

```text
에프티에이은  # Safe exception이 적용되지 않은 경우
```

### 18.10 `K-푸드`

처리:

1. single-letter hyphen lexical compound claim
2. `K` reading = `케이`
3. `푸드` original Korean literal
4. hyphen 보존 정책에 따라 lexical surface render

출력:

```text
케이푸드
```

### 18.11 `3~8cm`

처리:

1. range with unit claim
2. full consume: `3~8cm` 전체
3. left = `삼`
4. right = `팔`
5. unit = `센티미터`

출력:

```text
삼에서 팔 센티미터
```

금지:

```text
삼~8cm
삼에서 팔cm
```

### 18.12 `종로3가`

처리:

1. `종로` = `KOREAN_LITERAL`, context readable
2. `3가` = administrative suffix candidate
3. 좌측 지명 후보 `종로`
4. suffix `가` whitelist
5. administrative gate pass
6. `3` reading = `삼`
7. `가` original literal

출력:

```text
종로삼가
```

단, `3가 맞다`는 같은 규칙으로 처리하면 안 된다. 좌측 지명/주소 context가 없으면 preserve 또는 general number 정책을 따른다.

## 19. Canonical Outputs

| 입력 | canonical output | 핵심 규칙 |
|---|---|---|
| `회의(비공개) [긴급] 일정은 2025.01.03 13:05에 시작하고 비용은 €1,234.56이다` | `회의 긴급 일정은 이천이십오년 일월 삼일 십삼시 오분에 시작하고 비용은 천이백삼십사쩜오육 유로이다` | bracket + date/time + currency |
| `화재가 나면 119에 신고하고 연비는 15.2km/L로 확인한다` | `화재가 나면 일일구에 신고하고 연비는 리터당 십오쩜이 킬로미터로 확인한다` | emergency + compound unit |
| `긴급번호 112는 경찰 신고 번호이고 112명은 회의실에 있다` | `긴급번호 일일이는 경찰 신고 번호이고 백십이 명은 회의실에 있다` | emergency vs counter split |
| `그리고 12.12 사태 자료와 €1,234.56 보고서를 검토한다` | `그리고, 십이십이 사태 자료와 천이백삼십사쩜오육 유로 보고서를 검토한다` | event + currency + prosody |
| `21명` | `스물한 명` | counter policy |
| `31명` | `서른한 명` | hybrid threshold |
| `3~8cm` | `삼에서 팔 센티미터` | range owner |
| `1∼11월` | `일월에서 십일월` | date shared-suffix range |
| `FTA율` | `에프티에이율` | acronym lexical suffix |
| `K-푸드` | `케이푸드` | K-Hangul lexical prefix |
| `90km/h` | `시속 구십 킬로미터` | compound unit |
| `45㎡` | `사십오 제곱미터` | special unit |
| `-2.5℃` | `영하 이쩜오도` | temperature |
| `pH 7.4` | `피에이치 칠쩜사` | special parser |
| `123-456-7890` | `일이삼 사오육 칠팔구공` | hyphen digit blocks |
| `1-1-9` | `일 일 구` | hyphen digit blocks |
| `종로3가` | `종로삼가` | administrative suffix gate |


## 20. Ambiguous / Terminal Fallback Preserve Cases

다음 경우들은 안전을 위해 `Absolute Preserve` 또는 `Terminal Fallback Preserve`로 처리한다. 단, 본 문서에서 `Owner Fallback Candidate`로 명시한 항목은 즉시 preserve하지 않고 다음 후보 owner로 넘긴다.

1. **Protected Brackets**: `[...]` 내부의 모든 텍스트.
2. **Parenthesis Final Elision**: `(...)` 삭제 대상이나, 내부 내용이 보존되어야 하는 특수 context.
3. **URL/Path/Email/Code**: `/`, `.`, `@`, `_`, `-` 등이 복합적으로 쓰인 식별자 형태.
   - 예: `docs/2025/01/03`, `user@example.com`, `v1.2.3-beta`
4. **Unsupported Owner Fallback Ban**: 특정 owner가 명시적으로 fallback을 금지한 경우. 단, Owner Fallback Candidate로 명시된 경우는 다음 후보 owner 평가를 허용한다.
   - 단, hyphen exact `YYYY-MM-DD`의 calendar-invalid date-like pattern은 예외다.
   - 이 예외는 `date_time.date` owner가 우선 claim한 뒤 fallback guard를 모두 통과한 경우에만 `CODE_SEPARATOR_BLOCK_SURFACE` fallback을 허용한다.
5. **Owner Collision**: 우선순위가 같거나 상충하여 해소가 불가능한 overlap.
6. **Full Consume Failure**: parser가 점유한 span을 모두 소비하지 못한 경우. 이 경우 partial rewrite가 아니라 Terminal Fallback Preserve로 처리한다.
7. **Mixed Alnum/Code-like**: 숫자와 영문이 불규칙하게 섞인 토큰. 단, dictionary/fixed lexical claim 이후 허용된 hyphen/middle-dot mixed alnum code reading은 예외다.
   - 예: `A12.3B`, `12·3X` (Lexical tail이 아닌 경우)
8. **Invalid Date**: 달력 범위를 벗어난 full date-like token.
   - `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY.MM.DD`는 모두 `date_time.date` owner가 먼저 claim한다.
   - calendar-invalid full date-like token은 아래 조건을 모두 만족하면 `CODE_SEPARATOR_BLOCK_SURFACE` fallback을 허용한다.
     1. pure numeric 3-block이다.
     2. 각 block은 `4-2-2` 형태를 유지한다.
     3. 모든 구분자가 동일하다.
     4. 구분자 좌우에 공백이 없다.
     5. URL/path/email 내부가 아니다.
     6. alphabetic tail이 붙지 않았다.
     7. square bracket 보호 구간 내부가 아니다.
     8. version/log/model/code context가 아니다.
   - 위 조건 중 하나라도 실패하면 preserve한다.
   - calendar-invalid fallback은 date reading, decimal fallback, fraction fallback, general number fallback이 아니라 `CODE_SEPARATOR_BLOCK_SURFACE` fallback이다.


## 21. Forbidden Output Signatures

다음과 같은 출력 형태는 정책 위반으로 간주한다.

1. **Partial Residue**: 숫자 core, 기호, 단위, suffix 일부만 변환하고 나머지를 raw residue로 남기는 출력은 금지한다.

```text
12.3 -> 십이.3        # 금지
12.3 -> 12쩜삼        # 금지
3~8cm -> 삼에서 팔cm  # 금지
50kg -> 오십kg        # 금지
```

2. **Event Digit-sequence Split**: event/date 조건을 통과한 dotted 또는 middle-dot event surface를 block 사이 공백이 있는 형태로 출력하는 것은 금지한다. 사건형 날짜는 separator를 읽지 않고 digit-sequence event reading으로 붙여 읽는다.

```text
12.3 비상계엄 -> 십이 삼 비상계엄        # 금지
12·3 비상계엄 -> 십이 삼 비상계엄        # 금지
12.3-비상계엄 -> 십이 삼-비상계엄        # 금지
12·3-비상계엄 -> 십이 삼-비상계엄        # 금지
4.19 혁명 -> 사 일구 혁명                # 금지
4·19 혁명 -> 사 일구 혁명                # 금지
5.18 민주화 운동 -> 오 일팔 민주화 운동   # 금지
6.27 부동산대책 -> 육 이칠 부동산대책     # 금지
```

canonical output:

```text
12.3 비상계엄 -> 십이삼 비상계엄
12·3 비상계엄 -> 십이삼 비상계엄
12.3-비상계엄 -> 십이삼-비상계엄
12·3-비상계엄 -> 십이삼-비상계엄
4.19 혁명 -> 사일구 혁명
4·19 혁명 -> 사일구 혁명
5.18 민주화 운동 -> 오일팔 민주화 운동
6.27 부동산대책 -> 육이칠 부동산대책
12.12 사태 -> 십이십이 사태
12·12 사태 -> 십이십이 사태
```

3. **Event Decimal Misread**: event/date 조건을 통과한 dotted event surface에서 `.`을 decimal point로 읽는 출력은 금지한다.

```text
12.3 비상계엄 -> 십이쩜삼 비상계엄       # 금지
12.3-비상계엄 -> 십이쩜삼-비상계엄       # 금지
4.19 혁명 -> 사쩜일구 혁명               # 금지
5.18 민주화 운동 -> 오쩜일팔 민주화 운동 # 금지
12.12 사태 -> 십이쩜일이 사태            # 금지
```

canonical output:

```text
12.3 비상계엄 -> 십이삼 비상계엄
12.3-비상계엄 -> 십이삼-비상계엄
4.19 혁명 -> 사일구 혁명
5.18 민주화 운동 -> 오일팔 민주화 운동
12.12 사태 -> 십이십이 사태
```

4. **Event Middle-dot Misread**: event/date 조건을 통과한 middle-dot event surface에서 `·`를 decimal point처럼 읽거나 원본 기호를 generated reading 내부에 남기는 출력은 금지한다.

```text
12·3 비상계엄 -> 십이쩜삼 비상계엄       # 금지
12·3 비상계엄 -> 십이·삼 비상계엄        # 금지
12·3-비상계엄 -> 십이쩜삼-비상계엄       # 금지
12·3-비상계엄 -> 십이·삼-비상계엄        # 금지
4·19 혁명 -> 사쩜일구 혁명               # 금지
4·19 혁명 -> 사·일구 혁명                # 금지
```

canonical output:

```text
12·3 비상계엄 -> 십이삼 비상계엄
12·3-비상계엄 -> 십이삼-비상계엄
4·19 혁명 -> 사일구 혁명
5·18 민주화 운동 -> 오일팔 민주화 운동
6·27 부동산대책 -> 육이칠 부동산대책
```

5. **Spaced Separator Full Consume**: 숫자와 separator 사이에 공백이 있는 입력을 event/date/decimal/middle-dot full consume으로 처리하거나, 공백과 기호를 무시하고 합치는 출력은 금지한다.

```text
12 .3 -> 십이쩜삼        # 금지
12. 3 -> 십이쩜삼        # 금지
12 · 3 -> 십이삼         # 금지
12 · 3 -> 십이 삼        # 금지
12 . 3 -> 십이삼         # 금지
12 . 3 -> 십이쩜삼       # 금지
```

canonical output:

```text
12 .3 -> 십이 .삼
12. 3 -> 십이. 삼
12 · 3 -> 십이 · 삼
12 · 3 수치 -> 십이 · 삼 수치
```

6. **Middle-dot Decimal Misread in Fallback**: event/date로 확정되지 않은 `숫자·숫자` fallback에서 `·`를 decimal point로 읽는 출력은 금지한다. fallback의 `·`는 소수점이 아니라 numeric block separator다.

```text
12·3 -> 십이쩜삼       # 금지
7·25 -> 칠쩜이오       # 금지
10·5 -> 십쩜오         # 금지
1·2·3 -> 일쩜이쩜삼    # 금지
```

canonical output:

```text
12·3 -> 십이 삼
7·25 -> 칠 이오
10·5 -> 십 오
1·2·3 -> 일 이 삼
123·456 -> 일이삼 사오육
```

7. **Middle-dot Fallback Cardinal Misread**: event/date로 확정되지 않은 middle-dot numeric block fallback에서 각 block을 일반 cardinal number로 읽는 출력은 금지한다. 각 block은 digit-sequence reading으로 읽는다.

```text
7·25 -> 칠 이십오             # 금지
10·5 -> 십 오                 # 허용
123·456 -> 백이십삼 사백오십육 # 금지
```

canonical output:

```text
7·25 -> 칠 이오
10·5 -> 십 오
123·456 -> 일이삼 사오육
```

8. **Middle-dot Fallback Block Collapse**: event/date로 확정되지 않은 middle-dot numeric block fallback에서 block 사이 공백을 제거하고 붙여 읽는 출력은 금지한다.

```text
12·3 -> 십이삼
7·25 -> 칠이오
1·2·3 -> 일이삼
123·456 -> 일이삼사오육
```

canonical output:

```text
12·3 -> 십이 삼
7·25 -> 칠 이오
1·2·3 -> 일 이 삼
123·456 -> 일이삼 사오육
```

9. **Double Reading / Reentry**: 동일 span을 둘 이상의 owner가 중복 처리한 출력은 금지한다.

```text
12.12 사태 -> 십이십이 십이쩜일이 사태       # 금지
12.3 비상계엄 -> 십이삼 십이쩜삼 비상계엄    # 금지
12·3 비상계엄 -> 십이삼 십이 삼 비상계엄     # 금지
pH 7.4 -> 피에이치 칠쩜사 칠쩜사             # 금지
15.2km/L -> 십오쩜이 리터당 십오쩜이 킬로미터 # 금지
```

10. **Invalid Decimal Reading**: dotted decimal fallback에서 decimal point reading은 정책 기본값인 `쩜`을 사용한다. 별도 runtime profile 또는 dictionary override 없이 `점`으로 출력하는 것은 금지한다.

```text
12.3 -> 십이 점 삼      # 금지
3.14 -> 삼 점 일사      # 금지
7.25 -> 칠 점 이오      # 금지
0.125 -> 영 점 일이오    # 금지
```

canonical output:

```text
12.3 -> 십이쩜삼
3.14 -> 삼쩜일사
7.25 -> 칠쩜이오
0.125 -> 영쩜일이오
```

11. **Raw Separator in Generated Reading**: generated reading 내부에 원본 separator가 남는 출력은 금지한다. 단, spaced separator handling에서 보존되는 원문 기호와 공백은 generated reading이 아니라 ORIGINAL_BOUNDARY / ORIGINAL_SPACE piece로 남아야 한다.

```text
12.3 -> 십이.삼        # 금지
12·3 -> 십이·삼        # 금지
7·25 -> 칠·이오        # 금지
12.3수치 -> 십이.삼수치 # 금지
```

허용되는 원문 보존 예:

```text
12 .3 -> 십이 .삼
12 · 3 -> 십이 · 삼
```

12. **Event Preserve Regression**: `one-digit right block`이라는 이유만으로 event candidate를 preserve하는 출력은 금지한다.

```text
12.3 비상계엄 -> 12.3 비상계엄       # 금지
12·3 비상계엄 -> 12·3 비상계엄       # 금지
12.3-비상계엄 -> 12.3-비상계엄       # 금지
12·3-비상계엄 -> 12·3-비상계엄       # 금지
```

canonical output:

```text
12.3 비상계엄 -> 십이삼 비상계엄
12·3 비상계엄 -> 십이삼 비상계엄
12.3-비상계엄 -> 십이삼-비상계엄
12·3-비상계엄 -> 십이삼-비상계엄
```

13. **Korean Lexical Tail Preserve Regression**: `numeric core + Korean lexical tail`을 unsafe contamination으로 보고 전체 preserve하는 출력은 금지한다. 숫자 core만 변환하고 한글 tail은 보존해야 한다.

```text
12.3수치 -> 12.3수치     # 금지
12·3수치 -> 12·3수치     # 금지
3.14값 -> 3.14값         # 금지
7·25자료 -> 7·25자료     # 금지
```

canonical output:

```text
12.3수치 -> 십이쩜삼수치
12·3수치 -> 십이 삼수치
3.14값 -> 삼쩜일사값
7·25자료 -> 칠 이오자료
```

14. **Hyphen-linked Event Preserve Regression**: event keyword가 hyphen으로 인접한 경우 hyphen을 contamination으로 보고 전체 preserve하는 출력은 금지한다. hyphen은 ORIGINAL_BOUNDARY로 보존하고 event keyword는 ORIGINAL_KOREAN으로 보존해야 한다.

```text
12.3-비상계엄 -> 12.3-비상계엄       # 금지
12·3-비상계엄 -> 12·3-비상계엄       # 금지
4.19-혁명 -> 4.19-혁명               # 금지
5·18-민주화운동 -> 5·18-민주화운동   # 금지
```

canonical output:

```text
12.3-비상계엄 -> 십이삼-비상계엄
12·3-비상계엄 -> 십이삼-비상계엄
4.19-혁명 -> 사일구-혁명
5·18-민주화운동 -> 오일팔-민주화운동
```

15. **Hyphen-linked Non-event Decimal Misread**: event keyword가 아닌 hyphen-linked tail에서는 숫자 core만 fallback 처리하고 hyphen과 한글 tail은 보존한다. 이때 dotted numeric은 decimal fallback, middle-dot numeric은 block fallback을 따른다.

```text
12.3-수치 -> 십이삼-수치       # 금지
12·3-수치 -> 십이삼-수치       # 금지
7.25-자료 -> 칠이오-자료       # 금지
7·25-자료 -> 칠이오-자료       # 금지
```

canonical output:

```text
12.3-수치 -> 십이쩜삼-수치
12·3-수치 -> 십이 삼-수치
7.25-자료 -> 칠쩜이오-자료
7·25-자료 -> 칠 이오-자료
```

16. **Protected Region Violation**: square bracket 내부, URL/path/email/code 내부, alnum model/code-like token을 변환하는 출력은 금지한다.

```text
[12.3] -> 십이쩜삼         # 금지
[12·3] -> 십이 삼          # 금지
A12.3B -> A십이쩜삼B       # 금지
A12·3B -> A십이 삼B        # 금지
docs/2025/01/03 -> docs/이천이십오/일/삼 # 금지
```

canonical output:

```text
[12.3] -> 12.3
[12·3] -> 12·3
A12.3B -> A12.3B
A12·3B -> A12·3B
docs/2025/01/03 -> docs/2025/01/03
```

17. **Invalid Date Fallback Violation**: invalid date를 잘못된 owner로 재처리하거나 preserve-only로 남기는 출력은 금지한다.

`####-##-##`, `####/##/##`, `####.##.##`는 모두 `date_time.date` owner가 먼저 claim한다. calendar-valid이면 날짜로 읽고, calendar-invalid이면 code separator block reading으로 fallback한다.

- calendar-valid `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY.MM.DD`는 `date_time.date` owner가 날짜로 읽는다.
- calendar-invalid `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY.MM.DD`는 `date_time.date` owner가 먼저 claim한 뒤, fallback guard를 모두 통과한 경우에만 `CODE_SEPARATOR_BLOCK_SURFACE` fallback을 허용한다.
- fallback guard는 다음을 모두 만족해야 한다.
  1. pure numeric 3-block이다.
  2. 각 block은 `4-2-2` 형태를 유지한다.
  3. 모든 구분자가 동일하다.
  4. 구분자 좌우에 공백이 없다.
  5. URL/path/email 내부가 아니다.
  6. alphabetic tail이 붙지 않았다.
  7. square bracket 보호 구간 내부가 아니다.
  8. version/log/model/code context가 아니다.
- calendar-invalid fallback은 날짜 reading, general number fallback, decimal fallback, fraction fallback이 아니다.
- fallback guard를 통과하지 못한 invalid date-like pattern은 preserve한다.

금지:

```text
2025-13-03 -> 이천이십오년 십삼월 삼일  # calendar-invalid를 날짜로 읽으면 안 됨
2025-01-32 -> 이천이십오년 일월 삼십이일 # calendar-invalid를 날짜로 읽으면 안 됨
2025-13-03 -> 이천이십오 십삼 삼       # sino block reading 금지
2025-13-03 -> 이공이오-일삼-공삼       # raw hyphen residue 금지
2025.13.03 -> 이천이십오쩜일삼쩜영삼    # dotted invalid date를 일반 decimal처럼 읽으면 안 됨
2025/13/03 -> 이천이십오 슬래시 십삼 슬래시 삼 # slash를 literal reading하면 안 됨
2025.13.03 -> 2025.13.03              # fallback guard 통과 시 preserve 금지
2025/13/03 -> 2025/13/03              # fallback guard 통과 시 preserve 금지
```

canonical output:

```text
2025-13-03 -> 이공이오 일삼 공삼
2025-01-32 -> 이공이오 공일 삼이
2024-00-10 -> 이공이사 공공 일공
2025/13/03 -> 이공이오 일삼 공삼
2025/02/30 -> 이공이오 공이 삼공
2025.13.03 -> 이공이오쩜 일삼쩜 공삼
2025.02.30 -> 이공이오쩜 공이쩜 삼공
```

preserve output:
```text
A2025-13-03 -> A2025-13-03
2025-13-03B -> 2025-13-03B
2025-13-03-1 -> 2025-13-03-1
https://example.com/2025/13/03 -> https://example.com/2025/13/03
docs/2025/13/03/report.md -> docs/2025/13/03/report.md
[2025-13-03] -> 2025-13-03
[2025/13/03] -> 2025/13/03
[2025.13.03] -> 2025.13.03
```

18. **Lexical Rewrite**: 사용자가 입력한 한글 literal, 한글 간 공백, 한글 뒤 punctuation을 수정하는 출력은 금지한다.

```text
비상계엄 -> 비상게엄       # 금지
민주화 운동 -> 민주화운동   # 금지
안녕하세요, -> 안녕하세요.  # 금지
전문  가 -> 전문 가         # 금지
```

19. **Hangul Middle-dot Rewrite**: 한글 lexical token 사이의 middle dot를 공백으로 바꾸거나 삭제하는 출력은 금지한다.

```text
자동차·부품 -> 자동차 부품       # 금지
원목·제재목 -> 원목 제재목       # 금지
산업·공급망 -> 산업 공급망       # 금지
정치적·선별 -> 정치적 선별       # 금지
훈·포장 -> 훈 포장               # 금지
AI·반도체 -> 에이아이 반도체      # 금지
ISO·IEC -> 아이에스오 아이이씨    # 금지
```

canonical output:

```text
자동차·부품 -> 자동차·부품
원목·제재목 -> 원목·제재목
산업·공급망 -> 산업·공급망
정치적·선별 -> 정치적·선별
훈·포장 -> 훈·포장
AI·반도체 -> 에이아이·반도체
ISO·IEC -> 아이에스오·아이이씨
```

20. **Unsafe Tail Partial Consume**: unit, temperature, currency, date-like, code-like 후보가 invalid tail 때문에 full consume에 실패한 경우 앞 숫자만 변환하는 출력은 금지한다.

```text
30ºCtest -> 삼십ºCtest          # 금지
40℉abc -> 사십℉abc             # 금지
45㎡abc -> 사십오㎡abc           # 금지
5Hzabc -> 오Hzabc               # 금지
15.2km/La -> 십오쩜이km/La      # 금지
2025-13-03B -> 이공이오 일삼 공삼B # 금지
USB300 -> 유에스비 삼백          # 금지
```

canonical / preserve output:

```text
30ºCtest -> 30ºCtest
40℉abc -> 40℉abc
45㎡abc -> 45㎡abc
5Hzabc -> 5Hzabc
15.2km/La -> 15.2km/La
2025-13-03B -> 2025-13-03B
USB300 -> USB300
```

21. **Area / Volume Unit Partial Consume**: area/volume unit을 일부만 읽고 superscript 또는 digit residue를 남기는 출력은 금지한다.

```text
45m² -> 사십오 미터²     # 금지
45m2 -> 사십오 미터이    # 금지
45m3 -> 사십오 미터삼    # 금지
```

canonical output:

```text
45m² -> 사십오 제곱미터
45m2 -> 사십오 제곱미터
45m3 -> 사십오 세제곱미터
```

22. **Mixed Large Unit Partial Consume**: large unit quantity에서 일부 numeric chunk만 변환하고 앞 large unit chunk를 raw로 남기는 출력은 금지한다.

```text
2만 3,000명 -> 2만 삼천 명        # 금지
1억 2,500만 원 -> 일억 2,500만 원 # 금지
8만 9천 개 -> 8만 구천 개         # 금지
```

canonical output:

```text
2만 3,000명 -> 이만 삼천 명
1억 2,500만 원 -> 일억 이천오백만 원
8만 9천 개 -> 팔만 구천 개
```


## 22. 테스트 설계

### Hyphen calendar-invalid fallback tests

Canonical fallback tests:

```text
2025-13-03 -> 이공이오 일삼 공삼
2025-01-32 -> 이공이오 공일 삼이
2024-00-10 -> 이공이사 공공 일공
```

Preserve tests:

```text
2025-1-03 -> preserve
2025-01-3 -> preserve
A2025-13-03 -> preserve
2025-13-03B -> preserve
2025-13-03-1 -> preserve
2025-13-03T13:05 -> preserve
https://example.com/2025-13-03 -> preserve
docs/2025-13-03/report.md -> preserve
user@example.com-2025-13-03 -> preserve
[2025-13-03] -> square bracket protection, output 2025-13-03
```

Forbidden signatures:

```text
2025-13-03 -> 이천이십오년 십삼월 삼일  # calendar-invalid를 날짜로 읽으면 안 됨
2025-13-03 -> 이천이십오-일삼-공삼       # partial / mixed reading 금지
2025-13-03 -> 이공이오-일삼-공삼         # raw hyphen residue 금지
2025-13-03B -> 이공이오 일삼 공삼B       # alphabetic tail partial consume 금지
[2025-13-03] -> 이공이오 일삼 공삼       # square bracket 내부 변환 금지
```

### 22.1 Canonical Examples Test

| Input | Output | Category |
|---|---|---|
| `12.3 비상계엄` | `십이삼 비상계엄` | Event |
| `12·3 비상계엄` | `십이삼 비상계엄` | Event |
| `12.3-비상계엄` | `십이삼-비상계엄` | Event |
| `12·3-비상계엄` | `십이삼-비상계엄` | Event |
| `12.3` | `십이쩜삼` | Decimal |
| `12·3` | `십이 삼` | Middle-dot |
| `12.3수치` | `십이쩜삼수치` | Lexical tail |
| `12·3수치` | `십이 삼수치` | Lexical tail |
| `12 . 3` | `십이 . 삼` | Spaced (Preserve symbol) |
| `[12.3]` | `12.3` | Preserve (Bracket) |
| `A12.3B` | `A12.3B` | Preserve (Mixed) |

```text
15.2km/La -> preserve
A-1-2 -> 에이 일 이
A-B-C -> 에이 비 씨
가-나-다 -> 가 나 다
ㄱ-ㄴ-ㄷ -> 기역 니은 디귿
1 - 2 - 3 -> 일 - 이 - 삼
OpenAI -> OpenAI
1e6 -> preserve
3.2E-4 -> preserve
3가 맞다 -> 삼가 맞다
12로 나누다 -> 십이로 나누다
2025/13/03 -> 이공이오 일삼 공삼
2025.13.03 -> 이공이오쩜 일삼쩜 공삼
```

### 22.3 Forbidden Signature Tests

출력에 절대 나오면 안 되는 signature.

```text
전문이
있은
에프티에 이
에이아가
케가-푸드
육천사백이 억
삼~8cm
일∼십일월
십이 삼 비상계엄      # event digit-sequence split 금지
십이쩜삼 비상계엄    # event를 decimal로 읽는 것 금지
12.3 비상계엄        # event candidate preserve regression 금지
에프티에이은          # FTA은 입력에서 최종 출력 금지
에이아이가            # AI이 입력에서 금지
제사와                # 제4과 입력에서 금지
종로삼이              # 종로3가 입력에서 금지
```


### 22.4 Shadow Validation Tests

예:

```text
전문  가 -> 전문  가
안녕하세요 , 반갑습니다 -> 안녕하세요 , 반갑습니다
FTA은 -> 에프티에이는
AI이 -> 에이아이이
유로을 -> 유로을  # 유로가 ORIGINAL_KOREAN이면 교정 금지
€50을 -> 오십 유로를  # 유로가 GENERATED_READING이면 Safe 을/를 교정 허용
```

검증 항목:

- original Korean literal preserved
- original spaces preserved
- original punctuation preserved
- original particles preserved
- generated Hangul excluded from original preservation comparison

### 22.5 Claim Registry Tests

예:

```text
12.3 비상계엄
-> event surface claim
-> event parser must run
-> dotted decimal fallback must not run
-> output: 십이삼 비상계엄

3~8cm
-> range_with_unit claim
-> number parser must not partially consume 3 or 8

AI·반도체
-> lexical compound claim
-> middle-dot numeric parser must not run

K-푸드
-> lexical hyphen claim
-> hyphen digit route must not run
```

### 22.6 Gate Tests

Gate pass/fail 로그를 검증한다.

```text
13:05에 -> time gate pass
13:05 -> time gate fail -> Terminal Fallback Preserve
score 12:30 -> time gate fail -> Terminal Fallback Preserve
긴급번호 112는 -> emergency pass
112명 -> emergency fail, counter policy
12.12 사태 -> event pass
12.3 비상계엄 -> event gate pass
12·3 비상계엄 -> event gate pass
12.3-비상계엄 -> event gate pass
12.3수치 -> event gate fail, dotted decimal fallback
12·3수치 -> event gate fail, middle-dot numeric block fallback
종로3가 -> administrative gate pass
3가 맞다 -> administrative gate fail
```

### 22.7 Full Consume Tests

```text
3~8cm -> success
3~8cm에서 unit residue 남기면 fail
15.2km/L -> success
15.2km/La -> preserve
5Hz -> success
5Hzabc -> preserve
```

### 22.8 Prosody Insert-only Tests

```text
안녕하세요, 반갑습니다 -> 기존 comma 유지
안녕하세요 , 반갑습니다 -> 기존 spacing 유지
그리고 12.12 사태 자료와 €1,234.56 보고서를 검토한다
-> 그리고, 십이십이 사태 자료와 천이백삼십사쩜오육 유로 보고서를 검토한다
```

단, prosody가 protected surface 내부에 comma를 넣으면 실패다.

### 22.9 Regression Test Matrix

| test axis | 목적 | 대표 입력 |
|---|---|---|
| Korean Text Immutability | 한글 literal 훼손 방지 | `전문가`, `있는` |
| Spacing Preservation | 한글 간 공백 보존 | `전문  가` |
| Punctuation Preservation | 기존 punctuation 보존 | `안녕하세요 , 반갑습니다` |
| Particle Preservation / Safe Exception | 기본 조사 보존 및 Safe 예외 검증 | `FTA은`, `AI이`, `제4과`, `종로3가` |
| Context-readable Parser Gate | context read 허용 검증 | `13:05에`, `119에 신고` |
| Typed Surface Contract | typed surface 보호 | `FTA율`, `3~8cm` |
| Protected Surface Non-Reentry | 재진입 방지 | `12.3 비상계엄` |
| Mixed Token Atomicity | partial consume 방지 | `15.2km/La` |
| Date/Time/Range Priority | owner 우선순위 | `2025-01-03`, `13:05` |
| Currency/Unit Full-Consume | residue 방지 | `€1,234.56`, `5Hzabc` |
| Emergency Context Guard | emergency 오발화 방지 | `112명`, `긴급번호 112는` |
| Prosody Preservation | insert-only 검증 | `그리고 12.12 사태...` |
| Paragraph Split Conservatism | 과도한 split 방지 | 긴 문단 |
| Forbidden Signature Regression | 알려진 회귀 차단 | global/contextual signatures |


### 22.9 Bracket Policy Tests

```text
비용은 (약) 3만원입니다 -> 비용은 삼만 원입니다
문장(임시[확인])입니다 -> 문장입니다
가격은 [3kg]입니다 -> 가격은 3kg입니다
가격은 [3kg(확인)]입니다 -> 가격은 3kg(확인)입니다
문장(임시 입니다 -> 문장(임시 입니다
가격은 [3kg입니다 -> 가격은 [3kg입니다
```

검증 항목:

- `(...)`는 처리 완료 후 전체 삭제
- `(...)` 삭제로 생긴 중복 공백만 1칸 정리
- `[...]` 내부는 normalization하지 않음
- `[...]`는 최종 출력에서 괄호 문자만 삭제
- 중첩 괄호는 가장 바깥쪽 괄호 기준
- 불완전 괄호는 preserve

### 22.10 Jamo Reading Tests

```text
ㄱ -> 기역
ㄲ -> 쌍기역
ㄴ -> 니은
ㄷ -> 디귿
ㄹ -> 리을
ㅏ -> 아
ㅘ -> 와
ㄱㄴㄷ -> 기역 니은 디귿
AㄱB -> preserve 또는 mixed token owner 필요
```

### 22.11 Safe Particle Exception Tests

```text
3를 -> 삼을
3은 -> 삼은
10는 -> 십은
2을 -> 이를
2를 -> 이를
3kg으로 -> 삼 킬로그램으로
8km으로 -> 팔 킬로미터로
AI이 -> 에이아이이
FTA은 -> 에프티에이는
FTA는 -> 에프티에이는
종로3가 -> 종로삼가
제4과 -> 제 사과
12로 나누다 -> 십이로 나누다
3가 맞다 -> 삼가 맞다
```

설명:
`3가 맞다 -> 삼가 맞다`에서 `가`는 Risky 조사군이므로 `이`로 교정하지 않는다. 이 출력은 조사 교정 금지 검증용이다.
`12로 나누다 -> 십이로 나누다`에서 `로`도 Risky 조사군이므로 `으로`로 교정하지 않는다. 이 출력도 조사 교정 금지 검증용이다.

금지:

```text
3가 맞다 -> 삼이 맞다
3가 맞다 -> 삼 맞다
12로 나누다 -> 십이으로 나누다
```

검증 항목:
- Safe 조사군만 교정
- Risky 조사군은 보존
- 단위/명사군은 보존
- Safe 조사 예외는 trace에 남김
- 일반 한글 lexical token 뒤 조사는 교정하지 않음

### 22.12 Dictionary Tests

모든 dictionary 항목은 최소 smoke test를 가져야 한다.

- `dictionary_smoke_tests`: 모든 사전 항목 1회 변환 확인
- `dictionary_collision_tests`: 단위, acronym, mixed token과 충돌 가능성이 있는 항목 확인
- `domain_profile_tests`: 방송/기술/의학 등 profile별 결과 확인
- `public_number_tests`: context + allowed tail 없이 공공번호 특수 reading이 발생하지 않음을 확인
- `event_dictionary_tests`: bare form preserve와 keyword adjacency pass를 모두 확인

### 22.13 Slash Compound Unit Tests

```text
90km/h -> 시속 구십 킬로미터
60m/min -> 분속 육십 미터
3m/s -> 초속 삼 미터
15.2km/L -> 리터당 십오쩜이 킬로미터
100mg/dL -> 데시리터당 백 밀리그램
10MB/s -> 초당 십 메가바이트
3000rpm -> 삼천 알피엠
60fps -> 육십 에프피에스
15.2km/La -> preserve
```
### 22.14 Code Separator Additional Tests

Two-block hyphen decimal-containing block:

```text
B-2.5 -> 비 이쩜오
A-3.14 -> 에이 삼쩜일사
x-3 -> 엑스 삼
ㄱ-2.5 -> 기역 이쩜오
가-3.14 -> 가 삼쩜일사
```

Preserve:

```text
B-2.5beta -> B-2.5beta
x-2.5℉ -> x-2.5℉
A-3kg -> A-3kg
```

### 22.15 Hangul Middle-dot Preservation Tests

```text
자동차·부품 -> 자동차·부품
원목·제재목 -> 원목·제재목
산업·공급망 -> 산업·공급망
정치적·선별 -> 정치적·선별
훈·포장 -> 훈·포장
미국표준협회·표준기술원 -> 미국표준협회·표준기술원
AI·반도체 -> 에이아이·반도체
ISO·IEC -> 아이에스오·아이이씨
```

Forbidden:

```text
자동차·부품 -> 자동차 부품
AI·반도체 -> 에이아이 반도체
ISO·IEC -> 아이에스오 아이이씨
```

### 22.16 Unsafe Tail Preserve Tests

```text
30ºCtest -> 30ºCtest
40℉abc -> 40℉abc
45㎡abc -> 45㎡abc
5Hzabc -> 5Hzabc
5hzabc -> 5hzabc
15.2km/La -> 15.2km/La
15.2km/lab -> 15.2km/lab
3km/speed -> 3km/speed
90km/hour -> 90km/hour
250m/Lite -> 250m/Lite
2025-13-03B -> 2025-13-03B
USB300 -> USB300
```

Forbidden:

```text
30ºCtest -> 삼십ºCtest
45㎡abc -> 사십오㎡abc
5Hzabc -> 오Hzabc
USB300 -> 유에스비 삼백
```

### 22.17 Area / Volume Unit Tests

```text
45㎡ -> 사십오 제곱미터
45m² -> 사십오 제곱미터
45m2 -> 사십오 제곱미터
45㎥ -> 사십오 세제곱미터
45m³ -> 사십오 세제곱미터
45m3 -> 사십오 세제곱미터
```

Forbidden:

```text
45m² -> 사십오 미터²
45m2 -> 사십오 미터이
45m3 -> 사십오 미터삼
```

### 22.18 Mixed Large Unit Counter Tests

```text
2만 3,000명 -> 이만 삼천 명
1억 2,500만 원 -> 일억 이천오백만 원
3조 4,000억 원 -> 삼조 사천억 원
6,402억 달러 -> 육천사백이억 달러
8만 9천 개 -> 팔만 구천 개
```

Forbidden:

```text
2만 3,000명 -> 2만 삼천 명
1억 2,500만 원 -> 일억 2,500만 원
8만 9천 개 -> 8만 구천 개
```

### 22.19 Version / Log / Model Date-like Preserve Tests

```text
버전 2025.01.03 -> 버전 2025.01.03
버전 2025.13.03 -> 버전 2025.13.03
로그 2025.02.30 -> 로그 2025.02.30
모델 2025-13-03 -> 모델 2025-13-03
코드 2025/13/03 -> 코드 2025/13/03
ID 2025.13.03 -> ID 2025.13.03
```

Non-context fallback:

```text
2025-13-03 -> 이공이오 일삼 공삼
2025/13/03 -> 이공이오 일삼 공삼
2025.13.03 -> 이공이오쩜 일삼쩜 공삼
```

### 22.20 Policy Consistency Regression Tests

#### Code separator owner naming

```text
123-456-7890 -> 일이삼 사오육 칠팔구공
1-1-9 -> 일 일 구
A-1-2 -> 에이 일 이
A-B-C -> 에이 비 씨
```

검증:

```text
owner=code_separator_block
surface_type=CODE_SEPARATOR_BLOCK_SURFACE
owner != hyphen_digit_blocks
fallback_owner != hyphen_digit_blocks
```

#### Calendar-invalid date fallback trace

```text
2025-13-03 -> 이공이오 일삼 공삼
2025/13/03 -> 이공이오 일삼 공삼
2025.13.03 -> 이공이오쩜 일삼쩜 공삼
```

검증:

```text
original_owner=date_time.date
fallback_owner=code_separator_block
fallback_reason=calendar_invalid_date_like
```

#### Version/log/model/code context preserve

```text
버전 2025.13.03 -> 버전 2025.13.03
로그 2025.02.30 -> 로그 2025.02.30
모델 2025-13-03 -> 모델 2025-13-03
코드 2025/13/03 -> 코드 2025/13/03
ID 2025.13.03 -> ID 2025.13.03
```

#### Spaced separator deterministic fallback

```text
A - B -> 에이 - 비
A - 3 -> 에이 - 삼
1 - 2 - 3 -> 일 - 이 - 삼
12 . 3 -> 십이 . 삼
1 / 3 -> 일 / 삼
```

#### Separator consumed trace

```text
A-B-C -> 에이 비 씨
12/34/56 -> 일이 삼사 오육
12.34.56 -> 일이쩜 삼사쩜 오육
```

검증:

```text
A-B-C:
- '-' source spans are recorded as SEPARATOR_CONSUMED

12/34/56:
- '/' source spans are recorded as SEPARATOR_CONSUMED

12.34.56:
- '.' source spans are rendered as GENERATED_READING("쩜 ")
```


### 23. Logging / Trace 설계

디버깅 가능한 시스템이 되려면 로그가 중요하다.

#### 23.1 Claim Log

```python
@dataclass
class ClaimLog:
    span: SourceSpan
    raw: str
    owner: str
    claim_type: str
    reason: str
    priority: int
```

예:

```text
raw="12.3", owner="event", claim_type="surface", reason="event_keyword_gate_pass"
```

### 23.2 Gate Log

```python
@dataclass
class GateLog:
    gate_name: str
    raw: str
    passed: bool
    reason: str
    action_on_fail: str
```

### 23.3 Parser Log

```python
@dataclass
class ParserLog:
    owner: str
    raw: str
    success: bool
    reading: str | None
    failure_reason: str | None
```

### 23.4 Validation Log

```python
@dataclass
class ValidationLog:
    rule: str
    passed: bool
    expected: str | None
    actual: str | None
    span: SourceSpan | None
```

### 23.5 로그 정책

정상 skip과 collision을 같은 로그에 넣지 않는다.

로그는 분리한다.

```text
skip_log       : 정상적으로 처리하지 않은 것
claim_log      : owner 점유 기록
gate_log       : gate pass/fail
collision_log  : 비정상 owner 충돌
fallback_log   : fallback 발생
validation_log : shadow validation 결과
```

Hangul plain segment마다 generic helper skip log가 과도하게 쌓일 수 있다. 새 구조에서는 skip과 collision을 반드시 분리하고, long input에서는 skip log sampling 또는 summary log를 사용할 수 있다.


### 23.6 Trace Output 예시

Event gate를 통과한 `12.3 비상계엄`은 preserve가 아니라 `EVENT_SURFACE`로 claim되고, event parser가 `십이삼` reading을 생성한다.

```json
{
  "input": "12.3 비상계엄",
  "claims": [
    {
      "raw": "12.3",
      "owner": "event",
      "claim_type": "surface",
      "surface_type": "EVENT_SURFACE",
      "reason": "event_keyword_gate_candidate",
      "span": [0, 4],
      "reentry_allowed": false
    }
  ],
  "gates": [
    {
      "gate_name": "event_keyword_gate",
      "raw": "12.3",
      "right_context": "비상계엄",
      "passed": true,
      "reason": "immediate_event_keyword_space_adjacency",
      "action_on_fail": "fallback_to_owner"
    }
  ],
  "parsing": [
    {
      "owner": "event",
      "surface_type": "EVENT_SURFACE",
      "raw": "12.3",
      "reading": "십이삼",
      "full_consume": true,
      "render_pieces": [
        {
          "text": "십이삼",
          "provenance": "GENERATED_READING",
          "source_span": [0, 4],
          "owner": "event"
        },
        {
          "text": " ",
          "provenance": "ORIGINAL_SPACE",
          "source_span": [4, 5]
        },
        {
          "text": "비상계엄",
          "provenance": "ORIGINAL_KOREAN",
          "source_span": [5, 9]
        }
      ]
    }
  ],
  "validation": {
    "passed": true
  },
  "output": "십이삼 비상계엄"
}
```

비교용 fallback trace 예시는 다음과 같다. `12.3수치`는 event keyword gate를 통과하지 못하므로 dotted decimal fallback으로 처리한다.

```json
{
  "input": "12.3수치",
  "claims": [
    {
      "raw": "12.3",
      "owner": "event",
      "claim_type": "gate_fail",
      "surface_type": "EVENT_SURFACE",
      "reason": "event_keyword_gate_fail",
      "span": [0, 4],
      "reentry_allowed": true
    },
    {
      "raw": "12.3",
      "owner": "dotted_decimal_numeric",
      "claim_type": "surface",
      "surface_type": "DOTTED_DECIMAL_NUMERIC_SURFACE",
      "reason": "event_date_gate_failed_decimal_fallback",
      "span": [0, 4],
      "reentry_allowed": false
    }
  ],
  "gates": [
    {
      "gate_name": "event_keyword_gate",
      "raw": "12.3",
      "right_context": "수치",
      "passed": false,
      "reason": "no_immediate_event_keyword",
      "action_on_fail": "fallback_to_owner"
    }
  ],
  "parsing": [
    {
      "owner": "dotted_decimal_numeric",
      "surface_type": "DOTTED_DECIMAL_NUMERIC_SURFACE",
      "raw": "12.3",
      "reading": "십이쩜삼",
      "full_consume": true,
      "render_pieces": [
        {
          "text": "십이쩜삼",
          "provenance": "GENERATED_READING",
          "source_span": [0, 4],
          "owner": "dotted_decimal_numeric"
        },
        {
          "text": "수치",
          "provenance": "ORIGINAL_KOREAN",
          "source_span": [4, 6]
        }
      ]
    }
  ],
  "validation": {
    "passed": true
  },
  "output": "십이쩜삼수치"
}
```


## 24. 개발 우선순위

Codex가 한 번에 전체 시스템을 과도하게 구현하려고 하면 구조가 무너질 수 있다. 따라서 구현 우선순위를 다음처럼 분리한다.

### P0-A — 구조 안전성

가장 먼저 구현한다.

1. `SourceSpan`
2. `SpanToken`
3. `RenderPiece`
4. `ShadowUnit`
5. `Surface`
6. `SurfaceCandidate`
7. `SurfaceClaimRegistry`
8. `TransformOutput`
9. basic render
10. shadow validation
11. 문자열 태그 직접 삽입 금지
12. `ORIGINAL_*` provenance 수정 금지
13. claim replacement 제외

목표:

```text
한글 훼손, partial consume, owner 재진입, broad 조사 교정을 구조적으로 불가능하게 만든다.
```

### P0-B — 최소 기능 parser

1. dictionary/acronym
2. number
3. date/time minimal
4. unit minimal
5. range minimal
6. emergency 112/119
7. counter `명/개`
8. full consume failure preserve

### P0-C — 정책 예외

1. Safe post-surface particle exception
2. Final Bracket Filter
3. `JAMO_SURFACE`
4. slash compound unit table
5. signed temperature / signed degree
6. range-with-unit claim priority
7. hyphen date owner 고정

### P1 — 확장

1. full dictionary inventory
2. public number subtype
3. administrative suffix
4. prosody RenderPiece migration
5. large unit atomic
6. dictionary smoke/collision/domain profile tests

### P2 — 품질 개선

1. unit-bound / range-bound full consume 강화
2. mathematical numeric owner 정교화
3. prosody가 RenderPiece 기반으로 동작하도록 개선
4. dictionary/fixed event inventory 정비
5. address anchor dictionary 기반 administrative gate 보수화

### P3 — 운영 품질

1. owner trace debug output
2. validation fail fallback 정책
3. corpus 기반 regression 확장
4. performance profiling
5. long input log volume 제어
6. validation fail 샘플링과 alert 정책

## 25. 권장 파일/모듈 구조

새로 만든다면 다음 구조가 적합하다.

```text
engine/
  core/
    spans.py
    tokens.py
    shadow.py
    render_piece.py

  surfaces/
    models.py
    registry.py
    claim_registry.py
    types.py

  gates/
    registry.py
    models.py
    time_gate.py
    event_gate.py
    emergency_gate.py
    counter_gate.py
    hyphen_gate.py
    unit_gate.py
    currency_gate.py
    range_gate.py
    administrative_gate.py
    math_gate.py

  parsers/
    lexical_parser.py
    acronym_parser.py
    event_parser.py
    date_time_parser.py
    currency_parser.py
    unit_parser.py
    range_parser.py
    hyphen_parser.py
    emergency_parser.py
    counter_parser.py
    administrative_parser.py
    math_parser.py
    number_parser.py

  pipeline/
    tokenizer.py
    claim_phase.py
    parse_phase.py
    helper_phase.py
    render_phase.py
    validation_phase.py
    transform_engine.py

  prosody/
    comma.py
    paragraph.py

  policy/
    claim_order.py
    owner_matrix.py
    forbidden_signatures.py
    canonical_cases.py
```

### 25.1 기존 파일과의 대응

| 문서 규칙 | 구현 기준 파일 / 함수 |
|---|---|
| 전체 실행 순서 | `engine.main.transform` |
| normalization orchestration | `engine.pipeline.transform_engine.normalize_text` |
| source span | `engine.core.spans.SourceSpan` |
| tokenization | `engine.pipeline.tokenizer` |
| shadow buffer | `engine.core.shadow` |
| render piece | `engine.core.render_piece` |
| typed surface contract | `engine.surfaces.models.Surface` |
| claim registry | `engine.surfaces.claim_registry.SurfaceClaimRegistry` |
| gate registry | `engine.gates.registry.GateRegistry` |
| structured parse | `engine.pipeline.parse_phase` |
| restricted helper | `engine.pipeline.helper_phase` |
| render | `engine.pipeline.render_phase` |
| shadow validation | `engine.pipeline.validation_phase` |
| prosody comma | `engine.prosody.comma.insert_commas` |
| paragraph split | `engine.prosody.paragraph.split_paragraphs` |
| runtime contract | `api/server.py -> api.binary_runtime.run_transform_binary` |

Deployment/runtime entrypoint policy is maintained in
`docs/policies/TTS_Preprocessor_deployment_policy.md`. The official
production source entrypoint is
`engine.main.transform_with_rollout(text, mode="span_default", include_debug=False)`.

For the detailed numeric valid/invalid matrix, owner-attached numeric behavior,
partial fallback audit, and trailing-zero current state, see
`docs/policies/TTS_Preprocessor_numeric_matrix.md`.

## 26. 새 규칙 추가 시 준수사항

새 규칙을 추가할 때는 다음 절차를 반드시 따른다.

1. Core Invariance Principle과 충돌하는지 확인한다.
2. owner stage를 먼저 정한다.
3. claim priority를 정한다.
4. gate가 필요한지 정한다.
5. full consume 조건을 정의한다.
6. preserve 조건을 정의한다.
7. fallback 위치를 정의한다.
8. typed surface 후보라면 생성 시점, attach 허용 여부, `allow_prosody_inside` 여부를 함께 정의한다.
9. generic helper인지 structured parser인지 먼저 분류한다.
10. forbidden signature와 canonical output을 동시에 추가한다.
11. shadow validation 대상인지 generated reading 대상인지 provenance를 정의한다.

## 27. 최종 설계 요약이 아닌 핵심 결정

이 시스템을 새롭게 만든다면 반드시 다음 결정을 고정해야 한다.

### 채택

- object/span 기반 immutable token
- `SourceSpan`
- `SpanToken`
- `RenderPiece`
- `ShadowUnit`
- `SurfaceClaimRegistry`
- Non-Reentry Registry
- owner-first routing
- `GateRegistry`
- full consume parser
- typed surface render
- original particle attach
- boundary-only smoothing
- shadow validation
- prosody insert-only

### 제거

- 문자열 태그 직접 삽입
- broad regex rewrite
- 조사 교정
- 한글 spacing repair
- punctuation repair
- owner 없는 generic fallback
- partial consume
- 동일 구간 다중 parser 재진입
- event/date/unit보다 앞선 decimal 처리
- broad administrative heuristic

## 27.1 Codex 구현 전 최종 일관성 규칙

Codex는 이 문서만 보고 전체 시스템을 구현하므로, 다음 규칙은 중복 문구나 과거 예시보다 우선한다.

1. 출력은 표준 발음 전사가 아니라 TTS 입력용 정규화 문자열이다.
2. 한글 lexical literal은 오타처럼 보여도 수정하지 않는다.
3. 조사는 기본 보존이지만, Safe post-surface particle exception은 예외다.
4. Safe 조사 예외는 owner가 확정된 generated surface 직후에만 적용한다.
5. A1 교정 허용군은 `은/는`, `을/를`, `으로`이다. A2 보존 허용군은 `이`이며, `이`는 `가`로 교정하지 않는다.
6. `가`, `로`, `과`, `와`, `도`가 입력된 경우에는 Risky 조사군이므로 수정하지 않는다.
7. `(...)`는 render와 validation이 끝난 뒤 최종 bracket filter에서 괄호와 내부 내용을 삭제한다. 삭제로 새로 생긴 중복 공백만 1칸으로 정리한다.
8. `[...]`는 Phase 1 직후 `PROTECTED_LITERAL_SURFACE`로 claim하고 내부를 무교정 보호하며 최종 bracket filter에서 괄호 문자만 삭제한다.
9. Shadow Validation은 최종 문자열 검색이 아니라 RenderPiece sequence의 provenance와 source_span 기준으로 수행한다.
10. Final Bracket Filter는 Shadow Validation 이후의 출력 shaping 단계이므로, `(...)` 삭제는 Shadow Validation 실패로 보지 않는다.
11. Slash compound unit은 이 문서의 `Slash Compound Unit Reading Inventory`에 있는 한 줄 단위 명세만 구현한다. 복수 발음 후보를 runtime에서 임의 선택하지 않는다.
12. 사전 기반 교정 용어는 dictionary smoke test에 모두 포함한다.
13. `유로을`처럼 사용자가 직접 입력한 한글 통화명 뒤 조사는 교정하지 않는다. `€50을`처럼 generated currency reading 뒤 Safe 조사는 교정할 수 있다.
14. Range-with-unit claim은 simple/special unit claim보다 먼저 실행한다.
15. `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY.MM.DD` exact `4-2-2` pattern의 owner는 `date_time.date`가 우선 claim한다. calendar-valid이면 날짜로 읽고, calendar-invalid이면 다음 조건을 모두 만족할 때만 `CODE_SEPARATOR_BLOCK_SURFACE` fallback을 허용한다: pure numeric 3-block, `4-2-2` shape 유지, 동일 구분자, 구분자 좌우 공백 없음, URL/path/email 내부 아님, alphabetic tail 없음, square bracket 보호 구간 내부 아님, version/log/model/code context 아님. 조건 실패 시 preserve한다.
16. 문서 내 오래된 예시와 본 절, `27.2 Codex Implementation Guardrails`, 또는 `30. 확장 정책`이 충돌할 경우 본 절, Guardrails, 확장 정책이 우선한다.
17. `single_letter_alnum_code`와 `CODE_SEPARATOR_BLOCK_SURFACE`는 URL/path/email/protected code context owner보다 늦지만, `A-1`, `A-B-C`, `01-02`, `1234-5678`, `123-456-7890`, `1-1-9` 같은 명시 후보는 protected code context가 broad하게 선점하면 안 된다.
18. two-block hyphen에서 한쪽 block에 숫자 이외 문자(영문, 완성형 한글, 한글 자모)가 포함되고 다른쪽 block이 정수 또는 소수이면 `CODE_SEPARATOR_BLOCK_SURFACE`로 읽는다. 단, alphabetic tail, unit tail, temperature tail, URL/path/email/code protection 내부이면 preserve한다.
19. 완성형 한글 사이 middle dot `·`는 명시 owner가 없으면 원문 보존한다. middle dot를 공백으로 치환하거나 삭제하는 broad rewrite는 금지한다.
20. unit/temperature/currency/date/code-like 후보가 invalid tail 때문에 full consume에 실패하면, 앞 숫자만 general number fallback으로 소비하지 못하도록 candidate token 전체를 preserve claim한다.
22. `m²`, `m2`, `m³`, `m3` 등 area/volume ASCII/superscript 단위는 special unit family로 full consume해야 한다.
23. large unit chunk와 following numeric chunk가 결합된 수량 표현은 partial consume을 금지한다. `2만 3,000명`처럼 앞 large unit chunk가 raw로 남고 뒤 숫자만 변환되는 출력은 금지한다.

## 27.2 Codex Implementation Guardrails

Codex는 이 문서만 보고 전체 시스템을 구현하므로, 다음 Guardrails는 기존 본문 예시나 레거시 테스트보다 우선한다.

1. 기존 API 호환을 유지한다.
   - `transform(text: str) -> str`
   - `transform_with_trace(text: str) -> TransformOutput`를 추가할 수 있다.

2. v1 구현에서는 claim replacement를 구현하지 않는다.
   - `CLAIM_ORDER` 순서대로 먼저 claim된 non-reentry span이 우선한다.
   - overlap 충돌은 preserve claim 또는 reject로 처리한다.

3. Surface span은 `core_span`과 `attach_span`을 구분한다.
   - `core_span`: generated reading 대상
   - `attach_span`: 원문 particle/context 보존 대상

4. Safe 조사 예외는 render 후, shadow validation 전 sub-step에서만 실행한다.
   - `GENERATED_PARTICLE` provenance를 사용한다.
   - 원문 particle span은 `PARTICLE_EXCEPTION_CONSUMED`로 trace에 기록한다.

5. RenderPiece provenance enum에는 최소 다음 값을 포함한다.
   - `ORIGINAL_KOREAN`
   - `ORIGINAL_SPACE`
   - `ORIGINAL_PUNCT`
   - `ORIGINAL_BOUNDARY`
   - `GENERATED_READING`
   - `GENERATED_PARTICLE`
   - `GENERATED_PUNCT`

6. Square bracket protection은 claim phase 전에 `PROTECTED_LITERAL_SURFACE`로 등록한다.
   - 내부 parser 재진입 금지
   - final bracket filter에서 `[ ]`만 삭제

7. Parenthesis elision은 final bracket filter에서만 실행한다.
   - validation 이전에는 삭제하지 않는다.
   - 괄호 내부 context는 괄호 바깥 surface gate에 사용하지 않는다.

8. Range-with-unit claim은 simple unit보다 먼저 실행한다.
   - 또는 simple unit scanner가 range-with-unit 후보 내부를 claim하지 못하게 한다.
   - 본 문서의 기본 구현은 range-with-unit 선 claim이다.

9. Modern full date owner는 `date_time.date`가 우선 claim한다.
   - `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY.MM.DD` exact `4-2-2` date-like pattern은 `date_time.date`가 최초 claim한다.
   - `hyphen_digit_blocks`, fraction, path, unit, decimal parser는 exact `4-2-2` full date-like pattern을 최초 claim하지 않는다.
   - calendar-valid `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY.MM.DD`는 날짜로 읽는다.
   - calendar-invalid full date-like `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY.MM.DD`는 code separator guard를 모두 통과한 경우에만 `CODE_SEPARATOR_BLOCK_SURFACE` fallback을 허용한다.
   - code separator guard 조건은 다음을 모두 만족해야 한다.
     1. pure numeric 3-block이다.
     2. 각 block은 `4-2-2` shape을 유지한다.
     3. 모든 구분자가 동일하다.
     4. 구분자 좌우에 공백이 없다.
     5. URL/path/email 내부가 아니다.
     6. alphabetic tail이 붙지 않았다.
     7. square bracket 보호 구간 내부가 아니다.
     8. version/log/model/code context가 아니다.
   - code separator guard 실패 시 preserve한다.

10. 한 surface 내부에 original Korean과 generated reading이 섞이면 반드시 `render_pieces`를 반환한다.

11. 문서 내 충돌 시 `27.1 Codex 구현 전 최종 일관성 규칙`, 본 Guardrails, `30. 확장 정책`이 최우선이다.

12. colon time scanner는 longest match first로 실행한다. `HH:MM:SS` 또는 `H:MM:SS` 후보가 있으면 `HH:MM` 또는 `H:MM` parser가 앞부분만 partial consume하면 안 된다.

13. modern full date owner는 `date_time.date`로 고정한다. `YYYY-MM-DD`는 `date_time.date`가 우선 claim하고, `YYYY/MM/DD`는 fraction/path/unit parser가 claim하지 않는다. calendar-invalid full date-like token은 기본 preserve가 아니라 code separator guard를 평가하며, 통과 시 `CODE_SEPARATOR_BLOCK_SURFACE` fallback을 허용한다. 단, URL/path-like slash token과 protected span은 preserve한다.

14. dictionary expansion entry는 반드시 safety class와 claim_policy를 가진다. 단위/통화/파일크기/복합단위는 대부분 숫자 prefix 또는 context gate를 요구하며, dictionary 항목은 smoke, condition, collision, shadow test에 포함한다.

## 28. 본문과 레거시 정책의 관계

이 문서는 기존 통합 정책을 폐기하는 문서가 아니라, 기존 정책의 안전 원칙을 object/span 기반 아키텍처로 재구성한 실행 명세서다.

본문에 남겨야 하는 항목:

- owner stage
- gate
- threshold
- full consume
- preserve 조건
- canonical output
- forbidden signature
- shadow validation
- non-reentry
- prosody insert-only

본문에 두면 흐름을 흐리는 항목:

- 과거 placeholder 구현 세부
- 제거된 helper 경로
- 더 이상 허용하지 않는 broad 조사 교정 경로
- 문자열 태그 기반 설명
- deprecated fallback

이런 항목은 별도 legacy 문서에 보존할 수 있다. 단, 구현 기준은 본 문서가 우선한다.

## 29. 최종 한 문장 정의

이 시스템의 최적 구조는 다음이다.

> 원본 입력을 span 단위로 보존하고, 변환 가능한 수치·기호 구간만 owner가 먼저 점유한 뒤, gate를 통과한 typed surface만 full consume 방식으로 발음화하며, 최종 render 후 shadow validation으로 원본 한글 literal·공백·문장부호·조사 보존을 검증하되, 명시된 Safe post-surface particle exception은 별도 provenance로 검증하는 TTS 전처리 파이프라인.

이 구조는 물리적 보호, 계층적 탐지, non-reentry, context-aware gate, shadow validation을 모두 살리면서도, 문자열 태그 충돌, parser context 손실, 무제한 조사 교정 부활, broad heuristic, 기존 정책 불일치를 제거한다.


## 30. 확장 정책: 날짜, 시간, 사전 기반 교정 용어

이 절의 모든 날짜/구분자 정책에서 `hyphen_digit_blocks`라는 과거 명칭이 발견되면, 구현 기준으로는 `CODE_SEPARATOR_BLOCK_SURFACE` 또는 owner id `code_separator_block`으로 해석한다.

현행 구현 기준:

- owner id: `code_separator_block`
- surface type: `CODE_SEPARATOR_BLOCK_SURFACE`
- date fallback trace:
  - `original_owner=date_time.date`
  - `fallback_owner=code_separator_block`
  - `fallback_reason=calendar_invalid_date_like`

금지:

```text
fallback_owner=hyphen_digit_blocks
owner=hyphen_digit_blocks
```

허용:

```text
fallback_owner=code_separator_block
owner=code_separator_block
surface_type=CODE_SEPARATOR_BLOCK_SURFACE
```

### 30.1 Short Dotted / Middle-Dot Numeric 정책 (Phase 28A)

#### 30.1.1 Owner Priority 및 Fallback

1. **Square Bracket Protection**: 가장 먼저 보호한다.
2. **URL/Path/Email/Code Protection**: 식별자 형태 보호.
3. **Fixed Event Dictionary**: 사전 정의된 이벤트 우선.
4. **Event Candidate**: `M.D` / `M·D` + (공백/하이픈) + `Event Keyword`.
5. **Modern Date/Time**: 유효한 날짜 및 시간.
6. **Numeric Fallback**:
   - `.` (Dot) -> `dotted_decimal_numeric` (`쩜` 읽기)
   - `·` (Middle-dot) -> `middle_dot_numeric_block` (공백 읽기)

#### 30.1.2 Spaced Separator 처리

숫자와 기호 사이에 공백이 있는 경우(`12 . 3`), 이를 단일 numeric block으로 full consume하지 않는다. 기호와 공백은 보존(`ORIGINAL_BOUNDARY`, `ORIGINAL_SPACE`)하고 숫자만 각각 normalize한다.

- `12 . 3` -> `십이 . 삼`
- `12 · 3` -> `십이 · 삼`

#### 30.1.3 Korean Lexical Tail

숫자 뒤에 붙은 한글(`12.3수치`)은 contamination으로 보지 않는다. 숫자를 먼저 normalize하고 한글 literal을 보존한다.

- `12.3수치` -> `십이쩜삼수치`
- `12·3수치` -> `십이 삼수치`

#### 30.1.4 Hyphen-linked Event

하이픈으로 연결된 이벤트 키워드도 이벤트로 인식한다. 하이픈은 보존한다.

- `12.3-비상계엄` -> `십이삼-비상계엄`
- `12·3-비상계엄` -> `십이삼-비상계엄`

이벤트 키워드가 없는 하이픈 테일은 numeric fallback 후 하이픈을 보존한다.

- `12.3-수치` -> `십이쩜삼-수치`
- `12·3-수치` -> `십이 삼-수치`
- Safe post-surface particle exception은 surface가 성공적으로 생성된 뒤, render 후 Shadow Validation 전 sub-step에서만 적용한다.
- `[...]` 내부는 무교정 보호이므로 날짜/시간/단위/사전 parser가 진입하지 않는다.
- `(...)` 내부 token은 괄호 바깥 surface의 gate/context 판단에 사용하지 않는다.

## 31. Time Expansion: `H:MM` short colon time

### 31.1 목적

기존 `HH:MM` 시간 규칙에 더해 다음 입력을 제한적으로 지원한다.

```text
#:##
```

대표 예:

```text
1:05
2:30
7:00
9:45
```

목표 출력:

```text
회의는 1:05에 시작한다 -> 회의는 한시 오분에 시작한다
오후 2:30 회의 -> 오후 두시 삼십분 회의
7:00에 출발 -> 일곱시에 출발
```

단독 `1:05`는 ambiguous preserve가 기본이다.

### 31.2 Owner / surface

```text
owner: date_time.time_colon
surface_type: TIME_SURFACE
metadata.subtype: H_MM_SHORT
```

### 31.3 지원 패턴

```regex
(?<![\dA-Za-z])([0-9]):([0-5][0-9])(?![:\dA-Za-z])
```

허용 후보:

```text
0:05
1:05
2:30
7:00
9:45
```

비허용 후보:

```text
12:30   # HH:MM owner 대상
1:5     # minute 두 자리 아님
1:005   # minute 세 자리
1:05:30 # H:MM_SHORT가 partial consume하면 안 됨
A1:05   # attached alnum
1:05B   # attached alnum
```

### 31.4 Claim order

colon time scanner는 longest match first로 실행한다.

```text
1. HH:MM:SS
2. H:MM:SS
3. HH:MM
4. H:MM
```

`H:MM` parser는 `H:MM:SS`의 앞부분을 claim하면 안 된다.

### 31.5 Gate

Gate 이름:

```text
time_short_colon_context_gate
```

통과 조건은 다음 중 하나 이상이다.

- time prefix 존재: `오전`, `오후`, `새벽`, `아침`, `정오`, `밤`, `저녁`
- time postposition 존재: `에`, `까지`, `부터`, `경`, `쯤`, `정각`
- time-event keyword 존재: `출발`, `도착`, `시작`, `종료`, `마감`, `개시`, `오픈`, `폐장`, `예약`, `탑승`, `발차`, `상영`, `회의`, `수업`, `진료`, `시각`, `시간`, `방송`, `편성`, `경기`, `킥오프`
- 한국어 날짜 좌문맥 존재
- schedule/list UI context 존재: `일정`, `시간표`, `편성표`, `타임라인`, `상영표`, `알림`, `예약시간`, `시작시간`, `종료시간`

차단 조건:

- 단독 전체 입력
- score / ratio 문맥
- port-like 문맥
- version-like 문맥
- chapter/verse-like 문맥
- 다중 colon 패턴
- attached alphanumeric
- minute 값 범위 오류

### 31.6 Render

Hour는 native hour reading을 사용한다.

| 입력 hour | reading |
|---:|---|
| `0` | `영` |
| `1` | `한` |
| `2` | `두` |
| `3` | `세` |
| `4` | `네` |
| `5` | `다섯` |
| `6` | `여섯` |
| `7` | `일곱` |
| `8` | `여덟` |
| `9` | `아홉` |

Minute는 sino number를 사용한다.

```text
H:MM -> native_hour + "시" + minute_reading
```

`MM == 00`이면 `영분`을 출력하지 않고 `시`까지만 읽는다.

```text
1:05에 -> 한시 오분에
2:30부터 -> 두시 삼십분부터
7:00에 -> 일곱시에
0:05에 -> 영시 오분에
```

### 31.7 Span / ParserResult

```python
SurfaceCandidate(
    core_span=SourceSpan(start, colon_time_end),
    full_span=SourceSpan(start, particle_end),
    owner="date_time.time_colon",
    surface_type="TIME_SURFACE",
    trailing_particle_span=SourceSpan(particle_start, particle_end),
    metadata={
        "subtype": "H_MM_SHORT",
        "hour": 1,
        "minute": 5,
    },
)
```

`trailing_particle_span`은 generated reading으로 덮지 않고 `ORIGINAL_KOREAN` provenance를 유지한다.

### 31.8 Canonical / preserve / gate tests

| 입력 | canonical output | 핵심 규칙 |
|---|---|---|
| `회의는 1:05에 시작한다` | `회의는 한시 오분에 시작한다` | `H:MM` time gate + postposition |
| `오후 2:30 회의` | `오후 두시 삼십분 회의` | time prefix |
| `7:00에 출발` | `일곱시에 출발` | zero minute omission |
| `0:05에 시작` | `영시 오분에 시작` | zero hour |
| `1:05` | `1:05` | standalone ambiguous preserve |
| `스코어 1:05` | `스코어 1:05` | score context preserve |
| `창세기 1:05` | `창세기 1:05` | chapter/verse preserve |

Preserve tests:

```text
1:05 -> preserve
1:5 -> preserve
1:005 -> preserve
1:05:30 -> H:MM parser must not partially consume
A1:05 -> preserve
1:05B -> preserve
스코어 1:05 -> preserve
창세기 1:05 -> preserve
localhost:8080 -> preserve
```

Gate tests:

```text
1:05에 -> time_short_colon_context_gate pass
오전 1:05 -> time_short_colon_context_gate pass
오후 2:30 회의 -> time_short_colon_context_gate pass
1:05 -> time_short_colon_context_gate fail preserve
스코어 1:05 -> time_short_colon_context_gate fail preserve
창세기 1:05 -> time_short_colon_context_gate fail preserve
```

## 32. Time Expansion: `H:MM:SS` short colon time with seconds

### 32.1 목적

다음 입력을 제한적으로 지원한다.

```text
#:##:##
```

대표 예:

```text
1:05:30
2:30:00
7:00:05
9:45:12
```

이 표면형은 시각(clock)일 수도 있고 재생시간/경과시간(duration)일 수도 있으므로, semantic gate를 통해 구분한다.

```text
회의는 1:05:30에 시작한다 -> 회의는 한시 오분 삼십초에 시작한다
영상 길이는 1:05:30이다 -> 영상 길이는 한시간 오분 삼십초이다
```

### 32.2 Owner / subtype

```text
owner: date_time.time_colon
surface_type: TIME_SURFACE
metadata.subtype: H_MM_SS_SHORT
metadata.semantic: clock | duration
```

### 32.3 지원 패턴

```regex
(?<![\dA-Za-z])([0-9]):([0-5][0-9]):([0-5][0-9])(?![:\dA-Za-z])
```

허용 후보:

```text
0:05:30
1:05:30
2:30:00
7:00:05
9:45:12
```

비허용 후보:

```text
12:30:05   # HH:MM:SS owner
1:5:30
1:05:3
1:005:30
1:05:300
A1:05:30
1:05:30B
1:05:30:2
```

### 32.4 Claim order

```text
1. HH:MM:SS
2. H:MM:SS
3. HH:MM
4. H:MM
```

`H:MM` parser는 `H:MM:SS`의 앞부분 `H:MM`을 partial consume하면 안 된다.

### 32.5 Gate

Gate 이름:

```text
time_short_colon_seconds_context_gate
```

Gate는 두 단계로 나눈다.

1. shape/value gate
2. semantic context gate

Shape/value gate:

- hour: `0~9`
- minute: `00~59`
- second: `00~59`
- full consume
- not attached alnum
- not colon chain

Semantic context gate:

Clock context는 다음 중 하나 이상이 있을 때 통과한다.

- time prefix: `오전`, `오후`, `새벽`, `아침`, `정오`, `밤`, `저녁`
- clock postposition: `에`, `까지`, `부터`, `경`, `쯤`, `정각`
- clock event keyword: `출발`, `도착`, `시작`, `종료`, `마감`, `개시`, `오픈`, `폐장`, `예약`, `탑승`, `발차`, `상영`, `회의`, `수업`, `진료`, `시각`, `시간`, `방송`, `편성`, `경기`, `킥오프`
- clock UI context: `일정`, `시간표`, `편성표`, `타임라인`, `상영표`, `알림`, `예약시간`, `시작시간`, `종료시간`

Duration context는 다음 중 하나 이상이 있을 때 통과한다.

- duration keyword: `길이`, `분량`, `재생시간`, `러닝타임`, `상영시간`, `소요시간`, `경과시간`, `남은시간`, `잔여시간`, `총시간`, `duration`, `runtime`, `elapsed`, `remaining`
- media keyword: `영상`, `동영상`, `오디오`, `음원`, `녹음`, `녹화`, `클립`, `파일`, `트랙`, `에피소드`, `방송분`, `재생`, `구간`, `타임코드`, `타임라인`
- record keyword: `기록`, `랩타임`, `구간기록`, `완주기록`, `측정값`, `타이머`, `스톱워치`

둘 다 gate pass하면 다음 우선순위를 적용한다.

1. explicit duration/media keyword가 있으면 duration
2. explicit clock prefix/postposition이 있으면 clock
3. 둘 다 강하면 preserve

차단 조건:

- 단독 전체 입력
- score / ratio 문맥
- port-like 문맥
- version-like 문맥
- chapter/verse-like 문맥
- log/timestamp ambiguity
- colon chain
- attached alphanumeric
- minute/second 값 범위 오류

### 32.6 Render

Clock render:

```text
H:MM:SS -> native_hour + "시" + minute + "분" + second + "초"
```

Zero handling:

```text
minute == 0 and second == 0 -> hour only
minute == 0 and second > 0 -> hour + second
minute > 0 and second == 0 -> hour + minute
minute > 0 and second > 0 -> hour + minute + second
```

예:

```text
1:05:30에 -> 한시 오분 삼십초에
2:30:00에 -> 두시 삼십분에
7:00:05에 -> 일곱시 오초에
0:05:30에 -> 영시 오분 삼십초에
```

Duration render:

```text
H:MM:SS -> native_hour + "시간" + minute + "분" + second + "초"
```

Zero handling:

```text
hour == 0이면 hour 생략
minute == 0이면 minute 생략
second == 0이면 second 생략
단, 모두 0이면 "영초"
```

예:

```text
1:05:30 -> 한시간 오분 삼십초
2:30:00 -> 두시간 삼십분
0:05:30 -> 오분 삼십초
0:00:05 -> 오초
0:00:00 -> 영초
```

### 32.7 Canonical / preserve / gate tests

| 입력 | canonical output | 핵심 규칙 |
|---|---|---|
| `회의는 1:05:30에 시작한다` | `회의는 한시 오분 삼십초에 시작한다` | clock gate + postposition |
| `오후 2:30:00 회의` | `오후 두시 삼십분 회의` | clock prefix + zero second omission |
| `7:00:05에 출발` | `일곱시 오초에 출발` | zero minute + second |
| `영상 길이는 1:05:30이다` | `영상 길이는 한시간 오분 삼십초이다` | duration/media context |
| `러닝타임 2:30:00` | `러닝타임 두시간 삼십분` | duration zero second omission |
| `0:05:30 남음` | `오분 삼십초 남음` | duration zero hour omission |
| `1:05:30` | `1:05:30` | standalone ambiguous preserve |
| `스코어 1:05:30` | `스코어 1:05:30` | score context preserve |
| `창세기 1:05:30` | `창세기 1:05:30` | chapter/verse preserve |

Preserve tests:

```text
1:05:30 -> preserve
1:5:30 -> preserve
1:05:3 -> preserve
1:005:30 -> preserve
1:05:300 -> preserve
A1:05:30 -> preserve
1:05:30B -> preserve
1:05:30:2 -> preserve
스코어 1:05:30 -> preserve
창세기 1:05:30 -> preserve
로그 1:05:30 -> preserve
```

## 33. Date Expansion: `YYYY-MM-DD` modern hyphen date

### 33.1 목적

다음 입력을 엄격한 조건으로 날짜로 읽는다.

```text
####-##-##
YYYY-MM-DD
```

### 33.2 Owner / subtype

```text
owner: date_time.date
surface_type: DATE_SURFACE
metadata.subtype: YYYY_MM_DD_HYPHEN
```

중요:

* `YYYY-MM-DD` exact `4-2-2` pattern은 `date_time.date` owner가 우선 claim한다.
* hyphen_digit_blocks scanner는 exact `4-2-2` date-like pattern을 최초 claim하지 않는다.
* calendar-valid이면 DATE_SURFACE로 render한다.
* calendar-invalid이면 곧바로 preserve하지 않고 fallback guard를 평가한다.
* fallback guard를 모두 통과하면 `CODE_SEPARATOR_BLOCK_SURFACE` fallback으로 digit-by-digit block reading한다.
* code separator guard 실패 시 preserve한다.
* fallback guard 조건:

  1. pure numeric 3-block이다.
  2. 각 block은 `4-2-2` 형태를 유지한다.
  3. URL/path/email 내부가 아니다.
  4. alphabetic tail이 붙지 않았다.
  5. square bracket 보호 구간 내부가 아니다.

### 33.3 지원 패턴

```regex
(?<![\dA-Za-z])([0-9]{4})-([0-9]{2})-([0-9]{2})(?![\dA-Za-z-])
```

이 패턴은 `date_time.date` 우선 claim 후보를 찾기 위한 패턴이다.

fallback guard용 shape는 다음과 같이 별도로 정의한다.

```regex
([0-9]{4})-([0-9]{2})-([0-9]{2})
```

fallback guard는 regex match만으로 통과하지 않는다. 반드시 다음 조건을 모두 확인한다.

1. pure numeric 3-block이다.
2. 각 block은 `4-2-2` 형태를 유지한다.
3. URL/path/email 내부가 아니다.
4. alphabetic tail이 붙지 않았다.
5. square bracket 보호 구간 내부가 아니다.

### 33.4 Gate

Gate 이름:

```text
date_hyphen_yyyy_mm_dd_gate
```

Gate는 다음을 검사한다.

1. exact `4-2-2` hyphen shape
2. year range `1900~2099`
3. month range `01~12`
4. day range `01~last_day_of_month(year, month)`
5. safe left/right boundary
6. not part of hyphen chain
7. not attached alnum
8. not explicit code/model/version/log context
9. not URL/path/email context
10. not inside square bracket protected span

여기서 `calendar-invalid`는 year range와 boundary/context gate를 통과했지만 month/day calendar validity만 실패한 상태를 의미한다.

따라서 다음은 calendar-invalid fallback 대상이 아니다.

```text
1899-13-03 -> preserve  # year range fail
2100-13-03 -> preserve  # year range fail
A2025-13-03 -> preserve # boundary/alnum fail
2025-13-03B -> preserve # alphabetic tail fail
[2025-13-03] -> 2025-13-03 # square bracket protection
```

Gate 결과는 다음처럼 분기한다.

| 결과 | 동작 |
|---|---|
| 1~10 모두 통과 | DATE_SURFACE로 render |
| calendar-invalid만 실패하고 fallback guard 통과 | `CODE_SEPARATOR_BLOCK_SURFACE` fallback |
| year range 실패 | preserve |
| safe boundary 실패 | preserve |
| hyphen chain | preserve |
| attached alnum / alphabetic tail | preserve |
| code/model/version/log context | preserve |
| URL/path/email context | preserve |
| square bracket protected span 내부 | square bracket protection 우선, 내부 무교정 |

Year range:

```text
1900 <= year <= 2099
```

Calendar validity:

```python
def is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

def last_day_of_month(year: int, month: int) -> int:
    if month in {1, 3, 5, 7, 8, 10, 12}:
        return 31
    if month in {4, 6, 9, 11}:
        return 30
    if month == 2:
        return 29 if is_leap_year(year) else 28
    raise ValueError("invalid month")
```

Code/model/version/log 차단 keyword:

```text
코드, 상품코드, 모델, 모델명, 버전, version, ver, v, ID, 아이디, 로그, log, 에러, error,
빌드, build, 커밋, commit, 해시, hash, 티켓, ticket, 이슈, issue, 문서번호, 관리번호, 주문번호
```

Date context keyword:

```text
날짜, 일자, 일시, 회의일, 마감일, 시작일, 종료일, 등록일, 작성일, 수정일, 발행일,
기준일, 생년월일, 예약일, 방문일, 출발일, 도착일
```

Conflict rule:

```text
code/model/version context와 date context가 동시에 강하면 preserve한다.
```

### 33.5 Render

```text
YYYY-MM-DD -> {year}년 {month}월 {day}일
```

```text
2025-01-03 -> 이천이십오년 일월 삼일
1999-12-31 -> 천구백구십구년 십이월 삼십일일
2000-02-29 -> 이천년 이월 이십구일
2026-06-17 -> 이천이십육년 유월 십칠일
2026-10-01 -> 이천이십육년 시월 일일
```

calendar-invalid `YYYY-MM-DD`가 fallback guard를 통과한 경우에는 DATE_SURFACE render를 사용하지 않고, `CODE_SEPARATOR_BLOCK_SURFACE` fallback render를 사용한다.

이 fallback render는 날짜 reading이 아니다.

trace에는 다음을 기록한다.

```text
original_owner=date_time.date
fallback_owner=code_separator_block
fallback_reason=calendar_invalid_date_like
```

YYYY-MM-DD calendar-invalid fallback -> {yyyy_digits} {mm_digits} {dd_digits}

예:
```text
2025-13-03 -> 이공이오 일삼 공삼
2025-01-32 -> 이공이오 공일 삼이
2024-00-10 -> 이공이사 공공 일공
```


### 33.6 Square bracket / parenthesis

- `[2025-01-03] -> 2025-01-03`: square bracket protection으로 날짜 parser 진입 금지
- `회의일은 (2025-01-03)입니다 -> 회의일은 입니다`: parenthesis final filter에서 전체 삭제
- parenthesis 내부 날짜는 괄호 바깥 surface gate/context에 영향을 주면 안 된다.


### 33.7 Canonical / preserve / gate tests

| 입력 | canonical output | 핵심 규칙 |
|---|---|---|
| `2025-01-03` | `이천이십오년 일월 삼일` | modern hyphen date, calendar-valid |
| `회의일은 2025-01-03입니다` | `회의일은 이천이십오년 일월 삼일입니다` | date context |
| `1999-12-31` | `천구백구십구년 십이월 삼십일일` | year range pass |
| `2000-02-29` | `이천년 이월 이십구일` | leap year pass |
| `2024-02-29` | `이천이십사년 이월 이십구일` | leap year pass |
| `2025-13-03` | `이공이오 일삼 공삼` | calendar-invalid + code separator guard pass |
| `2025-01-32` | `이공이오 공일 삼이` | calendar-invalid + code separator guard pass |
| `2024-00-10` | `이공이사 공공 일공` | calendar-invalid + code separator guard pass |
| `1899-12-31` | `1899-12-31` | year range fail |
| `2100-01-01` | `2100-01-01` | year range fail |
| `모델 2025-01-03` | `모델 2025-01-03` | code/model context preserve |
| `[2025-13-03]` | `2025-13-03` | square bracket protection, fallback 금지 |
| `A2025-13-03` | `A2025-13-03` | attached alnum preserve |
| `2025-13-03B` | `2025-13-03B` | alphabetic tail preserve |

Preserve tests:

```text
1899-12-31 -> preserve
2100-01-01 -> preserve
2025-1-03 -> preserve
2025-01-3 -> preserve
A2025-13-03 -> preserve
2025-13-03B -> preserve
2025-13-03-1 -> preserve
2025-13-03T13:05 -> preserve
user@example.com-2025-13-03 -> preserve
https://example.com/2025-13-03 -> preserve
docs/2025-13-03/report.md -> preserve
[2025-13-03] -> square bracket protection, output 2025-13-03
모델 2025-13-03 -> preserve
버전 2025-13-03 -> preserve
로그 2025-13-03 -> preserve
```

## 34. Date Expansion: `YYYY/MM/DD` modern slash date

### 34.1 목적

다음 입력을 엄격한 조건으로 먼저 날짜 owner가 검사한다.

```text
####/##/##
YYYY/MM/DD
```

Slash date는 path/URL/fraction과 충돌하기 쉬우므로 강한 URL/path 차단 조건을 가진다. 단, date owner가 calendar-invalid만 확인한 경우에는 preserve-only가 아니라 `CODE_SEPARATOR_BLOCK_SURFACE` fallback을 허용한다.

### 34.2 Owner / subtype

```text
owner: date_time.date
surface_type: DATE_SURFACE
metadata.subtype: YYYY_MM_DD_SLASH
```

중요:

* `2025/01/03`의 최종 owner는 fraction, path, unit, generic slash parser가 아니다.
* date parse 성공 시 DATE_SURFACE로 읽는다.
* date parse 실패가 calendar-invalid뿐이고 fallback guard를 통과하면 `CODE_SEPARATOR_BLOCK_SURFACE`로 fallback한다.
* URL/path-like context, square bracket 내부, alphabetic attachment, slash chain이면 fallback하지 않고 preserve한다.

### 34.3 지원 패턴

```regex
(?<![\dA-Za-z/])([0-9]{4})/([0-9]{2})/([0-9]{2})(?![\dA-Za-z/])
```

date owner 후보이나 calendar-invalid fallback 대상:

```text
2025/13/01
2025/00/01
2025/01/00
2025/02/30
```

비허용 후보:

```text
1899/12/31
2100/01/01
2025/1/03
2025/01/3
A2025/01/03
2025/01/03B
2025/01/03/1
/path/2025/01/03
https://example.com/2025/01/03
docs/2025/01/03/report.md
[2025/13/01]
```

### 34.4 Claim order

```text
url/path protection
square bracket protection
date_time.date.YYYY_MM_DD_HYPHEN
date_time.date.YYYY_MM_DD_SLASH
date_time.date.YYYY_MM_DD_DOTTED
code_separator_block
fraction
unit/compound_unit
generic number
```

URL/path-like token이면 date slash claim과 code separator fallback을 모두 시도하지 않는다.

### 34.5 Gate

Gate 이름:

```text
date_slash_yyyy_mm_dd_gate
```

Gate는 다음을 모두 검사한다.

1. exact `4-2-2` slash shape
2. year range `1900~2099`
3. month range `01~12`
4. day range `01~last_day_of_month(year, month)`
5. safe left/right boundary
6. not part of slash chain
7. not attached alnum
8. not URL/path-like context
9. not explicit code/model/version/log context
10. not inside square bracket protected span

Gate 결과는 다음처럼 분기한다.

| 결과                                       | 동작                                      |
| ---------------------------------------- | --------------------------------------- |
| 1~10 모두 통과                               | DATE_SURFACE로 render                    |
| calendar-invalid만 실패하고 fallback guard 통과 | `CODE_SEPARATOR_BLOCK_SURFACE` fallback |
| year range 실패                            | preserve                                |
| shape 실패                                 | preserve                                |
| safe boundary 실패                         | preserve                                |
| slash chain                              | preserve                                |
| attached alnum / alphabetic tail         | preserve                                |
| code/model/version/log context           | preserve                                |
| URL/path/email context                   | preserve                                |
| square bracket protected span 내부         | square bracket protection 우선, 내부 무교정    |

URL/path-like 차단 조건:

* `://` 포함
* 가까운 앞 문맥에 `http`, `https`, `ftp`, `file`, `s3`, `gs` scheme 존재
* 앞쪽 또는 뒤쪽에 경로 segment가 이어짐
* 확장자 또는 파일명 문맥 존재
* 연속 slash chain

차단 예:

```text
https://example.com/2025/01/03
/file/2025/01/03
docs/2025/01/03
2025/01/03/report.md
s3://bucket/2025/01/03
```

### 34.6 Render

calendar-valid이면 `YYYY-MM-DD`와 동일한 date render 함수를 재사용한다.

```text
YYYY/MM/DD -> {year}년 {month}월 {day}일
```

```text
2025/01/03 -> 이천이십오년 일월 삼일
1999/12/31 -> 천구백구십구년 십이월 삼십일일
2000/02/29 -> 이천년 이월 이십구일
2026/06/17 -> 이천이십육년 유월 십칠일
2026/10/01 -> 이천이십육년 시월 일일
```

calendar-invalid `YYYY/MM/DD`가 fallback guard를 통과한 경우에는 DATE_SURFACE render를 사용하지 않고, `CODE_SEPARATOR_BLOCK_SURFACE` fallback render를 사용한다.

```text
YYYY/MM/DD calendar-invalid fallback -> {yyyy_digits} {mm_digits} {dd_digits}

예:
2025/13/03 -> 이공이오 일삼 공삼
2025/02/30 -> 이공이오 공이 삼공
2025/01/00 -> 이공이오 공일 공공
```

### 34.7 Canonical / preserve / gate tests

| 입력                   | canonical output       | 핵심 규칙                                      |
| -------------------- | ---------------------- | ------------------------------------------ |
| `2025/01/03`         | `이천이십오년 일월 삼일`         | modern slash date                          |
| `회의일은 2025/01/03입니다` | `회의일은 이천이십오년 일월 삼일입니다` | date context                               |
| `1999/12/31`         | `천구백구십구년 십이월 삼십일일`     | year range pass                            |
| `2000/02/29`         | `이천년 이월 이십구일`          | leap year pass                             |
| `2024/02/29`         | `이천이십사년 이월 이십구일`       | leap year pass                             |
| `2025/13/01`         | `이공이오 일삼 공일`           | calendar-invalid + code separator fallback |
| `2025/00/01`         | `이공이오 공공 공일`           | calendar-invalid + code separator fallback |
| `2025/01/00`         | `이공이오 공일 공공`           | calendar-invalid + code separator fallback |
| `2025/02/30`         | `이공이오 공이 삼공`           | calendar-invalid + code separator fallback |
| `1899/12/31`         | `1899/12/31`           | year range fail                            |
| `2100/01/01`         | `2100/01/01`           | year range fail                            |
| `경로 docs/2025/01/03` | `경로 docs/2025/01/03`   | path context preserve                      |
| `[2025/13/01]`       | `2025/13/01`           | square bracket protection                  |

Preserve tests:

```text
1899/12/31 -> preserve
2100/01/01 -> preserve
2025/1/03 -> preserve
2025/01/3 -> preserve
A2025/01/03 -> preserve
2025/01/03B -> preserve
2025/01/03/1 -> preserve
2025/01/03T13:05 -> preserve
https://example.com/2025/01/03 -> preserve
docs/2025/01/03/report.md -> preserve
모델 2025/01/03 -> preserve
버전 2025/01/03 -> preserve
로그 2025/01/03 -> preserve
[2025/13/01] -> square bracket protection, output 2025/13/01
```

## 34A. Date Expansion: `YYYY.MM.DD` modern dotted date

### 34A.1 목적

다음 입력을 엄격한 조건으로 먼저 날짜 owner가 검사한다.

```text
####.##.##
YYYY.MM.DD
```

Dotted date는 decimal, event dotted form, version/code-like token과 충돌하기 쉬우므로 date owner와 event owner가 먼저 판단하고, calendar-invalid인 경우에만 `CODE_SEPARATOR_BLOCK_SURFACE` fallback을 허용한다.

### 34A.2 Owner / subtype

```text
owner: date_time.date
surface_type: DATE_SURFACE
metadata.subtype: YYYY_MM_DD_DOTTED
```

중요:

* `2025.01.03`의 최종 owner는 decimal parser가 아니다.
* date parse 성공 시 DATE_SURFACE로 읽는다.
* date parse 실패가 calendar-invalid뿐이고 fallback guard를 통과하면 `CODE_SEPARATOR_BLOCK_SURFACE`로 fallback한다.
* URL/path-like context, square bracket 내부, alphabetic attachment, mixed separator이면 fallback하지 않고 preserve한다.

### 34A.3 지원 패턴

```regex
(?<![\dA-Za-z.])([0-9]{4})\.([0-9]{2})\.([0-9]{2})(?![\dA-Za-z.])
```

date owner 후보이나 calendar-invalid fallback 대상:

```text
2025.13.01
2025.00.01
2025.01.00
2025.02.30
```

비허용 후보:

```text
1899.12.31
2100.01.01
2025.1.03
2025.01.3
A2025.01.03
2025.01.03B
2025.01.03.1
version 2025.01.03
[2025.13.01]
```

### 34A.4 Claim order

```text
url/path/email/code protection
square bracket protection
event
date_time.date.YYYY_MM_DD_HYPHEN
date_time.date.YYYY_MM_DD_SLASH
date_time.date.YYYY_MM_DD_DOTTED
code_separator_block
dotted_decimal_numeric
math_numeric
generic number
```

### 34A.5 Gate

Gate 이름:

```text
date_dotted_yyyy_mm_dd_gate
```

Gate는 다음을 모두 검사한다.

1. exact `4-2-2` dotted shape
2. year range `1900~2099`
3. month range `01~12`
4. day range `01~last_day_of_month(year, month)`
5. safe left/right boundary
6. not part of dotted chain
7. not attached alnum
8. not URL/path/email/code-like context
9. not explicit code/model/version/log context
10. not inside square bracket protected span

Gate 결과는 다음처럼 분기한다.

| 결과                                       | 동작                                      |
| ---------------------------------------- | --------------------------------------- |
| 1~10 모두 통과                               | DATE_SURFACE로 render                    |
| calendar-invalid만 실패하고 fallback guard 통과 | `CODE_SEPARATOR_BLOCK_SURFACE` fallback |
| year range 실패                            | preserve                                |
| shape 실패                                 | preserve                                |
| dotted chain                             | preserve                                |
| attached alnum / alphabetic tail         | preserve                                |
| code/model/version/log context           | preserve                                |
| URL/path/email context                   | preserve                                |
| square bracket protected span 내부         | square bracket protection 우선, 내부 무교정    |

### 34A.6 Render

calendar-valid이면 date render 함수를 사용한다.

```text
YYYY.MM.DD -> {year}년 {month}월 {day}일
```

```text
2025.01.03 -> 이천이십오년 일월 삼일
1999.12.31 -> 천구백구십구년 십이월 삼십일일
2000.02.29 -> 이천년 이월 이십구일
2026.10.01 -> 이천이십육년 시월 일일
```

calendar-invalid `YYYY.MM.DD`가 fallback guard를 통과한 경우에는 DATE_SURFACE render를 사용하지 않고, `CODE_SEPARATOR_BLOCK_SURFACE` fallback render를 사용한다.

`.` 구분자는 각 구분자를 `쩜 `으로 렌더링한다.

```text
YYYY.MM.DD calendar-invalid fallback -> {yyyy_digits}쩜 {mm_digits}쩜 {dd_digits}

예:
2025.13.03 -> 이공이오쩜 일삼쩜 공삼
2025.02.30 -> 이공이오쩜 공이쩜 삼공
2025.01.00 -> 이공이오쩜 공일쩜 공공
```

### 34A.7 Canonical / preserve / gate tests

| 입력                   | canonical output       | 핵심 규칙                                      |
| -------------------- | ---------------------- | ------------------------------------------ |
| `2025.01.03`         | `이천이십오년 일월 삼일`         | modern dotted date                         |
| `회의일은 2025.01.03입니다` | `회의일은 이천이십오년 일월 삼일입니다` | date context                               |
| `1999.12.31`         | `천구백구십구년 십이월 삼십일일`     | year range pass                            |
| `2000.02.29`         | `이천년 이월 이십구일`          | leap year pass                             |
| `2024.02.29`         | `이천이십사년 이월 이십구일`       | leap year pass                             |
| `2025.13.01`         | `이공이오쩜 일삼쩜 공일`         | calendar-invalid + code separator fallback |
| `2025.00.01`         | `이공이오쩜 공공쩜 공일`         | calendar-invalid + code separator fallback |
| `2025.01.00`         | `이공이오쩜 공일쩜 공공`         | calendar-invalid + code separator fallback |
| `2025.02.30`         | `이공이오쩜 공이쩜 삼공`         | calendar-invalid + code separator fallback |
| `1899.12.31`         | `1899.12.31`           | year range fail                            |
| `2100.01.01`         | `2100.01.01`           | year range fail                            |
| `버전 2025.01.03`      | `버전 2025.01.03`        | version context preserve                   |
| `[2025.13.01]`       | `2025.13.01`           | square bracket protection                  |

Preserve tests:

```text
1899.12.31 -> preserve
2100.01.01 -> preserve
2025.1.03 -> preserve
2025.01.3 -> preserve
A2025.01.03 -> preserve
2025.01.03B -> preserve
2025.01.03.1 -> preserve
2025.01.03T13:05 -> preserve
version 2025.01.03 -> preserve
ver 2025.01.03 -> preserve
모델 2025.01.03 -> preserve
버전 2025.01.03 -> preserve
로그 2025.01.03 -> preserve
[2025.13.01] -> square bracket protection, output 2025.13.01
```


## 35. Dictionary Expansion Policy

사전 기반 교정은 많이 추가하되, 대부분을 조건부로 둔다. 핵심은 다음이다.

1. 고정 약어는 boundary 기반 사전 처리
2. 단위는 numeric prefix required
3. 통화는 symbol/code + number full consume
4. 공공번호는 context + allowed tail required
5. 사건형 날짜는 immediate event keyword 또는 fixed event surface required
6. 파일 확장자는 file/path context required
7. URL/path/email/code 내부는 preserve
8. 사전 기반 교정 항목은 모두 smoke/collision/shadow test에 포함

### 35.1 LexiconEntry schema

```python
@dataclass
class LexiconEntry:
    surface: str
    reading: str
    entry_type: Literal[
        "fixed_term",
        "acronym",
        "unit",
        "compound_unit",
        "currency_symbol",
        "currency_code",
        "technical_term",
        "file_format",
        "media_type",
        "public_number",
        "event",
        "jamo",
        "symbol",
    ]
    claim_policy: Literal[
        "always_with_boundary",
        "numeric_prefix_required",
        "context_required",
        "protected_only",
        "profile_required",
    ]
    case_sensitive: bool = True
    allow_particle_attach: bool = True
    allow_inside_compound: bool = False
    owner: str | None = None
    domains: set[str] = field(default_factory=set)
    notes: str | None = None
```

### 35.2 Safety classes

| 등급 | 의미 | 예 |
|---|---|---|
| S0 | 조건 없이 boundary만 맞으면 교정 가능 | `AI`, `TTS`, `PDF`, `KOSPI` |
| S1 | 숫자 prefix가 있을 때만 교정 | `kg`, `cm`, `Hz`, `Mbps` |
| S2 | 특정 context가 있을 때만 교정 | `110`, `120`, `1339`, 사건형 날짜 |
| S3 | profile이 있을 때만 교정 | `5G`, `4K`, `REST`, `RAM` 일부 |
| S4 | 기본 preserve 권장 | 단일 문자 `A`, `V`, `m`, `L`, `R`, `C` |

### 35.3 SI / 일반 단위 사전

#### 길이 단위

| 입력 | reading | 조건 |
|---|---|---|
| `mm`, `㎜` | 밀리미터 | numeric prefix required |
| `cm`, `㎝` | 센티미터 | numeric prefix required |
| `m`, `㎙` | 미터 | numeric prefix required, single-letter strict |
| `km`, `㎞` | 킬로미터 | numeric prefix required |
| `µm`, `μm` | 마이크로미터 | numeric prefix required |
| `nm` | 나노미터 | numeric prefix required |
| `pm` | 피코미터 | numeric prefix required |
| `in` | 인치 | numeric prefix required, English word collision guard |
| `ft` | 피트 | numeric prefix required |
| `yd` | 야드 | numeric prefix required |
| `mi` | 마일 | numeric prefix required |

#### 면적 / 부피 단위

| 입력 | reading | 조건 |
|---|---|---|
| `㎡`, `m²`, `m2` | 제곱미터 | numeric prefix required |
| `㎢`, `km²`, `km2` | 제곱킬로미터 | numeric prefix required |
| `㎠`, `cm²`, `cm2` | 제곱센티미터 | numeric prefix required |
| `㎥`, `m³`, `m3` | 세제곱미터 | numeric prefix required |
| `㎤`, `cm³`, `cm3` | 세제곱센티미터 | numeric prefix required |
| `cc` | 씨씨 | numeric prefix required |
| `L`, `ℓ`, `l` | 리터 | numeric prefix required, single-letter strict |
| `mL`, `ml`, `ML`, `㎖` | 밀리리터 | numeric prefix required |
| `dL` | 데시리터 | numeric prefix required |

#### 질량 / 무게 단위

| 입력 | reading | 조건 |
|---|---|---|
| `mg`, `㎎` | 밀리그램 | numeric prefix required |
| `g` | 그램 | numeric prefix required |
| `kg`, `㎏` | 킬로그램 | numeric prefix required |
| `t` | 톤 | numeric prefix required, single-letter strict |
| `ton` | 톤 | numeric prefix required |
| `oz` | 온스 | numeric prefix required |
| `lb`, `lbs` | 파운드 | numeric prefix required |

#### 시간 단위

| 입력 | reading | 조건 |
|---|---|---|
| `ms` | 밀리초 | numeric prefix required |
| `s`, `sec` | 초 | numeric prefix required, `s` strict |
| `min` | 분 | numeric prefix required |
| `h`, `hr`, `hrs` | 시간 | numeric prefix required, `h` strict |
| `d`, `day` | 일 | numeric prefix required, `d` strict |
| `wk` | 주 | numeric prefix required |
| `mo` | 개월 | numeric prefix required |
| `yr` | 년 | numeric prefix required |

#### 전기 / 전자 / 에너지 단위

| 입력 | reading | 조건 |
|---|---|---|
| `V`, `mV`, `kV` | 볼트 / 밀리볼트 / 킬로볼트 | numeric prefix required |
| `A`, `mA` | 암페어 / 밀리암페어 | numeric prefix required |
| `W`, `kW`, `MW`, `GW` | 와트 / 킬로와트 / 메가와트 / 기가와트 | numeric prefix required |
| `Wh`, `kWh`, `MWh` | 와트시 / 킬로와트시 / 메가와트시 | numeric prefix required |
| `J`, `kJ` | 줄 / 킬로줄 | numeric prefix required |
| `cal`, `kcal` | 칼로리 / 킬로칼로리 | numeric prefix required |
| `Ω`, `ohm`, `mΩ`, `kΩ` | 옴 / 옴 / 밀리옴 / 킬로옴 | numeric prefix required |
| `F`, `µF`, `nF`, `pF` | 패럿 / 마이크로패럿 / 나노패럿 / 피코패럿 | numeric prefix required |

#### 주파수 / 음향 / 신호 단위

| 입력 | reading | 조건 |
|---|---|---|
| `Hz`, `hz`, `㎐` | 헤르츠 | numeric prefix required |
| `kHz`, `MHz`, `GHz`, `THz` | 킬로헤르츠 / 메가헤르츠 / 기가헤르츠 / 테라헤르츠 | numeric prefix required |
| `dB`, `㏈` | 데시벨 | numeric prefix required |
| `dBm` | 디비엠 | numeric prefix required |
| `dBi` | 디비아이 | numeric prefix required |
| `ppm` | 피피엠 | numeric prefix required |
| `ppb` | 피피비 | numeric prefix required |
| `ppt` | 피피티 | numeric prefix required, file format collision guard |

#### 온도 / 각도 / 비율 기호

| 입력 | reading | 조건 |
|---|---|---|
| `℃`, `°C` | 도 | signed temperature owner |
| `℉`, `°F` | 화씨 | signed temperature owner |
| `K` | 켈빈 | numeric prefix required, single-letter strict |
| `°` | 도 | signed degree / numeric prefix required |
| `%`, `％` | 퍼센트 | numeric prefix required |
| `‰` | 퍼밀 | numeric prefix required |
| `‱` | 만분율 | profile required |

### 35.4 Slash compound unit dictionary

기본 원칙은 “뒷단위당 앞단위”이지만, 자연스러운 고정 표현이 있으면 `시속`, `분속`, `초속`을 우선한다.

#### 속도 / 이동

| 입력 | reading template | 조건 |
|---|---|---|
| `km/h`, `㎞/h`, `km/hr` | 시속 {n} 킬로미터 | numeric prefix required |
| `m/s`, `m/sec` | 초속 {n} 미터 | numeric prefix required |
| `km/s` | 초속 {n} 킬로미터 | numeric prefix required |
| `m/min` | 분속 {n} 미터 | numeric prefix required |
| `ft/s` | 초속 {n} 피트 | numeric prefix required |
| `mph` | 시속 {n} 마일 | numeric prefix required |
| `knot`, `kn` | {n} 노트 | numeric prefix required, `kn` strict |

#### 연비 / 효율

| 입력 | reading template | 조건 |
|---|---|---|
| `km/L`, `km/l`, `km/ℓ`, `㎞/L`, `㎞/l`, `㎞/ℓ` | 리터당 {n} 킬로미터 | numeric prefix required |
| `m/L`, `m/l`, `m/ℓ` | 리터당 {n} 미터 | numeric prefix required |
| `mpg` | 갤런당 {n} 마일 | numeric prefix required |

#### Phase 36A compound unit expansion

Phase 36A는 compound unit owner 내부에서만 다음 surface를 추가한다. 전역 Unicode normalization 또는 전역 string replace alias는 금지하며, slash alias `／`는 compound unit owner-local matcher에서만 처리한다.

- `number + m/min`, `number + m／min`은 `분속 {n} 미터`로 읽는다.
- `number + m/L`, `number + m/l`, `number + m／L`, `number + m／l`은 `리터당 {n} 미터`로 읽는다.
- 숫자는 양수 정수, 소수, comma-valid number를 허용하되 compound unit owner의 기존 numeric parser 지원 범위를 따른다.
- 숫자 없는 단독 unit 문자열은 변환하지 않는다: `m/min`, `m/L`, `km/L`, `km/s` preserve.
- unsafe tail은 preserve한다: `8.5m/minute`, `250m/Lite`, `250m/lab`, `3km/speed` preserve.
- 기존 compound unit은 유지한다: `90km/h`, `15.2km/L`, `3km/s`, `5cm/s`.

#### Phase 36B valid comma number and one-space number-unit policy

Phase 36B는 명시 owner가 소유한 숫자+단위 surface에 한해 valid thousands comma number와 숫자-단위 사이 ASCII space 한 칸을 허용한다. 전역 Unicode normalization, 전역 string replace, arbitrary unknown unit 확장은 금지한다.

숫자 블록:

- 정수: `1250`
- 소수: `12.5`
- valid thousands comma: `1,250`, `12,345`, `1,234,567`
- comma + decimal: `1,234.56`
- invalid comma는 preserve한다: `1,25m`, `12,34kg`, `1,23,456원`, `1,,000m`, `1,000,km/h`

숫자와 단위 사이 spacing:

- 공백 없음 또는 ASCII space 한 칸만 동일하게 허용한다.
- `1,250m` == `1,250 m`
- `25℃` == `25 ℃`
- `8.5m/min` == `8.5 m/min`
- `250m/L` == `250 m/L`
- `1,000KB/s` == `1,000 KB/s`
- 여러 칸, 탭, 줄바꿈은 Phase 36B에서 허용하지 않는다.
- slash 주변 공백은 Phase 36B에서 허용하지 않는다: `8.5 m/min`은 허용하지만 `8.5 m / min`은 미지원/preserve.

Boundary:

- 숫자 앞이 문자열 시작, 공백, 문장부호, 여는 괄호, 한글 문맥이면 허용한다.
- 숫자 앞이 ASCII letter/digit 또는 식별자 성격 문자이면 변환하지 않는다: `abc1,250m`, `A1,250 m`, `model25 ℃` preserve.
- 단위 뒤가 문자열 끝, 공백, 문장부호, 닫는 괄호, 한글 조사/어미이면 허용한다: `1,250m까지`, `25 ℃입니다`, `8.5 m/min으로`.
- 단위 뒤가 ASCII letter/digit이면 preserve한다: `1,250mtest`, `25 ℃abc`, `8.5 m/minute`, `250 m/Lite`.

적용 owner:

- currency: `1,330원`, `1,330 원`, `₩1,330`, `₩ 1,330`, `$1,234.56`, `$ 1,234.56`, `€1,234`, `€ 1,234`, `￥1,500`
- counter: `1,200건`, `1,200 건`, `8,500명`, `8,500 명`, `1,200점`, `1,200 점`
- simple physical/data/frequency unit: `1,250m`, `1,250 m`, `1,250km`, `1,250 km`, `1,250cm`, `1,250 cm`, `1,200kg`, `1,200 kg`, `1,200g`, `1,200 g`, `1,000MB`, `1,000 MB`, `1,000GB`, `1,000 GB`, `1,000PB`, `1,000 PB`, `1,000Hz`, `1,000 Hz`, `1,000MHz`, `1,000 MHz`, `1,000GHz`, `1,000 GHz`
- temperature: `25℃`, `25 ℃`, `-2.5℃`, `-2.5 ℃`, `+3℃`, `+3 ℃`, `25℉`, `25 ℉`, `-2.5℉`, `-2.5 ℉`
- compound slash unit: `1,000km/h`, `1,000 km/h`, `1,000m/s`, `1,000 m/s`, `1,000cm/s`, `1,000 cm/s`, `1,000m/min`, `1,000 m/min`, `1,000km/L`, `1,000 km/L`, `1,000m/L`, `1,000 m/L`, `1,000KB/s`, `1,000 KB/s`

Non-goals:

- slash 주변 공백 허용
- arbitrary unknown unit 처리
- code/path/url/email 내부 변환
- irregular comma 변환
- NFD normalization 확장

#### Data-rate decimal / one-space full-consume completion

Data-rate completion은 data-rate compound owner가 `KB/s`, `MB/s`, `GB/s`, `TB/s`, `PB/s`를 명시 allowlist로 소유하도록 보강한다. 이 처리는 compound/data unit owner 내부에 한정하며 전역 문자열 replace, 전역 Unicode normalization, unknown unit 확장은 금지한다.

지원 data-rate reading:

- `N KB/s` -> `초당 N 킬로바이트`
- `N MB/s` -> `초당 N 메가바이트`
- `N GB/s` -> `초당 N 기가바이트`
- `N TB/s` -> `초당 N 테라바이트`
- `N PB/s` -> `초당 N 페타바이트`

숫자 형식:

- 정수 허용: `1000KB/s`
- 소수 허용: `12.5MB/s`
- valid comma 허용: `1,000KB/s`
- comma + decimal이 필요한 경우 기존 numeric parser의 valid thousands comma 정책을 따른다: `1,234.5MB/s`
- invalid comma는 preserve한다: `1,00KB/s`, `1,23,456MB/s`, `1,,000GB/s`

숫자와 data-rate unit 사이 spacing:

- 공백 없음 또는 ASCII space 한 칸만 허용한다: `12.5MB/s`, `12.5 MB/s`, `1,000KB/s`, `1,000 KB/s`
- 여러 칸, 탭, 줄바꿈은 현재 정책 대상이 아니며 preserve한다.
- slash 주변 공백은 현재 정책 대상이 아니며 preserve한다: `1,000 KB / s`, `12.5 MB / s`

Full-consume / partial rewrite:

- `12.5 MB/s`는 전체 surface가 `초당 십이쩜오 메가바이트`로 full consume되어야 한다.
- `12.5 MB/s`가 `십이쩜오 MB/s`처럼 숫자만 변환되는 partial rewrite는 금지한다.
- data-rate owner가 전체 surface를 claim하지 못하면 unsafe preserve guard가 숫자-only fallback을 막아야 한다.

Boundary / unsafe tail:

- 숫자 앞이 ASCII letter/digit 또는 identifier-like이면 preserve한다: `abc12.5MB/s`
- 단위 뒤가 ASCII letter/digit이면 preserve한다: `1,000KB/speed`, `12.5MB/sec`, `12.5MB/second`
- 단독 unit은 preserve한다: `KB/s`, `MB/s`, `GB/s`
- `B/s`, lowercase `kb/s`, `mb/s`, `gb/s`, `Mbps`, `Gbps` 등 bit/byte 정책이 다른 surface는 현재 정책 대상이 아니다.


#### Numeric, suffix, and date-range policy corrections

장문 예문 smoke에서 확정된 numeric, suffix, date-range 정책 보강 사항은 관련 owner 본문에 통합한다. 이 정책은 comma/one-space 원칙을 유지하면서 명시 owner가 소유하는 대상을 정리한다.

적용 항목:

1. decimal simple unit / Korean suffix full consume
   - `1.2km -> 일쩜이 킬로미터`
   - `0.8초 -> 영쩜팔초`
   - `2,645.35선 -> 이천육백사십오쩜삼오선`
   - `제15권 -> 제 십오권`
2. Arabic `6월` and `10월` date rendering special case
   - `6월 -> 유월`
   - `10월 -> 시월`
   - 한글 `유월`, `십월`은 보존
3. date/time shared suffix range expansion
   - `1~11월 -> 일월에서 십일월`
   - `2~5시 -> 이시에서 오시`
4. Korean page/document tilde range
   - `5~7쪽 -> 오에서 칠쪽`
   - approved hyphen form `12-15장 -> 십이에서 십오 장`
5. large-unit numeric surface coverage
   - `3.5만 원 -> 삼쩜오 만 원`
   - `1.2억 원 -> 일쩜이 억 원`
6. spaced hyphen numeric multi-block
   - `010 - 1234 - 5678 -> 공일공 천이백삼십사 오천육백칠십팔`
7. frequency case aliases
   - `Hz/hz`, `kHz/khz`, `MHz/mhz`, `GHz/Ghz/ghz`는 numeric prefix가 있을 때 같은 family로 처리한다.
8. bitrate / byte-rate 표기 분리
   - `1Gbps -> 일 기가비피에스`를 유지한다.
   - slash throughput 표기 `1Gb/s`는 프로젝트 정책상 `초당 일 기가바이트`로 읽는다.

유지되는 non-goals:

- bare `-1.3도 -> 영하 일쩜삼도` 일반화는 하지 않는다.
- time-like/protected/invalid가 아닌 standalone `숫자:숫자`는 broad N:M 정책에 따라 `N 대 M`으로 읽는다.
- approved semantic-pair keyword 문맥은 `N:M`의 유효한 positive context이지만 유일한 claim 조건은 아니다.
- 임의 hyphen range는 range owner canonical 대상이 아니다. Approved `N-M + range-compatible unit`만 별도 정책을 따른다.
- slash 주변 공백은 여전히 미지원/preserve한다: `1,000 KB / s` preserve.

#### Compact `N대M` relation fallback

`N대M`처럼 공백 없이 `대`로 연결된 compact relation은 score/ratio owner를 새로 만들지 않고 일반 number fallback으로 양쪽 숫자 core를 각각 읽는다. `대`와 뒤 조사/어미는 원문 한글 literal로 유지한다. 이 규칙은 hyphen score/range(`1-1`, `1-2`)로 확장하지 않는다. Colon-like `N:M`은 최신 broad N:M 정책에 따라 time-like/protected/invalid guard 이후 `N 대 M`으로 읽을 수 있다.

```text
1대1로 -> 일대일로
1대1 교육 -> 일대일 교육
2대1 구조 -> 이대일 구조
10대1 경쟁률 -> 십대일 경쟁률
3:2 승 -> 삼 대 이 승
3:2 세트 -> 삼 대 이 세트
1-1 무 -> 1-1 무
```

ASCII/Hangul identifier에 붙은 `N대M` 또는 unsafe alphabetic tail은 partial rewrite하지 않고 preserve한다.

#### Preserve taxonomy / owner fallback clarification

`preserve` 용어는 `Absolute Preserve`, `Owner Fallback Candidate`, `Terminal Fallback Preserve`로 분리한다. 이 구분은 owner 평가 순서에 직접 영향을 준다.

- Absolute Preserve는 owner 재진입을 금지한다.
- Owner Fallback Candidate는 다음 후보 owner 평가를 허용한다.
- Terminal Fallback Preserve는 모든 후보 owner가 실패한 뒤 최종적으로 원문 출력한다.

대표 변경:

```text
13.3 비상계엄 -> event 실패 -> decimal fallback -> 십삼쩜삼 비상계엄
12·3수치 -> event 실패 -> middle-dot fallback -> 십이 삼수치
2025-13-03 -> date 실패 -> guarded code separator fallback -> 이공이오 일삼 공삼
제15권 -> numeric suffix owner -> 제 십오권
010 - 1234 - 5678 -> spaced hyphen numeric multi-block -> 공일공 천이백삼십사 오천육백칠십팔
```

금지:

```text
URL/path/code 내부 숫자를 다음 owner로 재진입
unsafe tail surface 일부만 변환
full consume 실패 후 raw residue 유지
```

#### 데이터 전송 / 처리량

| 입력 | reading template | 조건 |
|---|---|---|
| `bps` | {n} 비피에스 | numeric prefix required, lexicalized |
| `Kbps`, `kbps` | {n} 킬로비피에스 | numeric prefix required, lexicalized |
| `Mbps`, `mbps` | {n} 메가비피에스 | numeric prefix required, lexicalized |
| `Gbps`, `gbps` | {n} 기가비피에스 | numeric prefix required, lexicalized |
| `Tbps`, `tbps` | {n} 테라비피에스 | numeric prefix required, lexicalized |
| `B/s` | 초당 {n} 바이트 | numeric prefix required, slash throughput |
| `KB/s`, `Kb/s`, `kb/s` | 초당 {n} 킬로바이트 | numeric prefix required, slash throughput project reading |
| `MB/s`, `Mb/s`, `mb/s` | 초당 {n} 메가바이트 | numeric prefix required, slash throughput project reading |
| `GB/s`, `Gb/s`, `gb/s` | 초당 {n} 기가바이트 | numeric prefix required, slash throughput project reading |
| `TB/s`, `Tb/s`, `tb/s` | 초당 {n} 테라바이트 | numeric prefix required, slash throughput project reading |
| `PB/s`, `Pb/s`, `pb/s` | 초당 {n} 페타바이트 | numeric prefix required, slash throughput project reading |

#### 의학 / 과학 농도

| 입력 | reading template | 조건 |
|---|---|---|
| `mg/dL` | 데시리터당 {n} 밀리그램 | numeric prefix required |
| `g/dL` | 데시리터당 {n} 그램 | numeric prefix required |
| `mmol/L` | 리터당 {n} 밀리몰 | numeric prefix required |
| `mol/L` | 리터당 {n} 몰 | numeric prefix required |
| `IU/L` | 리터당 {n} 아이유 | numeric prefix required |
| `U/L` | 리터당 {n} 유닛 | numeric prefix required |
| `ng/mL` | 밀리리터당 {n} 나노그램 | numeric prefix required |
| `pg/mL` | 밀리리터당 {n} 피코그램 | numeric prefix required |
| `µg/mL`, `μg/mL` | 밀리리터당 {n} 마이크로그램 | numeric prefix required |
| `cells/µL` | 마이크로리터당 {n} 셀 | numeric prefix required |
| `copies/mL` | 밀리리터당 {n} 카피 | numeric prefix required |

### 35.5 File size / data unit dictionary

#### 십진 / 일반 파일 크기

| 입력 | reading | 조건 |
|---|---|---|
| `bit`, `bits` | 비트 | numeric prefix required |
| `b` | 비트 | numeric prefix required, strict |
| `B` | 바이트 | numeric prefix required, strict |
| `Byte`, `Bytes` | 바이트 | numeric prefix required |
| `KB`, `MB`, `GB`, `TB`, `PB`, `EB`, `ZB`, `YB` | 킬로바이트 / 메가바이트 / 기가바이트 / 테라바이트 / 페타바이트 / 엑사바이트 / 제타바이트 / 요타바이트 | numeric prefix required |

#### 이진 접두어

| 입력 | reading | 조건 |
|---|---|---|
| `KiB` | 키비바이트 | numeric prefix required |
| `MiB` | 메비바이트 | numeric prefix required |
| `GiB` | 기비바이트 | numeric prefix required |
| `TiB` | 테비바이트 | numeric prefix required |
| `PiB` | 페비바이트 | numeric prefix required |
| `EiB` | 엑스비바이트 | numeric prefix required |
| `ZiB` | 제비바이트 | numeric prefix required |
| `YiB` | 요비바이트 | numeric prefix required |

### 35.6 Currency dictionary

#### 통화 기호

| 입력 | reading | 조건 |
|---|---|---|
| `$`, `US$` | 달러 | numeric required |
| `€` | 유로 | numeric required |
| `₩`, `￦` | 원 | numeric required |
| `¥`, `￥` | 엔 | numeric required |
| `£` | 파운드 | numeric required |
| `₽` | 루블 | numeric required |
| `₹` | 루피 | numeric required |
| `₫` | 동 | numeric required |
| `₭` | 킵 | numeric required |
| `₱` | 페소 | numeric required |
| `₪` | 셰켈 | numeric required |
| `₺` | 리라 | numeric required |
| `₴` | 흐리우냐 | numeric required |
| `₦` | 나이라 | numeric required |
| `₡` | 콜론 | numeric required |
| `₲` | 과라니 | numeric required |
| `₵` | 세디 | numeric required |
| `₸` | 텡게 | numeric required |
| `₼` | 마나트 | numeric required |
| `฿` | 바트 | numeric required |
| `₿` | 비트코인 | numeric required, crypto profile |

#### 주요 ISO 통화 코드

| 입력 | reading | 조건 |
|---|---|---|
| `USD` | 달러 | numeric required |
| `KRW` | 원 | numeric required |
| `EUR` | 유로 | numeric required |
| `JPY` | 엔 | numeric required |
| `GBP` | 파운드 | numeric required |
| `CNY`, `RMB` | 위안 | numeric required |
| `HKD` | 홍콩 달러 | numeric required |
| `TWD` | 대만 달러 | numeric required |
| `SGD` | 싱가포르 달러 | numeric required |
| `AUD` | 호주 달러 | numeric required |
| `CAD` | 캐나다 달러 | numeric required |
| `NZD` | 뉴질랜드 달러 | numeric required |
| `CHF` | 스위스 프랑 | numeric required |
| `SEK` | 스웨덴 크로나 | numeric required |
| `NOK` | 노르웨이 크로네 | numeric required |
| `DKK` | 덴마크 크로네 | numeric required |
| `RUB` | 루블 | numeric required |
| `INR` | 루피 | numeric required |
| `THB` | 바트 | numeric required |
| `VND` | 동 | numeric required |
| `IDR` | 루피아 | numeric required |
| `MYR` | 링깃 | numeric required |
| `PHP` | 페소 | numeric required |
| `BRL` | 헤알 | numeric required |
| `MXN` | 멕시코 페소 | numeric required |
| `ZAR` | 랜드 | numeric required |
| `TRY` | 리라 | numeric required |
| `AED` | 디르함 | numeric required |
| `SAR` | 리얄 | numeric required |

`CAD`, `AUD`, `SGD` 등은 단독 acronym fallback으로 읽지 말고 currency context 또는 numeric required 조건을 둔다.

### 35.7 Technical / IT dictionary

#### 개발 / 웹

| 입력 | reading | 조건 |
|---|---|---|
| `API` | 에이피아이 | always with boundary |
| `SDK` | 에스디케이 | always with boundary |
| `CLI` | 씨엘아이 | always with boundary |
| `GUI` | 지유아이 | always with boundary |
| `UI` | 유아이 | always with boundary |
| `UX` | 유엑스 | always with boundary |
| `HTML` | 에이치티엠엘 | always with boundary |
| `CSS` | 씨에스에스 | always with boundary |
| `JS` | 제이에스 | always with boundary |
| `JSON` | 제이슨 | always with boundary |
| `XML` | 엑스엠엘 | always with boundary |
| `YAML` | 야믈 | always with boundary |
| `CSV` | 씨에스브이 | always with boundary |
| `SQL` | 에스큐엘 | always with boundary |
| `NoSQL` | 노에스큐엘 | exact dictionary |
| `HTTP` | 에이치티티피 | always with boundary |
| `HTTPS` | 에이치티티피에스 | always with boundary |
| `URL` | 유알엘 | always with boundary |
| `URI` | 유알아이 | always with boundary |
| `DNS` | 디엔에스 | always with boundary |
| `IP` | 아이피 | context or boundary |
| `TCP` | 티씨피 | always with boundary |
| `UDP` | 유디피 | always with boundary |
| `TLS` | 티엘에스 | always with boundary |
| `SSL` | 에스에스엘 | always with boundary |
| `SSH` | 에스에스에이치 | always with boundary |
| `FTP` | 에프티피 | always with boundary |
| `SFTP` | 에스에프티피 | always with boundary |
| `SMTP` | 에스엠티피 | always with boundary |
| `REST` | 레스트 | technical context recommended |
| `GraphQL` | 그래프큐엘 | exact dictionary |
| `gRPC` | 지알피씨 | exact dictionary |
| `OAuth` | 오어스 | exact dictionary |
| `JWT` | 제이더블유티 | always with boundary |

#### AI / 음성 / 언어처리

| 입력 | reading | 조건 |
|---|---|---|
| `AI` | 에이아이 | always with boundary |
| `AGI` | 에이지아이 | always with boundary |
| `LLM` | 엘엘엠 | always with boundary |
| `ML` | 엠엘 | technical context recommended |
| `DL` | 디엘 | technical context recommended |
| `NLP` | 엔엘피 | always with boundary |
| `NLU` | 엔엘유 | always with boundary |
| `NLG` | 엔엘지 | always with boundary |
| `TTS` | 티티에스 | always with boundary |
| `STT` | 에스티티 | always with boundary |
| `ASR` | 에이에스알 | always with boundary |
| `OCR` | 오씨알 | always with boundary |
| `RAG` | 래그 | AI context recommended |
| `GPT` | 지피티 | always with boundary |
| `BERT` | 버트 | AI context recommended |
| `CNN` | 씨엔엔 | AI/media ambiguity, context recommended |
| `RNN` | 알엔엔 | AI context recommended |
| `GPU` | 지피유 | always with boundary |
| `TPU` | 티피유 | technical context recommended |
| `NPU` | 엔피유 | technical context recommended |

#### 하드웨어 / 네트워크

| 입력 | reading | 조건 |
|---|---|---|
| `CPU` | 씨피유 | always with boundary |
| `GPU` | 지피유 | always with boundary |
| `RAM` | 램 | hardware context recommended |
| `ROM` | 롬 | hardware context recommended |
| `SSD` | 에스에스디 | always with boundary |
| `HDD` | 에이치디디 | always with boundary |
| `USB` | 유에스비 | always with boundary |
| `HDMI` | 에이치디엠아이 | always with boundary |
| `PCIe` | 피씨아이이 | exact dictionary |
| `LAN` | 랜 | network context recommended |
| `WAN` | 왠 | network context recommended |
| `Wi-Fi`, `WIFI` | 와이파이 | exact dictionary |
| `LTE` | 엘티이 | always with boundary |
| `5G` | 파이브지 | technical context/profile |
| `4G` | 포지 | technical context/profile |
| `3G` | 쓰리지 | technical context/profile |
| `NFC` | 엔에프씨 | always with boundary |
| `RFID` | 알에프아이디 | always with boundary |
| `QR` | 큐알 | context recommended |
| `SIM` | 심 | telecom context recommended |
| `USIM` | 유심 | telecom context recommended |

### 35.8 File format / extension dictionary

| 입력 | reading | 조건 |
|---|---|---|
| `PDF`, `.pdf` | 피디에프 | boundary or file/path context |
| `DOC` | 디오씨 | file context |
| `DOCX` | 닥스 | file context |
| `XLS` | 엑스엘에스 | file context |
| `XLSX` | 엑스엘에스엑스 | file context |
| `PPT` | 피피티 | file context |
| `PPTX` | 피피티엑스 | file context |
| `TXT` | 티엑스티 | file context |
| `MD` | 엠디 | file context |
| `RTF` | 알티에프 | file context |
| `HWP` | 에이치더블유피 | Korean doc context |
| `JPG` | 제이피지 | file context |
| `JPEG` | 제이펙 | file context |
| `PNG` | 피엔지 | file context |
| `GIF` | 지프 | file context |
| `WEBP` | 웹피 | file context |
| `SVG` | 에스브이지 | file context |
| `MP3` | 엠피쓰리 | file/media context |
| `MP4` | 엠피포 | file/media context |
| `AVI` | 에이브이아이 | file/media context |
| `MOV` | 엠오브이 | file/media context |
| `MKV` | 엠케이브이 | file/media context |
| `WAV` | 웨이브 | file/media context |
| `FLAC` | 플랙 | file/media context |
| `ZIP` | 집 | file context |
| `RAR` | 라 | file context |
| `7z` | 세븐집 | file context |
| `TAR` | 타르 | file context |
| `GZ` | 지지 | file context |
| `EXE` | 이엑스이 | file context |
| `APK` | 에이피케이 | file context |
| `IPA` | 아이피에이 | file context |
| `DMG` | 디엠지 | file context |
| `ISO` | 아이에스오 | file or standard context |

`MD`, `MOV`, `ISO`, `ZIP`은 일반 단어/약어와 충돌 가능하므로 확장자 점 또는 file context를 우선한다.

### 35.9 Media / broadcast dictionary

| 입력 | reading | 조건 |
|---|---|---|
| `HD` | 에이치디 | media context |
| `FHD` | 에프에이치디 | media context |
| `QHD` | 큐에이치디 | media context |
| `UHD` | 유에이치디 | media context |
| `4K` | 포케이 | media/display context |
| `8K` | 에이트케이 | media/display context |
| `HDR` | 에이치디알 | media context |
| `SDR` | 에스디알 | media context |
| `FPS`, `fps` | 에프피에스 | numeric prefix or media/game context |
| `VOD` | 브이오디 | media context |
| `OTT` | 오티티 | media context |
| `IPTV` | 아이피티비 | media context |
| `EPG` | 이피지 | broadcast context |
| `DMB` | 디엠비 | broadcast context |
| `FM` | 에프엠 | broadcast context |
| `AM` | 에이엠 | broadcast/time ambiguity, context |
| `TV` | 티비 | boundary/context |
| `MC` | 엠씨 | media context |
| `BGM` | 비지엠 | media context |
| `OST` | 오에스티 | media context |
| `CG` | 씨지 | media context |
| `VFX` | 브이에프엑스 | media context |
| `SFX` | 에스에프엑스 | media context |
| `K-POP` | 케이팝 | always with boundary |
| `K-푸드` | 케이푸드 | K-Hangul lexical prefix |
| `K-뷰티` | 케이뷰티 | K-Hangul lexical prefix |

### 35.10 Finance / economy / news dictionary

| 입력 | reading | 조건 |
|---|---|---|
| `KOSPI` | 코스피 | always with boundary |
| `KOSDAQ` | 코스닥 | always with boundary |
| `NASDAQ` | 나스닥 | finance context |
| `S&P` | 에스앤피 | finance context |
| `DOW` | 다우 | finance context |
| `GDP` | 지디피 | finance/economy context |
| `GNP` | 지엔피 | finance/economy context |
| `CPI` | 씨피아이 | finance/economy context |
| `PPI` | 피피아이 | finance/economy context |
| `PMI` | 피엠아이 | finance/economy context |
| `FOMC` | 에프오엠씨 | finance/economy context |
| `Fed` | 연준 | profile/context |
| `ECB` | 이씨비 | finance context |
| `BOJ` | 비오제이 | finance context |
| `BOK` | 비오케이 | Korean finance context |
| `IMF` | 아이엠에프 | finance/institution context |
| `WTO` | 더블유티오 | institution context |
| `OECD` | 오이시디 | institution context |
| `WHO` | 더블유에이치오 | institution context |
| `UN` | 유엔 | institution context |
| `EU` | 이유 | institution context |
| `ETF` | 이티에프 | finance context |
| `ETN` | 이티엔 | finance context |
| `IPO` | 아이피오 | finance context |
| `ROE` | 알오이 | finance context |
| `PER` | 피이알 | finance context |
| `PBR` | 피비알 | finance context |
| `EPS` | 이피에스 | finance context |
| `BPS` | 비피에스 | finance context |
| `YoY` | 와이오와이 | finance context |
| `MoM` | 엠오엠 | finance context |
| `QoQ` | 큐오큐 | finance context |

`PER`, `BPS`, `EPS`는 단위/기술 약어와 충돌할 수 있으므로 finance context가 필요하다.

### 35.11 Institution / country / sports dictionary

| 입력 | reading | 조건 |
|---|---|---|
| `KR` | 케이알 | country/code context |
| `KOR` | 코리아 / 케이오알 | profile |
| `US` | 미국 / 유에스 | context/profile |
| `USA` | 유에스에이 | context |
| `UK` | 영국 / 유케이 | context/profile |
| `JP` | 제이피 | country/code context |
| `JPN` | 재팬 / 제이피엔 | profile |
| `CN` | 씨엔 | country/code context |
| `CHN` | 차이나 / 씨에이치엔 | profile |
| `ASEAN` | 아세안 | institution context |
| `NATO` | 나토 | institution context |
| `OPEC` | 오펙 | institution context |
| `IAEA` | 아이에이이에이 | institution context |
| `IOC` | 아이오씨 | sports/institution context |
| `FIFA` | 피파 | sports context |
| `AFC` | 에이에프씨 | sports context |
| `KBO` | 케이비오 | sports context |
| `KBL` | 케이비엘 | sports context |
| `KFA` | 케이에프에이 | sports context |

### 35.12 Public number dictionary

Public number는 emergency owner의 하위 subtype으로 구현한다.

| 입력 | reading | 조건 |
|---|---|---|
| `112` | 일일이 | emergency context + allowed tail |
| `119` | 일일구 | emergency context + allowed tail |
| `110` | 일일공 | 국민콜/민원/정부민원 context |
| `120` | 일이공 | 다산콜/지자체/콜센터 context |
| `117` | 일일칠 | 학교폭력/신고 context |
| `118` | 일일팔 | 사이버/인터넷/상담 context |
| `1339` | 일삼삼구 | 질병/응급/상담/감염병 context |
| `182` | 일팔이 | 경찰민원 context |
| `125` | 일이오 | 밀수/관세/신고 context |
| `129` | 일이구 | 보건복지/상담 context |
| `1388` | 일삼팔팔 | 청소년/상담 context |
| `1399` | 일삼구구 | 식품/안전/신고 context |

공통 규칙:

```text
context 없으면 public number reading 금지
gate fail이면 general number fallback
alphabetic contamination이면 preserve
```

예:

```text
국민콜 110에 문의 -> 국민콜 일일공에 문의
110명 참석 -> 백십명 참석
질병 상담 1339에 문의 -> 질병 상담 일삼삼구에 문의
1339에 문의 -> 천삼백삼십구에 문의
```

### 35.13 Event dictionary

| surface | reading | keyword context |
|---|---|---|
| `12.12` | `십이십이` | `사태`, `군사반란` |
| `5.18` | `오일팔` | `민주화운동`, `광주`, `항쟁` |
| `4.19` | `사일구` | `혁명` |
| `6.25` | `육이오` | `전쟁`, `사변` |
| `8.15` | `팔일오` | `광복절`, `해방` |
| `12.3` | `십이삼` | `비상계엄`, `계엄` |
| `12·3` | `십이삼` | `비상계엄`, `계엄` |
| `6.27` | `육이칠` | `부동산대책`, `대책` |

주의:

```text
bare 12.12 -> preserve
bare 5·18 -> 오 일팔  # Phase 28G-B: middle-dot numeric block fallback
```

### 35.14 Jamo dictionary

완성형 한글은 보존 대상이지만, compatibility jamo 단독 입력은 `JAMO_SURFACE`로 읽을 수 있다.

#### 자음

| 입력 | reading |
|---|---|
| `ㄱ` | 기역 |
| `ㄲ` | 쌍기역 |
| `ㄴ` | 니은 |
| `ㄷ` | 디귿 |
| `ㄸ` | 쌍디귿 |
| `ㄹ` | 리을 |
| `ㅁ` | 미음 |
| `ㅂ` | 비읍 |
| `ㅃ` | 쌍비읍 |
| `ㅅ` | 시옷 |
| `ㅆ` | 쌍시옷 |
| `ㅇ` | 이응 |
| `ㅈ` | 지읒 |
| `ㅉ` | 쌍지읒 |
| `ㅊ` | 치읓 |
| `ㅋ` | 키읔 |
| `ㅌ` | 티읕 |
| `ㅍ` | 피읖 |
| `ㅎ` | 히읗 |

#### 모음

| 입력 | reading |
|---|---|
| `ㅏ` | 아 |
| `ㅐ` | 애 |
| `ㅑ` | 야 |
| `ㅒ` | 얘 |
| `ㅓ` | 어 |
| `ㅔ` | 에 |
| `ㅕ` | 여 |
| `ㅖ` | 예 |
| `ㅗ` | 오 |
| `ㅘ` | 와 |
| `ㅙ` | 왜 |
| `ㅚ` | 외 |
| `ㅛ` | 요 |
| `ㅜ` | 우 |
| `ㅝ` | 워 |
| `ㅞ` | 웨 |
| `ㅟ` | 위 |
| `ㅠ` | 유 |
| `ㅡ` | 으 |
| `ㅢ` | 의 |
| `ㅣ` | 이 |

조건:

```text
단독 compatibility jamo 또는 연속 compatibility jamo만 JAMO_SURFACE claim
완성형 한글 내부는 절대 변환하지 않음
mixed token 내부 자모는 preserve
```

### 35.15 Math / symbol dictionary

기호는 문맥에 따라 읽기가 달라지므로 대부분 symbol owner + context/profile로 둔다.

| 입력 | reading | 조건 |
|---|---|---|
| `+` | 플러스 | numeric/math context |
| `−`, `-` | 마이너스 | numeric/math context, hyphen과 구분 |
| `×` | 곱하기 | math context |
| `x` | 곱하기 | math context only |
| `÷` | 나누기 | math context |
| `=` | 는 / 이콜 | math/profile |
| `≠` | 같지 않음 | math context |
| `≈` | 약 | math context |
| `<` | 미만 | math context |
| `>` | 초과 | math context |
| `≤` | 이하 | math context |
| `≥` | 이상 | math context |
| `±` | 플러스마이너스 | numeric context |
| `√` | 루트 | math context |
| `π` | 파이 | math context |
| `∞` | 무한대 | math context |
| `∑` | 시그마 | math context |
| `∫` | 인테그랄 | math context |
| `→` | 화살표 | diagram/profile |
| `←` | 왼쪽 화살표 | diagram/profile |
| `↔` | 양방향 화살표 | diagram/profile |
| `※` | 참고 | document/profile |
| `#` | 샵 | tag/context |
| `@` | 앳 | email/handle context |
| `&` | 앤드 | acronym/fixed context |
| `*` | 별표 | document/math context |
| `/` | 슬래시 | preserve by default |
| `\` | 백슬래시 | path/code context |

기본 원칙:

```text
수학 기호는 숫자/수식 owner가 있을 때만 변환
일반 문장 기호는 preserve
URL/path/email 내부 기호는 preserve
```

### 35.16 Roman numeral / grade / model notation

| 입력 | reading | 조건 |
|---|---|---|
| `Ⅰ` | 일 | context required |
| `Ⅱ` | 이 | context required |
| `Ⅲ` | 삼 | context required |
| `Ⅳ` | 사 | context required |
| `Ⅴ` | 오 | context required |
| `Ⅵ` | 육 | context required |
| `Ⅶ` | 칠 | context required |
| `Ⅷ` | 팔 | context required |
| `Ⅸ` | 구 | context required |
| `Ⅹ` | 십 | context required |
| `I`, `II`, `III`, `IV` | profile/context | default preserve |

로마 숫자는 모델명, 챕터, 게임, 영화 제목에서 읽기가 달라지므로 기본 preserve가 안전하다. Unicode roman numeral 문자만 context가 있으면 처리한다.

### 35.17 Immediately addable S0 candidates

조건 없이 boundary만 맞으면 추가해도 비교적 안전한 항목이다.

```text
AI -> 에이아이
API -> 에이피아이
TTS -> 티티에스
STT -> 에스티티
ASR -> 에이에스알
OCR -> 오씨알
NLP -> 엔엘피
LLM -> 엘엘엠
GPT -> 지피티
PDF -> 피디에프
HTML -> 에이치티엠엘
CSS -> 씨에스에스
JSON -> 제이슨
XML -> 엑스엠엘
CSV -> 씨에스브이
HTTP -> 에이치티티피
HTTPS -> 에이치티티피에스
URL -> 유알엘
URI -> 유알아이
USB -> 유에스비
HDMI -> 에이치디엠아이
SSD -> 에스에스디
HDD -> 에이치디디
CPU -> 씨피유
GPU -> 지피유
KOSPI -> 코스피
KOSDAQ -> 코스닥
IMF -> 아이엠에프
OECD -> 오이시디
WTO -> 더블유티오
WHO -> 더블유에이치오
UN -> 유엔
EU -> 이유
```

### 35.18 Dictionary test requirements

사전 항목은 반드시 테스트에 들어가야 한다.

```text
dictionary_smoke_tests:
- 모든 dictionary entry가 boundary 조건에서 기대 reading을 내는지 확인

dictionary_condition_tests:
- numeric prefix required 항목이 숫자 없이 나오면 preserve되는지 확인

dictionary_collision_tests:
- unit_alias와 dictionary 충돌 확인
- file extension과 일반 약어 충돌 확인
- currency code와 acronym 충돌 확인

dictionary_shadow_tests:
- generated reading 뒤 Safe 조사 예외 적용 확인
- ORIGINAL_KOREAN은 교정하지 않는지 확인
```

예:

```text
10kg -> 십 킬로그램
kg -> kg
60fps -> 육십 에프피에스
fps가 낮다 -> 에프피에스가 낮다
€50을 -> 오십 유로를
유로을 -> 유로을
2025/01/03 -> 이천이십오년 일월 삼일
docs/2025/01/03/report.md -> preserve
AI가 -> 에이아이가
AI이 -> 에이아이이
```

## 36. Guardrail additions

이 항목들은 `27.2 Codex Implementation Guardrails`에 추가된 것과 동일한 강도의 구현 규칙이다.

1. colon time scanner는 longest match first로 실행한다.
   - `HH:MM:SS`, `H:MM:SS`, `HH:MM`, `H:MM` 순서로 claim한다.
   - `H:MM` parser는 `H:MM:SS`의 앞부분을 partial consume하면 안 된다.

2. `H:MM`과 `H:MM:SS`는 단독 전체 입력이면 preserve한다.
   - time prefix, time postposition, event keyword, schedule/list context, duration/media context 중 하나가 필요하다.

3. `H:MM:SS`는 clock과 duration semantic gate를 분리한다.
   - 둘 다 강하면 preserve한다.

4. `YYYY-MM-DD` owner는 `date_time.date`가 우선 claim한다.
   - `code_separator_block` scanner는 exact `4-2-2` date-like pattern을 최초 claim하지 않는다.
   - calendar-valid이면 날짜로 읽는다.
   - calendar-invalid이면 fallback guard를 모두 통과한 경우에만 `CODE_SEPARATOR_BLOCK_SURFACE` fallback을 허용한다.
   - code separator guard 실패 시 preserve한다.

5. `YYYY/MM/DD` owner는 `date_time.date`다.
   - fraction/path/unit parser는 exact `4-2-2` slash date-like pattern을 claim하지 않는다.
   - slash date parse fail이 calendar-invalid인 경우 fraction/path/unit fallback은 금지하고 `CODE_SEPARATOR_BLOCK_SURFACE` fallback만 평가한다. URL/path-like context면 preserve한다.
   - URL/path-like context는 slash date를 차단한다.

6. modern full date는 기본적으로 `1900~2099` 범위만 지원한다.
   - 범위 밖 연도는 실제 날짜일 수 있어도 preserve한다.

7. date parser는 month/day calendar validity를 검사한다.
   - 윤년을 반영한다.
   - calendar-valid `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY.MM.DD`는 날짜로 읽는다.
   - calendar-invalid full date-like `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY.MM.DD`는 fallback guard를 모두 통과한 경우에만 `CODE_SEPARATOR_BLOCK_SURFACE` fallback으로 읽는다.
   - fallback guard는 다음을 모두 만족해야 한다.
     1. pure numeric 3-block이다.
     2. 각 block은 `4-2-2` shape을 유지한다.
     3. 모든 구분자가 동일하다.
     4. 구분자 좌우에 공백이 없다.
     5. URL/path/email 내부가 아니다.
     6. alphabetic tail이 붙지 않았다.
     7. square bracket 보호 구간 내부가 아니다.
     8. version/log/model/code context가 아니다.
   - fallback guard 실패 시 preserve한다.

8. dictionary expansion은 조건부 교정을 기본으로 한다.
   - 단위/파일크기/통화/복합단위는 numeric prefix 또는 owner-specific context를 요구한다.
   - URL/path/email/code 내부 사전 교정은 기본 preserve다.

9. 모든 `30. 확장 정책`의 항목은 smoke, preserve, gate, full consume, collision, shadow test에 포함한다.

## 37. Long-article Gap Policy

Long-article gap policy는 장문 기사 smoke에서 반복적으로 드러난 정책 공백 중 기존 owner/gate 원칙과 충돌하지 않는 항목만 보강한다. 모든 항목은 full consume 또는 preserve 중 하나여야 하며 partial rewrite는 금지한다.

### 37.1 Unsigned temperature

`℃`, `º`, `ºC`는 섭씨라고 읽지 않고 plain degree로 읽는다. `℉`, `ºF`는 `화씨 ...도`로 읽는다. 정수와 소수를 모두 지원한다.

부호가 없으면 `영상` 또는 `플러스`를 붙이지 않는다. signed case에서는 `º` bare degree는 temperature-like로 처리하지만, `°` signed degree는 기존 angle policy를 유지한다.

```text
25℃ -> 이십오도
25º -> 이십오도
25ºC -> 이십오도
25° -> 이십오도
2.5℃ -> 이쩜오도
25℉ -> 화씨 이십오도
2.5ºF -> 화씨 이쩜오도
30ºCtest -> 30ºCtest
40℉abc -> 40℉abc
```

### 37.2 Duration and counter inventory

Clock hour `시`와 duration `시간`은 별도 suffix owner다.

Clock hour `N시`는 시각이다. `1~12시`는 고유어 hour form으로 읽고, `13~24시`는 24시간제 표기로 보고 한자어 숫자 + `시`로 읽는다.

```text
1시 -> 한 시
2시 -> 두 시
3시 -> 세 시
4시 -> 네 시
10시 -> 열 시
11시 -> 열한 시
12시 -> 열두 시
13시 -> 십삼 시
19시 -> 십구 시
20시 -> 이십 시
21시 -> 이십일 시
22시 -> 이십이 시
23시 -> 이십삼 시
24시 -> 이십사 시
오전 9시 5분 -> 오전 아홉 시 오분
오후 3시 20분 -> 오후 세 시 이십분
23시 59분 -> 이십삼 시 오십구분
```

Duration `N시간`은 지속 시간이다. `1~23시간`은 고유어 duration form으로 읽고, `24시간` 이상은 한자어 숫자 + `시간`으로 읽는다. `20시간`은 `스물 시간`이 아니라 `스무 시간`이다.

```text
1시간 -> 한 시간
2시간 -> 두 시간
3시간 -> 세 시간
4시간 -> 네 시간
10시간 -> 열 시간
11시간 -> 열한 시간
12시간 -> 열두 시간
13시간 -> 열세 시간
19시간 -> 열아홉 시간
20시간 -> 스무 시간
21시간 -> 스물한 시간
22시간 -> 스물두 시간
23시간 -> 스물세 시간
24시간 -> 이십사 시간
25시간 -> 이십오 시간
48시간 -> 사십팔 시간
72시간 -> 칠십이 시간
```

`분`, `초`는 sino counter로 읽고 붙인다. `05분`, `05초`처럼 두 자리 leading zero minute/second는 time reading과 같은 방식으로 허용한다.

`건`, `곳`은 hybrid counter로 추가한다. `점`은 sino counter로 추가한다. 세 단위는 단위 앞에 띄어쓰기를 둔다.

```text
7시간 05분 -> 일곱 시간 오분
3시간 이상 -> 세 시간 이상
15건 -> 열다섯 건
59건 -> 오십구 건
120점 -> 백이십 점
8곳 -> 여덟 곳
```

### 37.3 Currency decimal/code coverage

통화 owner는 symbol-prefix, code-prefix, suffix-code/symbol을 full consume한다. Decimal은 달러/유로에 허용한다. Comma integer는 원/엔/유로에 허용한다. Code-like tail은 preserve한다.

```text
$25.99 -> 이십오쩜구구 달러
€1,234 -> 천이백삼십사 유로
1,234.56 EUR -> 천이백삼십사쩜오육 유로
300 USD -> 삼백 달러
300 EUR -> 삼백 유로
300 KRW -> 삼백 원
300EURabc -> 300EURabc
EURA 300 -> EURA 300
```

### 37.4 Data, power, and frequency units

`MB`, `GB`, `PB`, `kWh`, `Hz`, `hz`, `MHz`, `GHz`, `Gbps`는 numeric prefix가 있을 때만 변환한다. 정수와 소수를 모두 허용한다. 공백형은 `Hz`/`hz` frequency 단위에 한정해 허용하고, 단독 unit은 preserve한다. alphabetic unsafe tail은 full token preserve다.

```text
12.5MB -> 십이쩜오 메가바이트
2.4PB -> 이쩜사 페타바이트
3.2kWh -> 삼쩜이 킬로와트시
60Hz -> 육십 헤르츠
120 Hz -> 백이십 헤르츠
3.2GHz -> 삼쩜이 기가헤르츠
5Hzabc -> 5Hzabc
Hz -> Hz
```

### 37.5 pH

`pH`는 exact lowercase `pH`만 지원한다. 숫자는 붙거나 한 칸 이상 떨어질 수 있다. trailing alphabet이 있거나 `pH` 앞에 ASCII/Hangul 문자가 붙은 경우 full preserve한다.

```text
pH 7.4 -> 피에이치 칠쩜사
pH7.4 -> 피에이치 칠쩜사
pH 12 -> 피에이치 십이
xpH 7.4 -> xpH 7.4
pH7.4test -> pH7.4test
pH -> pH
```

### 37.6 Spaced separator preserve

공백이 포함된 dotted/middle-dot numeric separator는 event/decimal owner가 아니다. 양쪽 숫자 중 한쪽만 변환하지 말고 full preserve한다.

```text
12 · 3 -> 12 · 3
12. 3 -> 12. 3
12 .3 -> 12 .3
```

공백 없는 정상 event/decimal은 기존 정책을 유지한다.

```text
12.3 비상계엄 -> 십이삼 비상계엄
12·3 비상계엄 -> 십이삼 비상계엄
3.14 -> 삼쩜일사
```

### 37.7 Current policy retained / future phase

현재 정책에서는 다음 항목을 변경하지 않는다.

- `4위` 같은 순위 품질 개선
- `제62회`, `제15권` 같은 numeric-prefixed noun은 현재 정책에서 numeric suffix owner 대상이며 `제 육십이회`, `제 십오권`처럼 출력한다.
- bare `-1.3도`를 기상 문맥 없이 `영하`로 일반화하는 정책
- approved gate 밖의 arbitrary hyphen numeric range 정책
- standalone `2:1`, non-approved `3:2 승` 같은 score/ratio 정책
- 사용자 입력 소괄호 `( ... )` 최종 삭제 정책

## 38. Duration, Percent-point, and Fraction Policy

Duration, percent-point, and fraction policy는 duration, percent-point, slash fraction을 explicit owner로 추가한다. 모든 항목은 owner-first claim과 full consume 또는 preserve 원칙을 따른다. 공백, unsafe tail, code-like token, slash path, compound unit과 충돌하는 부분은 preserve한다.

### 38.1 시간/분 duration

다음 duration surface를 읽는다.

- 시간 단독: `##시간`
- 분 단독: `##분`
- 시간+분: `##시간 ##분`, `##시간##분`

각 숫자 block은 0 이상의 정수, 소수, 일반 slash fraction, 규칙적인 comma 자리수 숫자를 허용한다. 음수 duration은 preserve한다. 시간 또는 분 중 하나라도 음수이면 해당 duration claim을 적용하지 않고 preserve한다.

읽기 방식:

- `시간` 앞 1~23 자연수는 고유어 duration form을 따른다.
- `시간` 앞 0, 24 이상, 소수, 분수, comma 큰 수는 한자어 숫자 reading을 사용하고 `시간` 앞에 공백을 둔다.
- `분`은 기존 duration policy처럼 한자어 숫자 reading을 사용하고 `분`을 붙인다.
- `05분`처럼 두 자리 leading zero minute은 `오분`으로 허용한다.

```text
3시간 -> 세 시간
7시간 -> 일곱 시간
20시간 -> 스무 시간
23시간 -> 스물세 시간
24시간 -> 이십사 시간
48시간 -> 사십팔 시간
0시간 -> 영 시간
1,200시간 -> 천이백 시간
2.5시간 -> 이쩜오 시간
1/2시간 -> 이분의 일 시간
18분 -> 십팔분
05분 -> 오분
1,200분 -> 천이백분
2.5분 -> 이쩜오분
1/2분 -> 이분의 일분
3시간 18분 -> 세 시간 십팔분
3시간18분 -> 세 시간 십팔분
-3시간 -> -3시간
3시간 -18분 -> 3시간 -18분
```

### 38.2 Percent-point `%p`

`##%p`는 `[숫자 reading] 퍼센트포인트`로 읽는다. 숫자는 정수, 음수, 소수, slash fraction, 규칙적인 comma 자리수 숫자를 허용한다. `%p`는 일반 `%` percent보다 먼저 full consume한다.

```text
2.5%p -> 이쩜오 퍼센트포인트
-2.5%p -> 마이너스 이쩜오 퍼센트포인트
1/2%p -> 이분의 일 퍼센트포인트
1,200%p -> 천이백 퍼센트포인트
0.5%p -> 영쩜오 퍼센트포인트
33%p -> 삼십삼 퍼센트포인트
2.5%point -> 2.5%point
2.5%pa -> 2.5%pa
A2.5%p -> A2.5%p
```

일반 percent는 기존 percent unit 정책을 유지하되 decimal percent도 full consume한다.

```text
33.3% -> 삼십삼쩜삼 퍼센트
72% -> 칠십이 퍼센트
```

### 38.3 Slash fraction `##/##`

일반 slash fraction은 양수 분자/분모만 허용한다. 각 block은 정수 또는 규칙적인 comma 자리수 숫자를 허용한다. 출력은 `[분모 reading]분의 [분자 reading]`이다. 음수는 `-##/##` 형태만 허용하고 `마이너스`를 앞에 붙인다.

```text
1/3 -> 삼분의 일
4/7 -> 칠분의 사
10/25 -> 이십오분의 십
1,200/3,400 -> 삼천사백분의 천이백
-1/3 -> 마이너스 삼분의 일
```

다음은 preserve한다.

```text
0/3 -> 0/3
1/0 -> 1/0
1.5/3 -> 1.5/3
1/3.5 -> 1/3.5
1 / 3 -> 1 / 3
1/ 3 -> 1/ 3
1 /3 -> 1 /3
1/3abc -> 1/3abc
abc1/3 -> abc1/3
A/B -> A/B
USB/300 -> USB/300
```

Slash fraction owner는 date/slash date, path/code-like token, compound slash unit과 충돌하지 않도록 엄격한 boundary를 적용한다. `km/L`, `m/s`, `15.2km/L` 등은 compound unit owner가 우선한다.

## 39. Phase 34C no-crash fallback invariant

Phase 34C는 valid text input으로 인해 내부 parser, owner, renderer, validation 단계에서 exception이 발생하더라도 public transform, CLI, API 실행 경로 전체가 crash하지 않는 것을 runtime invariant로 둔다.

1. Valid text input으로 인해 내부 parser/owner/renderer exception이 발생하더라도 전체 transform은 crash하지 않는다.
2. 내부 exception 발생 시 no-Hangul global bypass 또는 전체 입력 absolute preserve block에서는 `normalized_text`를 original input text로 fallback preserve할 수 있다. 한글 포함 입력에서는 실패 span/segment fallback으로 좁힌다.
3. debug/error metadata가 가능한 경로에서는 error class/message와 fallback marker를 기록한다.
4. CLI plain output 경로에서는 stdout에 original text를 반환하고, error는 stderr 또는 debug metadata로만 노출한다.
5. API 경로에서는 valid JSON request와 string `text` field가 있으면 `normalized_text`를 포함한 JSON을 반환한다.
6. invalid rollout mode, invalid CLI option, invalid JSON, missing binary, OS/process failure는 operational error로 처리할 수 있다.
7. fallback은 correctness를 가장한 변환이 아니라 preserve safety이다.
8. fallback은 broad rewrite가 아니며, 정상 기능 출력 변경을 목적으로 하지 않는다.

이 invariant는 owner/gate 정책을 약화하지 않는다. 개별 owner는 계속 full consume 또는 preserve 원칙을 지키며, no-crash fallback은 마지막 방어선으로만 동작한다.

## 40. JSON-like protected string values

JSON-like container string values are common protected spans. Numeric owners,
currency owners, unit/temperature/range/colon/hyphen owners, and large-unit
owners must not rewrite string value contents inside JSON-like objects.

```text
{"price":"KRW1000"} -> {"price":"KRW1000"}
{"range":"1~2테스트"} -> {"range":"1~2테스트"}
{"large":"2천8백28억"} -> {"large":"2천8백28억"}
```

This is a common protected span/gate policy, not a currency-specific rule.
It belongs to the same protection layer as backtick, path, URL, email, and
code-like literal protection. The policy does not expand to arbitrary quoted
text in normal prose.

## 41. Ordinary decimal fractional zero canonicalization

This section records the implemented ordinary decimal fractional-zero
canonicalization for ordinary decimal-aware owners.

일반 수치 소수에서 소수부의 0은 모두 `영`으로 읽는다. 정수부 0도
`영`으로 읽는다.

```text
0.050 -> 영쩜영오영
1.50 -> 일쩜오영
25.00 -> 이십오쩜영영
1,000.50 -> 천쩜오영
```

`공`은 전화번호, 코드/식별자 등 기존 digit-reading owner가 명시적으로
소유한 문맥에 한정한다. 일반 수치 decimal renderer에서 `공`을 `영`으로
맞추기 위해 전역 문자열 치환을 사용하지 않는다. 구현은
`engine/span_engine/numeric_reading.py::read_decimal_fraction_digits`를
ordinary decimal-aware owner 경로에서 호출하는 방식으로 분리한다.

이번 정책은 leading-zero 처리, time-like 처리, phone/code/version/
identifier 처리를 변경하지 않는다. leading zero가 있다고 해서 malformed
decimal을 새로 읽지 않는다.

```text
01.5 -> current leading-zero fallback behavior 유지
+01.5kg -> invalid owner-attached preserve 유지
09:30 -> time-like owner behavior 유지
010-1234-5678 -> phone digit reading 유지
v01 -> version/code-like preserve 유지
```

Ordinary decimal-aware owner alignment includes:

- standalone decimal
- signed decimal
- unit / percent decimal
- KRW and non-KRW currency decimal
- temperature decimal
- large-unit decimal
- tilde range decimal
- colon / multi-colon decimal
- numeric-delimited range-compatible unit decimal

Excluded owner families:

- phone number digit reading
- code / identifier digit reading
- date and time-like reading
- leading-zero malformed numeric fallback
- version-like preserve
- malformed numeric segmented reading
- invalid numeric preserve policy
- JSON-like/path/URL/backtick protected contexts

Invalid comma grouping and leading-zero malformed decimal policy remain
unchanged. Valid unsigned standalone comma decimal is claimed:

```text
1,000.50 -> 천쩜오영
1,00.50 -> 1,00.50
01.5 -> existing leading-zero fallback behavior 유지
+01.50kg -> invalid owner-attached preserve 유지
```

Runtime coverage is provided by
`scripts/probes/decimal_fractional_zero.py`, which validates source and
production_source by default and supports optional `--binary` and `--api`
runners through the shared probe runtime matrix helper.

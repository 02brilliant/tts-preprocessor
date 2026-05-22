# TTS Preprocessor Policy Changelog

이 문서는 릴리스 로그가 아니라 현재 canonical policy로 정리된 주요 정책 변경과 결정 기록이다. 구현과 테스트 판단의 단일 원본은 `docs/policies/TTS_Preprocessor_policy.md`이며, 이 문서는 왜 현재 정책이 그런 형태인지 추적하기 위한 보조 문서다.

---

## 0. Latest Addendum: Numeric Surface Broad Reading

- Added `scripts/dev_probe_decimal_fractional_zero_reading.py` using the shared
  source/production_source/binary/API probe runtime matrix helper.
- Finalized ordinary decimal fractional zero documentation to implementation
  complete status, including protected, invalid/malformed, leading-zero, and
  unsigned comma decimal boundaries.
- Implemented phase-2 ordinary decimal fractional zero `영` canonicalization
  for standalone, signed, unit/percent, KRW/non-KRW currency, temperature,
  large-unit, tilde range, colon/multi-colon, and numeric-delimited decimal
  paths.
- Added `read_decimal_fraction_digits` as the ordinary decimal fractional
  helper and kept phone/code/time-like/digit-sequence readers separate.
- Enabled valid unsigned standalone comma decimals such as
  `1,000.50 -> 천쩜오영` while keeping invalid comma grouping and
  leading-zero malformed owner surfaces preserved according to existing policy.
- Removed the phase-1 xfail target status for ordinary decimal fractional zero;
  target cases are now regular regression assertions.
- Added phase-1 ordinary decimal fractional zero `영` canonicalization
  investigation without changing transform semantics.
- Documented current decimal renderer/helper paths for standalone, signed,
  unit/percent, currency, temperature, large-unit, range, colon/multi-colon,
  compound unit, legacy, and digit-sequence owner routes.
- Added production-source audit and non-strict xfail target coverage for
  ordinary decimal fractional zero canonicalization, including protected,
  invalid/malformed, leading-zero, and complex sentence cases.
- Recorded unsigned standalone comma decimal `1,000.50 -> 1,000.50` as a
  phase-1 owner coverage issue separate from signed comma decimal handling.
- Added common malformed numeric segmented reading policy analysis to the
  numeric matrix without changing transform semantics.
- Added current production-source audit coverage for malformed dot/comma
  numeric-like surfaces, severe invalid numeric surfaces, protected/code-like
  exclusions, and structural delimiter owner inventory.
- Documented that any future segmented reader must run only after absolute
  preserve, structural delimiter owners, existing valid full-claim owners, and
  owner-specific strict invalid preserve checks.
- Recorded future segmented reading candidates separately from current expected
  outputs, and kept severe invalid, protected/code-like, path, URL, JSON, and
  backtick surfaces outside segmented fallback scope.
- Added a dedicated colon/time-like runtime probe using the shared
  source/production_source/binary/API matrix helper and finalized the numeric
  matrix policy section for the three-step cleanup.
- Implemented stage-2 `N:M` / time-like minimal policy: strong bare time-like
  surfaces read as time, ambiguous no-context time-like surfaces preserve, and
  ambiguous ratio/score contexts read as `대`.
- Added stage-1 `N:M` / time-like canonical policy audit notes and target
  `xfail` tests without changing transform semantics.
- Added `TTS_Preprocessor_numeric_matrix.md` to audit standalone numeric, owner-attached numeric, invalid partial fallback, trailing-zero, protected-context, time-like, and hyphen exception behavior without changing transform semantics.
- Added common protected span handling for JSON-like string values so currency, unit, temperature, range, colon, hyphen, and large-unit owners do not rewrite them.
- Clarified that JSON-like protection is not a broad normal-prose quote protection policy.
- Clarified the official production source entrypoint as `engine.main.transform_with_rollout(text, mode="span_default", include_debug=False)`.
- Documented binary/API runtime routing through `bin/build_binary_entrypoint.py` and the packaged PyInstaller binary rather than deployed source imports.
- Clarified that `check_server.sh` is a health/sanity check and semantic regression coverage belongs in source/main/binary/API probes and parity tests.
- Expanded large-unit numeric input coverage for comma integer and signed decimal surfaces.
- Added mixed Arabic-Hangul large-unit full-claim handling.
- Added Hangul-tail spacing and English-tail literal retention behavior for large-unit numeric surfaces.
- Clarified large-unit English-tail behavior: valid numeric-large-unit cores are read and following English tails are kept literally without inserted spacing.
- Preserved code-like English-prefix large-unit surfaces.
- Added API/runtime path coverage for standalone large-unit numeric cores and reused the large-unit scanner in the legacy pipeline to block partial fallback.
- Blocked invalid large-unit partial fallback.
- Preserved standalone number, unit/percent/currency, temperature, range, colon, hyphen, phone, and protected surface behavior.
- Added registry-based currency form equivalence for registered code/symbol/suffix forms.
- Added KRW equivalence across `원`, `KRW`, `₩`, and `￦` forms.
- Added signed decimal-aware numeric support across equivalent currency forms.
- Added no-space / one ASCII-space currency attachment policy.
- Strengthened invalid numeric partial fallback blocking for currency contexts.
- Preserved protected/code-like surfaces and non-target unit/percent/temperature/range/hyphen/colon/phone policies.
- Added single-space unit suffix consistency for valid signed decimal-aware numeric blocks.
- Added single-space percent suffix consistency.
- Preserved attached unit/percent behavior.
- Restricted suffix spacing to no space or one ASCII space only.
- Strengthened invalid numeric partial fallback blocking for unit/percent contexts.
- Preserved temperature, range, hyphen, colon, currency, phone, slash/fraction policies.
- Updated two-block colon numeric policy documentation to match broad N:M reading.
- Clarified that semantic-pair keywords are no longer the only claim path.
- Added N:M arbitrary adjacent Korean tail spacing.
- Documented HH:MM time-like guard precedence and protected/invalid exclusions.
- Preserved multi-colon, tilde, hyphen, slash, phone, temperature, and currency policies.
- Changed tilde-like numeric range policy so arbitrary adjacent Korean tails no longer block range reading.
- Fixed tilde-like numeric ranges with arbitrary adjacent Korean tails.
- Added comma-decimal numeric block support in tilde-like broad ranges.
- Added optional whitespace support around tilde-like delimiters for numeric ranges.
- Added sentence-final punctuation handling for tilde-like numeric ranges.
- Prevented partial fallback inside valid tilde-like ranges that fail tail matching.
- Preserved unit/counter suffix canonical while spacing general Korean tails after range reading.
- Maintained protected/code-like/path/url/email/backtick/json-like and invalid numeric exclusions.
- Non-tilde delimiters remain unchanged.
- Added safe tail boundary support for signed temperature/unit/currency/percent/decimal surfaces before Korean endings and sentence punctuation.
- Broadened two-block colon numeric reading to `대` when not time/time-like, with `HH:MM` time-like recognizing `00..24` hours and `00..59` minutes.
- Added tilde-like numeric range reading without unit suffix and independent optional signs on both sides.
- Preserved protected/code-like/path/url/email/backtick exclusions and invalid numeric fallback blocking.
- Signed hyphen/en-dash ranges remain out of scope.

### 0.1 Temperature Context De-Duplication

- Added temperature context de-duplication for adjacent Korean Celsius/Fahrenheit labels with matching temperature symbols.
- Prevented duplicate Fahrenheit/Celsius rendering such as `화씨 화씨 영상...`.
- Preserved standalone temperature canonical and signed temperature handling.
- Kept mismatch label/symbol correction out of scope.

### 0.2 Numeric-Delimited Follow-Up Regressions

- Fixed full-width colon and mixed colon-like delimiter handling for multi-colon numeric surfaces.
- Fixed plus-start and mixed-sign multi-colon numeric handling.
- Narrowed code-like guard boundaries so independent multi-colon numeric surfaces after ordinary hyphenated English words can be claimed.
- Added plus comma-decimal KRW/currency full-claim handling for forms such as `+1,000.50원`.
- Preserved math-like expressions as whole spans to avoid unsafe partial numeric reading.
- Kept bracket, square-bracket, and temperature sign policies unchanged.
- Added real long-sentence regression/probe cases from observed webpage output issues.

### 0.3 Leading Plus Sign Numeric Policy

- Added leading plus sign numeric policy.
- Extended signed decimal-aware numeric parsing from minus-only to plus/minus signs where the owner explicitly supports signed numeric surfaces.
- Render leading `+` as `플러스`; existing `-` behavior remains `마이너스`.
- Added plus support for general numeric, unit/symbol/currency/temperature/percent, numeric-delimited semantic pair, multi-colon, tilde-like range, and international phone surfaces.
- Phone owner now full-consumes supported `+국가번호` phone-like surfaces and renders the leading plus as `플러스` before the existing digit-block phone canonical.
- Preserved protected/code-like/path/url/email/math-like exclusions including `C++`, `A+B`, `foo+bar`, and `a+=1`.
- Strengthened partial fallback guards for plus-signed numeric-like surfaces so failed owners do not rewrite internal numeric fragments.
- Decimal rendering keeps the existing compact `쩜` canonical and preserves trailing fractional digits.
- Signed hyphen/en-dash range remains out of scope.

### 0.4 Temperature Sign Canonical Correction

- Restored temperature-owner sign canonical for signed Celsius/Fahrenheit surfaces.
- Temperature `+` is rendered as `영상`, not `플러스`.
- Temperature `-` remains rendered as `영하`, not `마이너스`.
- General plus numeric, unit, currency, percent, phone, N:M semantic pair, multi-colon, and tilde-like range behavior remains unchanged.
- Signed unit/percent surfaces continue to use explicit sign words (`플러스`/`마이너스`) while temperature symbols use `영상`/`영하`.
- Temperature owner precedence over general signed number/unit owners remains required so signed temperature surfaces are full-consumed.

## 1. Canonical Document Consolidation

정책 문서는 버전 번호별 구현 지시가 아니라 현재 정책의 단일 기준 문서로 정리한다.

- `docs/policies/TTS_Preprocessor_policy.md`를 현재 canonical policy로 둔다.
- `docs/policies/TTS_Preprocessor_policy_changelog.md`는 결정 기록으로만 사용한다.
- 과거 버전명 중심 문서와 누적된 임시 notes는 참고 자료이며, 정책 해석은 canonical policy 본문을 우선한다.
- 앞부분에 덧붙었던 eligibility, symbol alias, preserve taxonomy, numeric/date/range correction 내용은 관련 owner 본문과 우선순위/테스트 섹션에 통합한다.

## 2. Preserve Taxonomy and Owner Fallback

`preserve`는 단일 의미가 아니다. 현재 정책은 다음 세 상태를 구분한다.

- `Absolute Preserve`: URL, email, path, JSON, shell, code-like, square bracket internal boundary, unsafe alphabetic tail 등 owner 재진입이 금지되는 보호 상태다.
- `Owner Fallback Candidate`: 특정 owner 조건을 만족하지 않아도 즉시 preserve하지 않고 다음 후보 owner 평가를 허용하는 상태다.
- `Terminal Fallback Preserve`: 모든 후보 owner가 실패하거나 full consume/validation에 실패한 뒤 최종적으로 원문을 출력하는 상태다.

대표 결정:

- event owner 실패 dotted numeric은 decimal fallback으로 넘긴다.
- event owner 실패 middle-dot numeric은 middle-dot numeric block fallback으로 넘긴다.
- calendar-invalid date-like는 guarded code separator fallback을 허용한다.
- generic numeric + Korean suffix는 numeric suffix/counter 후보 평가를 허용한다.
- leading-zero numeric block은 code digit reading fallback을 허용한다.

### 2.1 Clarification Addendum

이번 변경은 정책 의미를 바꾸는 새 기능 추가가 아니라 해석 보강이다.

- Safe post-surface particle exception과 partial rewrite의 경계를 명확히 했다.
- standalone numeric token과 code-like numeric token의 경계를 명확히 했다.
- short slash date는 current policy non-goal임을 다시 적었다.
- fallback status taxonomy를 trace/debug 관점에서 구분하도록 명확히 했다.
- 새 기능 추가 없음.
- 코드 변경 없음.

## 3. Korean Eligibility and Non-Korean Preserve

Korean eligibility gate는 owner 정책을 대체하지 않고, owner 평가 대상 segment를 결정한다.

- code-like, URL, email, path, JSON, shell command preserve가 numeric-list 판정보다 우선한다.
- 전체 입력이 standalone supported token이면 한글이 없어도 transform한다.
- 한글 없는 영어/비한국어 prose 또는 code-like block은 exact preserve한다.
- 한글 line과 no-Hangul line이 섞인 입력에서만 line-level gate를 적용한다.
- Korean-context numeric-list line은 인접한 한국어 문맥이 있을 때만 transform한다.
- 한글 포함 입력에서는 whole-input fallback을 금지한다. validation/parser/owner 실패는 실패 span 또는 실패 segment 단위로만 degrade해야 하며, 하나의 unsupported 또는 preserve token이 같은 문단/문서의 다른 변환을 막으면 regression failure로 본다.

## 4. Symbol Alias Scope

symbol alias는 owner-local matcher에서만 적용한다. 전역 Unicode normalization, 전역 문자열 치환, fullwidth ASCII normalization은 금지한다.

유지되는 alias 범위:

- slash/fraction alias: `／`, `⁄`, `∕`
- percent alias: `％`, `﹪`
- colon time alias: `：`
- tilde/range alias: `~`, `∼`, `～`, `〜`
- signed minus alias: `−`, `－`
- temperature/unit aliases: `°C`, `°F`, `㎜`, `㎝`, `㎞`, `㎎`, `㎏`, `㎡`, `㎥`, `㎐`, `㎒`, `㎓`, etc.

명시 non-goal:

- broad dash alias such as en dash/em dash
- fullwidth Latin/digit normalization
- NFD Hangul eligibility
- middle-dot alias expansion beyond policy-defined forms
- kHz compatibility symbol `㎑`

## 5. Numeric, Unit, and Suffix Corrections

명시 owner가 소유한 numeric surface는 decimal과 valid comma decimal도 full consume 대상이다.

주요 결정:

- Added a numeric-delimited two-block policy for ASCII `N-M` and `N:M` surfaces.
  Standalone or ambiguous two-block surfaces are not broad numeric fallback targets:
  internal numeric blocks must not be partially rewritten.
  `N-M` is read as a range only when followed by a range-compatible registered unit,
  counter, classifier, or safe range noun, such as `1-2장 -> 일에서 이 장`,
  `10-20개 -> 십에서 이십 개`, and `1-2kg -> 일에서 이 킬로그램`.
  `N:M` is read as time only with explicit time context such as a prefix,
  postposition, or narrowly adjacent schedule/time keyword; standalone `13:05`
  remains unchanged. Two-block `N:M` duration/media interpretation is excluded.
- Hardened the `N-M` range-compatible unit source by moving scanner-local
  allowlist behavior behind registry-backed compatibility helpers/tables.
  Missing range-compatible metadata now defaults to non-compatible, and existing
  approved numeric-delimited range outputs remain unchanged.
- Added first-pass `N:M` semantic pair owner policy and implementation.
  Explicit ratio/scale/score/result/game-match contexts render as
  `read(N) + " 대 " + read(M)`, without splitting ratio and score into separate
  owners because their rendering is identical. The owner supports valid
  thousands comma grouping and up to 8 digits per numeric block after comma
  removal. Current broad policy also reads valid non-time-like two-block `N:M`
  after protected/code-like/invalid guards, while scripture and two-block
  duration/media owners remain out of scope.
- Added shared delimiter equivalence classes for numeric-delimited owners.
  `COLON_LIKE_DELIMITERS` now define first-pass `:` and `：` behavior for time,
  semantic-pair, and `N:M` fallback-block scanning. `RANGE_LIKE_DELIMITERS` now
  define first-pass `-`, `–`, `~`, and `～` behavior for range-compatible
  `N-M` unit reading and fallback-block scanning. Delimiter equivalence is
  scanner-local and does not globally normalize protected/code-like text.
- Extended numeric-delimited owners from integer-only blocks to decimal-aware
  numeric blocks. `N:M` semantic pair and `N-M` range-compatible unit owners now
  share decimal-aware numeric block validation, allowing unsigned decimals and
  valid thousands comma grouping in the integer part. Fractional digits are
  preserved during rendering, including trailing zeros. Standalone or ambiguous
  `N-M` remains no-claim with numeric fallback blocked. Non-time-like valid
  `N:M` now follows broad `대` reading, and existing
  time/protected/code-like precedence is preserved. This does not add signed,
  slash, Korean `대` delimiter, scripture, or two-block duration/media handling.
- Fixed decimal numeric-delimited rendering to follow the existing `쩜`
  decimal canonical instead of spaced `점`, while preserving trailing
  fractional digits. Extended the `N:M` semantic pair owner to signed
  decimal-aware numeric blocks and extended `N-M` unit range handling to signed
  tilde-like ranges. Signed range is limited to `~`, `～`, `∼`, and `〜`; it
  does not apply to `-` or `–`. Standalone/ambiguous fallback-block behavior and
  time/protected/code-like precedence remain unchanged. Plus sign, slash ratio,
  Korean `대` delimiter, duration/media, and scripture owner remain out of
  scope.
- Added multi-colon numeric `대` reading owner for three to eight colon-delimited
  numeric blocks. Three-block surfaces preserve time/duration/media precedence
  and avoid H:MM:SS-like timecode shapes. Four-to-eight-block surfaces render
  valid signed decimal-aware numeric blocks joined by `대`; nine-or-more-block
  surfaces remain unclaimed with numeric fallback blocked. The owner reuses the
  signed decimal-aware parser and `쩜` decimal canonical, strengthens fallback
  blocking against partial numeric rewrites, and keeps protected/code-like/path/
  version contexts higher priority.
- Added owner-scoped `K-` + Hangul lexical prefix policy.
  `K-푸드`, `K-뷰티`, `K-컬처`, `K-콘텐츠`, `K-방산`, `K-드라마`, and `K-팝` are read as `케이` + the original Hangul token.
  The owner must full-consume the token and must not partially rewrite unsafe/code-like tails such as `K-푸드-v2`.
  Existing fixed term `K-POP -> 케이팝` remains unchanged.
- Added owner-scoped single-letter uppercase alnum code policy.
  One uppercase letter followed by optional hyphen, integer digits, and optional uppercase tail of one or two letters is read as alphabet name + number reading + optional tail letters.
  Digits 1-9 are read with English digit names; 10 and above are read Sino-Korean.
  Examples: `K-1 -> 케이 원`, `K10 -> 케이 십`, `F-15C -> 에프 십오 씨`, `A-10C -> 에이 십 씨`.
  Multi-letter acronym codes and unsafe tails remain protected, and `K-2024` remains preserved.

- `1.2km -> 일쩜이 킬로미터`
- `1.2 km -> 일쩜이 킬로미터`
- `0.8초 -> 영쩜팔초`
- `2,645.35선 -> 이천육백사십오쩜삼오선`
- `제15권 -> 제 십오권`
- `제62회 -> 제 육십이회`

일반 counter와 충돌할 수 있는 `권`, `장`, `회`는 policy-defined numeric suffix 조건과 counter 조건을 구분한다.

- Updated counter hybrid threshold policy: `개`, `권`, `장`, `명`,
  `마리`, `그루`, `송이`, `자루`, `알`, `벌`, `켤레`, `그릇`,
  `공기`, `잔`, `병`, `조각`, and `차례` now use hybrid threshold 39.
  Numbers 1-39 use native Korean readings; 40 and above use Sino-Korean readings.
- Aligned `차례` spacing with other counters:
  `2차례 -> 두 차례`, `40차례 -> 사십 차례`.
- Kept `사람` and `살` as native_only counters.
- Previous policy introduced 100+ tail-native reading for native/hybrid counters:
  high-order digits were read Sino-Korean, while the final 1-39 tail used native counter reading.
  Previous examples: `101명 -> 백한 명`, `139명 -> 백서른아홉 명`, `140명 -> 백사십 명`.
- Replaced the previous 100+ tail-native counter reading policy with a 100+ Sino-Korean counter policy.
  Native/hybrid counter behavior now applies only to values 1~99.
  All counter values 100 and above are read fully in Sino-Korean.
  Examples: `101명 -> 백일 명`, `139명 -> 백삼십구 명`, `101살 -> 백일 살`, `112명 -> 백십이 명`, `119건 -> 백십구 건`.
  Emergency context digit reading for `112`/`119` remains unchanged.
- Added explicit hybrid threshold 39 counters:
  `건`, `곳`, `팀`, `쌍`, `상자`, `봉지`, `통`, `묶음`, `편`, `판`, `줄`, `칸`.
- Added additional hybrid threshold-39 counters: `대`, `석`, `표`, `매`,
  `문항`, `문제`, `곡`, `장면`, `세트`, `팩`, `봉`, `종류`, `항목`, `사례`.
  These counters use native readings for 1~39 and Sino-Korean readings for 40+.
  The existing 100+ Sino counter policy applies.
  This change does not expand explicit `제N+단위` ordinal targets.
  `쪽` and `부` are intentionally excluded from this counter expansion.
- Updated canonical output for `제+숫자+한글단위`:
  outputs now use `제 ` + Sino-Korean number reading + attached unit.
  Examples: `제5차 -> 제 오차`, `제15권 -> 제 십오권`, `제2편 -> 제 이편`.
- Added support for the spaced form `제 N+한글단위` when the left boundary is sentence start or whitespace and the gap between `제` and the number is exactly one space.
  Examples: `제 5차 -> 제 오차`, `제 2편 -> 제 이편`.

### 5.1 Bare Integer and Milliliter Alias Clarification

Plain integer와 valid thousands-comma integer는 standalone supported numeric token이며, 일반 한국어 원고 또는 numeric-list segment 안에서도 일반 정수 reading으로 변환한다. 단, identifier/code-like 내부 숫자와 invalid comma는 preserve한다.

- `1,250 -> 천이백오십`
- `12,345 -> 만 이천삼백사십오`
- `6402 -> 육천사백이`
- `10000 -> 만`
- `id_12345`, `ABC123`, `v1.2.3`, `log_2025_01_03` preserve
- Clarified large-number group spacing as canonical:
  numbers are read in 4-digit groups, group-internal readings are attached,
  and non-empty `만/억/조/경` groups are separated by one space.
  Examples: `12,345,678,901 -> 백이십삼억 사천오백육십칠만 팔천구백일`,
  `12,345,678,901,234명 -> 십이조 삼천사백오십육억 칠천팔백구십만 천이백삼십사 명`.

Milliliter unit alias는 numeric prefix가 있을 때 `mL`, `ml`, `ML`, `㎖`를 같은 `밀리리터` surface로 처리한다. Unsafe alphabetic tail은 preserve한다.

### 5.2 Compact Relation and Prefixed Ordinal Suffix Clarification

Compact `N대M` relation은 score/ratio owner 확장이 아니라 일반 number fallback으로 양쪽 숫자 core를 모두 읽는다. `대`와 뒤 조사/어미는 원문 한글 literal로 유지한다. 이후 정책에서 explicit semantic-pair keyword 문맥의 ASCII `N:M`은 `N:M semantic pair owner`로 승인되었지만, standalone colon score와 hyphen score/range는 non-goal로 유지한다.

- `1대1로 -> 일대일로`
- `2대1 구조 -> 이대일 구조`
- `3:2 승`, `1-1 무`, `1-2` preserve
- `3:2 세트 -> 삼 대 이 세트`

한글 prefix/suffix에 공백 없이 붙은 숫자는 별도 고유어 counter 정책 또는 `제+숫자+등록된 한글표기단위` 정책이 명확히 적용되는 경우가 아니면 기본 한자어 숫자로 읽는다. `제N+등록된 한글표기단위`와 조건을 만족하는 `제 N+등록된 한글표기단위`는 `제 ` + 한자어 숫자 reading + 단위로 출력한다.

- `제5차 -> 제 오차`
- `제15권 -> 제 십오권`
- `제62회 -> 제 육십이회`
- `제4과 -> 제 사과`
- `제 5차 -> 제 오차`
- `제 15권 -> 제 십오권`
- `제12권 -> 제 십이권`
- Generalized `제N+Hangul unit` ordinal handling to registered Hangul counter/suffix inventory.
  When `제` is followed by an integer and a registered Hangul counter/suffix, the number is always read in Sino-Korean and rendered as `제 ` + Sino number + suffix.
  This applies to both `제N+suffix` and `제 N+suffix`.
  Counter native/hybrid readings remain unchanged for plain `N+suffix`.
  Unsafe tails and code-like prefixes remain preserved.

## 6. Frequency and Data-rate Decisions

Frequency aliases:

- `Hz` and `hz` use the same `헤르츠` policy.
- `kHz/khz`, `MHz/mhz`, `GHz/Ghz/ghz` are same-family frequency units when a numeric prefix exists.
- Unsafe alphabetic tails preserve: `5Hzabc`, `5hzabc`.

Bitrate and slash throughput are distinct:

- `1Gbps -> 일 기가비피에스`
- `1Gb/s -> 초당 일 기가바이트`
- `KB/s`, `MB/s`, `GB/s`, `TB/s`, `PB/s` and approved case variants use slash throughput reading.
- Slash-side spaces remain unsupported: `1,000 KB / s` preserve.

## 7. Currency and Decimal KRW Large Unit

Currency owner remains strict about boundary, amount shape, and unsupported tails.

Decimal Korean large-unit KRW expansion is owner-owned only when KRW `원` is present:

- `3.5만 원 -> 삼쩜오 만 원`
- `1.2억 원 -> 일쩜이 억 원`
- `2.75억 원 -> 이쩜칠오 억 원`
- `3.5만 -> 삼쩜오 만`

The rule is restricted to positive decimal Arabic numbers, `만/억/조`, and KRW `원`, with safe boundary checks.

## 8. Date, Month, and Range Decisions

Arabic `6월` and `10월` are read as `유월` and `시월` when rendered as date months. Literal Korean `유월` and `십월` are preserved as original Korean text.

Examples:

- `6월 -> 유월`
- `10월 -> 시월`
- `2026년 6월 17일 -> 이천이십육년 유월 십칠일`
- `2026-06-17 -> 이천이십육년 유월 십칠일`
- `2026/06/17 -> 이천이십육년 유월 십칠일`
- `2026년 10월 1일 -> 이천이십육년 시월 일일`
- `10월 21일 -> 시월 이십일일`
- `6개월 -> 육개월`
- `10개월 -> 십개월`
- `유월 -> 유월`
- `십월 -> 십월`

Clock hour `시` and duration `시간` are separate suffix owners. Shared suffix range follows the suffix type:

- `1~11월 -> 일월에서 십일월`
- `2024~2026년 -> 이천이십사년에서 이천이십육년`
- `3~5일 -> 삼일에서 오일`
- `2~3시 -> 두 시에서 세 시`
- `10~12시 -> 열 시에서 열두 시`
- `13~15시 -> 십삼 시에서 십오 시`
- `20~22시 -> 이십 시에서 이십이 시`
- `10~30분 -> 십분에서 삼십분`
- `3~8초 -> 삼초에서 팔초`
- `7~9시간 -> 일곱 시간에서 아홉 시간`
- `20~22시간 -> 스무 시간에서 스물두 시간`
- `24~48시간 -> 이십사 시간에서 사십팔 시간`

Clock hour `시` uses native hour form for `1~12시` and Sino clock hour form for `13~24시`. Duration `시간` uses native duration form for `1~23시간` and Sino duration form for `24시간` and above. `20시간` is `스무 시간`, not `스물 시간`.

Partial or mis-owned range readings are forbidden:

- `7~9시간 -> 칠시에서 구시간`
- `7~9시간 -> 칠시에서 아홉 시간`

Non-date physical-unit range keeps generic shared-suffix reading:

- `3~8cm -> 삼에서 팔 센티미터`
- `3~5km -> 삼에서 오 킬로미터`

Page/document tilde range:

- `5~7쪽 -> 오에서 칠쪽`
- `8∼12장 -> 팔에서 십이장`

Hyphen numeric range remains out of scope for canonical range owner:

- `12-15장 -> 12-15장`
- `1-2쪽 -> 1-2쪽`

## 9. Event Number Gate and Numeric Fallback

Event number policy is strict.

Event pass examples:

- `12.3 비상계엄 -> 십이삼 비상계엄`
- `12·3 비상계엄 -> 십이삼 비상계엄`
- `12.12 사태 -> 십이십이 사태`
- `4.19 혁명 -> 사일구 혁명`
- `5·18 민주화 운동 -> 오일팔 민주화 운동`
- `6.27 부동산대책 -> 육이칠 부동산대책`

Event fail fallback examples:

- `13.3 비상계엄 -> 십삼쩜삼 비상계엄`
- `12.32 사태 -> 십이쩜삼이 사태`
- `0.19 혁명 -> 영쩜일구 혁명`
- `4.0 혁명 -> 사쩜영 혁명`
- `14.35 대책 -> 십사쩜삼오 대책`
- `12.3수치 -> 십이쩜삼수치`
- `12·3수치 -> 십이 삼수치`
- `12.3-수치 -> 십이쩜삼-수치`
- `12·3-수치 -> 십이 삼-수치`

Immediate event keyword, supported date-like range, boundary, and spacing conditions must all pass.

## 10. Code Separator and Spaced Hyphen Decisions

Spaced hyphen numeric multi-block is not telephone-number inference. It reads each numeric block independently.

- `010 - 1234 - 5678 -> 공일공 천이백삼십사 오천육백칠십팔`
- `001 - 23 - 456 -> 공공일 이십삼 사백오십육`
- `0.5 - 1.2 - 3 -> 영쩜오 일쩜이 삼`

Mixed alnum code separator fallback applies within the policy-defined scope after dictionary/fixed lexical claims fail:

- `K-POP -> 케이팝`
- `A1-B2 -> 에이 일 비 이`
- `A1·B2 -> 에이 일 비 이`

Dictionary entries such as `K-POP` outrank code fallback. This record does not expand the dictionary beyond the current policy-defined entries.

## 11. Temperature and Bare `도`

Signed temperature is limited to explicit signed temperature/degree surfaces.

- `-2.5℃ -> 영하 이쩜오도`
- `-2.5℉ -> 화씨 영하 이쩜오도`
- `+3º -> 영상 삼도`

Bare Korean `도` does not trigger broad weather inference:

- `서울 -1.3도 -> 서울 마이너스 일쩜삼도`

The policy intentionally does not add `-1.3도 -> 영하 일쩜삼도` as a broad rule.

## 12. Signed temperature boundary clarification

- Clarified that signed temperature / signed degree owner may claim a directly attached `sign + number + degree/temperature symbol` surface after Korean text, whitespace, punctuation, delimiter, or start of text.
- Korean labels before the signed surface remain original Korean literal and are not rewritten.
- Canonical example: `온도-2.5℃ -> 온도영하 이쩜오도`.
- ASCII/code-like attached forms remain preserved: `A-2.5℃ -> A-2.5℃`, `x-2.5℉ -> x-2.5℉`.
- Partial rewrites such as `온도-2.5℃ -> 온도-이쩜오℃` are explicitly forbidden.

## 13. Retained Non-goals

The following remain out of scope unless separately approved in the canonical policy:

- global Unicode normalization
- fullwidth Latin/digit normalization
- broad language detection model
- unconditional or standalone score/ratio expansion such as bare `숫자:숫자 -> A대 B`
- bare signed Korean `도` weather inference
- arbitrary hyphen numeric range expansion outside approved `N-M + range-compatible unit` gates
- slash-side spacing support such as `1,000 KB / s`
- arbitrary unknown unit parsing

## 14. Test and Validation Requirements

Canonical tests must cover:

- preserve taxonomy and fallback routing
- general decimal vs event number
- middle-dot numeric vs event number
- date hyphen vs code hyphen
- phone number vs spaced hyphen numeric multi-block
- temperature vs bare Korean `도`
- `Hz/hz` vs unsafe alphabetic tail
- `K-POP` dictionary priority vs generic code separator
- Arabic `10월` date month reading
- decimal unit/suffix and KRW large-unit currency expansion

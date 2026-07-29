# TTS Preprocessor Policy Changelog

이 문서는 릴리스 로그가 아니라 현재 canonical policy로 정리된 주요 정책 변경과 결정 기록이다. 구현과 테스트 판단의 단일 원본은 `docs/TTS_Preprocessor_policy.md`이며, 이 문서는 왜 현재 정책이 그런 형태인지 추적하기 위한 보조 문서다.

## Context-aware LLM handoff

- 전면 활성화된 규칙 엔진이 의도적으로 남기는 raw 숫자+다의 단위를 후단
  LLM 프롬프트에 반영했다. 같은 문장/절의 의미 관계를 우선하고 일반적인
  표준 한국어 용례로 가장 자연스러운 native/Sino 읽기를 선택하도록
  정렬했다. 정책상 보호 대상이 아닌 숫자와 영문은 최종 `speech_text`에
  원문 표면으로 남기지 않는다.
- `분·번·점·조·대·부·동·호·판·단·등·척·장·권·편·층`과 `가지`의
  의미 대조, compact decimal `쩜`, malformed/protected atomic preserve,
  기존 canonical spacing을 활성 통합 프롬프트에 반영했다.
- 규칙 엔진이 확정한 `오분 뒤`, `삼번 버스`, `제 삼장` 등은 LLM이
  재판정하거나 spacing을 변경하지 않는 고정 결과로 명시했다.
- 1단계와 2단계 사이에 marker, candidate, decision log 또는 hidden
  metadata를 추가하지 않았다. LLM 요청은 계속 순수 `normalized_text`
  문자열만 사용하고, 규칙 출력은 LLM 없이 독립적으로 TTS 입력에 사용할
  수 있다.

## Full-activation transition cleanup

- 개선 엔진 전면 적용 후 사용되지 않던 source-debug compatibility
  fallback을 제거했다. packaged binary가 `--include-debug`를 지원하지
  않으면 source import로 우회하지 않고 stale binary 오류를 그대로 내며,
  배포 semantic gate에서 재빌드 대상으로 처리한다.
- production adapter에서 무시되던 `enable_prosody`와 런타임 호출자가
  없던 `transform_payload` wrapper를 제거했다. 현행 내부 facade는
  `transform_for_production(text, debug=False)` 하나다.
- counter threshold와 signed numeric core에 남아 있던 내부 backward
  alias를 제거하고 현행 이름인 `HYBRID_THRESHOLD_39_COUNTERS`,
  `sign_surface`를 직접 사용하도록 정렬했다.
- local Linux package/release CLI의 무시되는 version positional argument와
  비어 있던 legacy expectation audit fixture를 제거했다.
- rollout/shadow-mode 단계별 중복 테스트는 삭제하고 mode-less facade,
  stale-binary failure, API rollout-field rejection을
  `test_production_facade_isolation.py`의 현행 계약으로 통합했다.
- `engine.span_engine.shadow`, `ShadowUnit`, `shadow_logs`는 삭제하지
  않았다. 이 경로는 구·신 엔진 dual-run이 아니라 원문 source-span
  preservation 검증에 현재도 사용되는 safety invariant다.

## Live API semantic deployment gate

- 운영 API의 debug 결과에 새 `contextual_number_unit` owner와
  `contextual_decision_logs`가 없고 이전 owner만 관찰된 사례를 배포
  산출물 불일치로 판정했다. 동일 입력은 source runtime에서 canonical
  결과를 반환하므로 숫자·문맥 판정 구현 결함이 아니다.
- 배포 스크립트의 개별 probe 파일 allowlist를 제거하고
  `scripts/probes/` 전체를 canonical set으로 전송한다. 새 core probe가
  runner에는 등록되었지만 원격 buildsrc에는 누락되는 drift를 차단한다.
- dist/staging/published binary core probe에 더해 서버 시작 후 live API
  core probe를 cleanup 전 필수 gate로 추가했다. 이 단계는 실행 중인 API가
  방금 publish한 `TTS_PREPROCESSOR_BINARY`를 실제로 사용하며 source와
  동일한 문맥형·소수 canonical을 반환하는지 검증한다.
- 관찰된 비분리 공백 포함 혼합 문장을 canonical contextual probe로
  고정하여 native/Sino 의미 분리와 decimal 읽기를 한 요청에서 검증한다.
- score exact anchor에 허용된 조사가 결합된 `평점은 3점이었다`도
  `평점은 삼 점이었다`로 확정한다. anchor는 여전히 등록된 `평점`이고
  조사 철자는 변경하지 않는다.

## Decimal number-unit coverage and caret atomicity

- 기존 compact `쩜`과 source-exact fractional digit/trailing-zero canonical은
  그대로 유지한다. `이쩜 삼오` 같은 새 decimal 간격은 도입하지 않는다.
- valid decimal은 등록 simple/special unit, exact compound unit
  `Mbps·Gbps·rpm·fps·ppm·ppb·dBi`, 등록 counter, 승인된 contextual
  exact anchor에서 Sino decimal로 읽는다. `kHz`, `KB`, plain
  `10000.5kg`의 누락된 decimal eligibility를 공통 numeric reader 범위에
  맞췄다.
- contextual integer의 native/Sino 의미 판정은 유지하되 decimal 숫자
  자체는 Sino로 고정한다. 의미에 따라 attachment/spacing이 달라지는
  `번·부·단·등` 등은 exact anchor gate를 계속 사용하고 bare decimal은
  유보한다. `1.5가지`, `총 2.35번`, `책 2.35권`, `영화 2.35편`,
  `2.35층 회의실`을 새 canonical로 확정했다.
- valid decimal counter/contextual surface는 직접 붙은 `+`와 owner-local
  minus alias를 부호·숫자·단위 전체 claim 안에서
  `플러스`/`마이너스`로 읽는다. signed integer counter의
  UNSIGNED_ONLY 정책은 유지한다. `쯤·정도·꼴·당`은 exact attached
  decimal-counter tail로 허용한다.
- pH는 signed/unsigned valid integer, decimal, comma-decimal을 전체
  claim하고 문장 끝 마침표를 punctuation으로 분리한다. malformed
  comma/repeated-dot는 pH token 전체를 보존하여 부분 숫자 변환을 막는다.
- caret power 자동 registry 생성을 제거하고 natural exact length-unit
  allowlist `mm·cm·km·m`의 `^2`/`^3`만 읽는다. 비승인
  `alphabetic-unit^exponent` literal은 보존하면서 앞의 독립적인 valid
  numeric core만 읽고, exponent-only fallback은 차단한다.
- large-unit 뒤 비승인 delimiter `–—−－＋·`와 malformed caret numeric
  surface는 부분 변환 없이 원자적으로 보존한다.

## Contextual number-unit default activation

- 문맥형 숫자+단위 판정을 기본 mode-less transform에 즉시 활성화하기로
  결정했다. LLM OFF에서도 모호한 surface의 raw 숫자가 남을 수 있으며,
  별도 compatibility/rollout mode와 API rollout field는 도입하지 않는다.
- 내부 결과를 `confirmed`, `deferred`, `absolute_preserve`,
  `not_applicable`의 네 typed outcome으로 구분한다. confirmed/deferred
  claim은 모두 terminal이며 generic numeric suffix/counter/number
  fallback 재진입을 차단한다.
- 원문 preservation 검증용 `shadow_logs`의 의미는 유지한다. 의미 판정은
  별도의 debug-only `contextual_decision_logs`로 기록하며 일반 서비스
  문자열에는 판정, 후보, marker를 삽입하지 않는다.
- 기존 구체 owner와 renderer/spacing canonical을 우선한다. 보호 구간,
  날짜·시간·전화·통화·범위·분수·점수 관계·측정 단위 owner는 새
  contextual owner보다 먼저 claim한다.
- 첫 기능 owner로 `가지`를 추가했다. 1~99 native, 0/100+ Sino 정책과
  항상 한 칸인 counter spacing을 기존 renderer로 구현했다. 이후 valid
  decimal과 signed decimal은 위 decimal coverage 정책으로 확장했으며,
  signed integer/leading-zero/malformed/alphanumeric/ordinal 표면은
  계속 원자적으로 유보한다. 범위 owner는
  `3~4가지 -> 세 가지에서 네 가지`를 먼저 full-claim한다.
- `분`, `번`, `점`, `조`를 exact local anchor 기반 owner로 분리했다.
  특정 시간/소수 점수/금액·large-unit owner는 계속 먼저이며,
  사람 높임 수량·횟수·물품 수량·그룹 수량만 기존 native renderer로
  확정한다. bare/ambiguous와 unsupported numeric forms는 기본 출력에서
  source-exact로 남고 generic fallback 재진입을 차단한다.
- 기존의 모든 bare `N분`, `N번`, `N점`, 조사 결합 `N조`를 일괄
  Sino/native로 읽던 기대값은 supersede했다. 이는 즉시 유보 활성화에
  따른 승인된 canonical 변경이다.
- `대`는 기존 점수 관계와 `제N대`를 보존한 채 중앙 기계 registry,
  세대 exact noun/`째`, 10의 배수 연령대 exact noun을 분리했다.
  `3대 과제` 같은 초기 검토 주요 항목과 확장 검토 기계 명사는 제외했다.
  기존 unsigned integer 40+ threshold는 유지한다. 이후 exact anchor의
  valid decimal/signed decimal만 위 decimal coverage로 확장했고,
  signed integer/bare decimal/leading-zero/malformed/alphanumeric `대`는
  contextual deferred claim으로 유지한다.
- `부·동·호·판·단·등·척`을 문서/주소/등급 contextual batch로
  활성화했다. 순서·식별·등급·길이와 실제 복사본·건물·가구·경기·적층·
  조명·선박 수량을 exact noun/suffix/action 구조에서만 분리한다.
  bare 또는 한쪽 anchor만 있는 표현은 source-exact deferred claim이며,
  기존 주소·서수·범위 owner와 각 단위의 기존 spacing canonical이 우선한다.
- `장·권·편·층`을 수량/구조번호 충돌 batch로 활성화했다. 물품·책·작품
  direct noun과 장/권의 고정 번호 구조를 분리하고, `층`은 조사
  `에·에서`, `지하`, 등록 위치 명사에서만 location을 확정한다.
  이동·개수 가능성이 겹치는 층 표현과 모든 bare 표현은 유보한다.

- Allowed the approximate tail `께` only after a complete structured suffix
  clock containing minutes: `N시 N분`, `N분 N초`, or `N시 N분 N초`.
  Bare `N분께` and hour-only `N시께` remain preserve-first, and no
  honorific-person `N분` reading was added.
- Added `mixed_integer_atomic` as the fallback owner for complete valid
  Arabic-Hangul integer cores such as `6천5백`, `6천400`,
  `1천2백3십4`, `2만3천`, and `3천만5천`.
  Registered counter/currency suffix ownership still wins first. Safe attached
  Korean prose and sentence-punctuation boundaries are admitted. A trailing
  Arabic block is valid only when positive and smaller than its immediately
  preceding small unit; oversized blocks preserve instead of being
  reinterpreted. ASCII identifiers, URL/path/code protection, prefixed
  ordinals, leading-zero cores, malformed unit order, and partial numeric
  residue remain preserve-first.
- Added `mixed_decimal_atomic` ahead of generic decimal fallback so a valid
  mixed integer plus ordinary fractional part is consumed as one surface:
  `5천830.13 -> 오천팔백삼십쩜일삼`. This prevents generic decimal from
  converting only `830.13`. Fractional digits reuse the existing positional
  `쩜` reading, and original Korean numeric-unit provenance is retained.
  Invalid, leading-zero, or code-like mixed decimal tokens receive an atomic
  preserve claim to block the same partial fallback.
- Added longest-first hybrid counters `자녀`, `자리`, `자릿수`, and `자매`
  while retaining the existing `자루` policy. Values 1..39 use native/hybrid
  readings and 40+ use Sino readings.
- Kept `제N자` / `제 N자` out of the prefixed ordinal reading owner. They
  reuse the general Sino `N자` route and preserve the source gap before the
  number (`제3자 -> 제삼자`, `제 3자 -> 제 삼자`).
- Added contextual `N자` routing: name length uses `한/두/석/넉` only for
  exact 1..4 and ordinary hybrid forms for 13/14; password/ID/Korean/English
  character-count contexts use ordinary hybrid forms such as `세/네`; an
  independent `N자` remains attached Sino (`3자 회담 -> 삼자 회담`).
- Registered the traditional special determiners `냥·되·섬·자` with
  `3=석, 4=넉` and `돈·말·발·푼` with `3=서, 4=너`. Except for
  self-identifying `N냥`, collision-prone surfaces require bounded
  gold/weight, grain/volume, or length context, so ordinary lexical uses such
  as `4발표` and `3말했다` do not receive the special form. These additions
  are integer-only and do not expand the registered decimal-suffix policy.
  Attached `N냥` remains attached (`금요일 3냥 -> 금요일 석냥`).
- Extended the live case-sensitive SI unit pairs with `mW/MW`, `mV/MV`,
  `mPa/MPa`, and `mHz/MHz`. Lowercase `m` renders `밀리`, uppercase `M`
  renders `메가`, and valid integer/comma/decimal plus optional one-space
  numeric forms reuse the existing simple-unit owner.
- Added exact owner-local aliases `㎽ -> mW`, `㎷ -> mV`, `㎹ -> MV`, and
  `㎫ -> MPa`. Unicode provides no single-character `mPa` alias; `㎩` means
  `Pa` and remains unregistered. Exact uppercase `MPA` is deliberately not a
  unit alias and remains on the news/acronym path.
- Kept collision-prone automatic expansions closed: `ML` remains the existing
  milliliter alias, while `MA`, `MJ`, `Mm`, and `Mg` are not added because of
  acronym, identifier, chemical-symbol, or existing-policy ambiguity. Unit
  candidates now make acronym fallback yield only when a complete numeric
  unit surface exists, so `2.5 MV` is a unit while bare `MV` remains `엠브이`.
- Added owner-local Unicode compatibility aliases for alphabetic units already
  present in the live registry: `㎾`/`㎿`, `㎑`/`㎒`/`㎓`,
  `㎅`/`㎆`/`㎇`, `ℓ`, and `㎧`. The aliases reuse the same Korean readings
  as `kW`/`MW`, `kHz`/`MHz`/`GHz`, `KB`/`MB`/`GB`, `L`, and `m/s`
  without global NFKC normalization. Canonical examples include
  `55㎿ -> 오십오 메가와트` and `55㎧ -> 초속 오십오 미터`.
- Added atomic preservation for unregistered CJK compatibility unit symbols so
  inputs such as `55㎩`, `55㎺`, `55㎸`, and `55㎙` do not fall
  through to a partial number-only reading. Corrected the stale `㎙` meter
  claim: Unicode defines it as `fm` (femtometer), not plain meter. The later
  case-sensitive SI expansion above supersedes the earlier preservation of
  `㎽`, `㎷`, `㎹`, and `㎫`.
- Aligned the documented ASCII area aliases `m2`, `cm2`, and `km2` with the
  special-unit registry and added an explicit equivalence/protected-tail test
  matrix covering both newly added and already supported unit symbols. Also
  aligned the existing policy-declared `‰ -> 퍼밀` notation with the live
  registry and tests; it is a separate unit, not a percent-equivalent alias.
- Restricted specialized `시` and `시간` number readings to attached markers.
  A horizontal space before either marker delegates the numeric core to
  ordinary number policy: `3 시 -> 삼 시`, `3 시간 -> 삼 시간`, and
  `09 시 -> 09 시`. Attached suffix-clock zero is now valid:
  `0시` and `00시` both read `영 시`. Attached `시` otherwise keeps the
  native `1..12`, Sino `13..24`, and out-of-range preserve rules; attached
  `시간` keeps its separate duration policy.
- Superseded the earlier Batch 2 suffix-clock leading-zero preserve decision
  only for registered suffix-time `시`/`분`/`초`. These owners now remove
  integer-part leading zeros locally when their spacing gate admits the
  surface. Attached `시` uses its `0..24`
  clock-hour range and native/Sino split; `분`/`초` share one Sino reader
  without a digit-count or `00..59` limit. Canonical examples include
  `09시 -> 아홉 시`, `23분045초 -> 이십삼분 사십오초`, and
  `123분545초 -> 백이십삼분 오백사십오초`. Other leading-zero
  identifiers, counters, units, currency, and malformed/unsafe surfaces retain
  their existing atomic preserve policy; `시간` remains a separate duration
  rule.
- Extended suffix-clock ownership to compact and mixed-horizontal-spacing
  `N시N분`, `N시N분N초`, and `N분N초` compounds. The time owner now claims all
  numeric cores in the complete structure before generic suffix fallback,
  inserts a generated boundary space only where source spacing is absent, and
  keeps the clock-hour and Sino minute/second reading split while applying the
  registered suffix-time leading-zero rule above. Unsafe-tail and
  protected-context policy remain unchanged. Minute/second amounts reuse the
  standalone suffix reading without a `00..59` clock limit.
- Unified successfully claimed colon-time hour rendering with the existing
  clock-hour mapping: `00` reads `영시`, `01..12` use native Korean forms, and
  `13..24` use Sino-Korean forms. This corrects `02..09` strong leading-zero
  readings such as `09:30 -> 아홉시 삼십분` without expanding the existing
  strong/ambiguous admission gate, suffix-clock leading-zero preservation, or
  protected and higher-priority semantic contexts.
- Replaced the blanket compact large-unit `개` preserve with a registered-counter
  full-claim path. The counter scanner now reuses the large-unit integer core
  parser's end, complete value, and canonical reading, so `3만개`,
  `12만개입니다`, and `1만3천개다` follow the 100+ Sino counter policy while
  `개월` keeps longest-match/spaceless behavior. ASCII, slash, code-like,
  unregistered Hangul tails, leading-zero forms, and lexical `만개` remain
  preserve-first without partial numeric reentry.
- Added conditional dual-role acronym handling for `KB`: safe standalone and Korean-context forms read `케이비`, while existing simple/data-rate unit scanners retain `10KB`, `10 KB`, and `1,000KB/s`; `KB/s`, numeric-code-like tails, identifiers, and protected contexts preserve. The conditional entry is intentionally outside the exact managed dictionary so it cannot inherit managed numeric-code suffixes.
- Added full-claim `ampersand_acronym` for safe unspaced `UPPERCASE_BLOCK&UPPERCASE_BLOCK` surfaces. It reuses central letter readings and renders the original `&` span as `앤`; spaced, mixed-case, numeric, repeated-ampersand, code-like, and protected forms preserve. Base `Q&A` and `S&P` moved from fixed dictionary ownership to this structural owner, while `S&P500` and `S&P 500` remain finance-index full claims.
- Revised source-attached numeric `대`: valid unsigned numeric values 40 or greater now always use the Sino reading with reason `dae_counter_sino_threshold_40_plus`, while protected/structured, signed, leading-zero, malformed, ordinal, and full-claimed score surfaces keep precedence. Values below 40 retain the conservative context gate.
- Extended the centralized `대` quantity inventory with `자동차` and added the bounded topic/quantity bridge `registered noun + 은/는/이/가 + space + 모두/총 + space + N대`. The bridge does not cross punctuation and is consulted before a keywordless independent score-pair interpretation; explicit score/game context remains score-owned. Explicit quantity `N대 M` uses `numeric_dae_quantity_sequence` rather than the score owner, while context-free spaced threshold `40대 M` is split into threshold counter plus ordinary number and compact `40대3` retains the structured relation owner.
- Routed documents containing fenced code through the whole-input protected-span path so the language line gate cannot re-enter `KB`, ampersand acronyms, or threshold `N대` inside a fence.

- Audited arithmetic routing: standalone compact `3+4` was retained by the no-Hangul path, spaced expressions entered core and only their independent number/decimal operands converted, and assignments such as `3+4=7` overlapped the broad `_MATH_ASSIGNMENT_RE` protected claim. `A+B`, `x-y=3`, `a+=1`, and `C++17` already used the protected/code-like route.
- Added `basic_arithmetic_expression` / `BASIC_ARITHMETIC_EXPRESSION_SURFACE` with reason `basic_arithmetic_expression_full_consume_gate`. A state parser distinguishes operand-position unary signs from binary `+/-`, supports `+`, `-`, `×`, lower-case operand-delimited `x`, `÷`, and at most one `=`, and reads chains in source order without calculation. `X`, `*`, and binary `/` remain unsupported.
- Reused the shared `SignedNumericCore` parser/renderer for integer, comma, decimal, comma-decimal and signed operands. Extracted `parse_fraction_operand_at` from the existing fraction policy so arithmetic validation and rendering reuse the same denominator-zero, sign, comma, and fraction-reading contract; fraction is attempted before numeric parsing.
- Added strict no-Hangul arithmetic admission before the general code-like bypass. Broad math preserve now yields only an exact numeric/fraction-only expression; URL/path/email/JSON/backtick/bracket and variable/code expressions retain priority. Registered managed code (`version-2`), date, time, phone, restricted range, duration, multiplier, and unit-contamination owners remain ahead of arithmetic.
- Added equality `은/는` as an owner-local generated reading selected from the jongseong of the rendered last left operand. This is separate from source-particle correction; accepted operator boundaries render with one canonical generated space.
- Audited the arithmetic rollout against the existing hyphen matrix. The rollout had reclassified bare `1-2`/`3-2` and pure `10-3-2` as subtraction, accepted asymmetric minus spacing, and allowed arithmetic invalid-preserve to preempt leading-zero/long two-block code readings.
- Restored bare compact `N-N` atomic preserve and pure compact hyphen chains to the existing hyphen-digit/code route. Moved the existing hyphen digit/code claim ahead of arithmetic and restored generic two-block leading-zero or 4+-digit block reading with reason `two_block_numeric_code_separator_route`; the established supported-range short hyphen year-month boundary (`2025-01`) remains source-exact and is excluded from that generic code route.
- Restricted ordinary subtraction to exact spaced `operand - operand`, while retaining compact binary minus only inside a full-consumed expression containing another supported operator or exactly one valid equality. Canonicals include `3-2+1 -> 삼 빼기 이 더하기 일`, `2×4-3 -> 이 곱하기 사 빼기 삼`, and `4-3=1 -> 사 빼기 삼은 일`.
- Preserved phone/date/range/managed-code/protected priority and no-partial-fallback. Added source-exact Hangul-left provenance for the existing two-block code owner so `가-3.14 -> 가 삼쩜일사` passes Shadow Validation rather than triggering whole-input recovery.
- Added atomic `INVALID_BASIC_ARITHMETIC_EXPRESSION_PRESERVE_SURFACE` with reason `invalid_basic_arithmetic_expression_preserve` before standalone fraction/signed/decimal/number fallback. Malformed operands, repeated operators, unsupported operators/operands and incomplete expressions no longer produce partial readings. Existing invalid-signed, phone/emergency/hyphen-digit, range and protected preserves remain more specific.
- Added a narrow protected-literal boundary for unsupported parenthesized numeric arithmetic and numeric-argument function tokens. `(3+4)×2` and `sqrt(4)` now preserve atomically inside Korean sentences and bypass only final parenthesis elision; ordinary parenthesis presentation such as `문장(임시)` and `(+3°)` is unchanged.
- Added operand/operator RenderPieces with generated provenance and exact source spans, parser metadata (`operand_kinds`, `operator_kinds`, `has_equality`), internal-whitespace Shadow Validation coverage, standalone/no-Hangul regressions, protected and structured-owner regressions, and a Korean mixed-expression E2E test.

- Audited signed numeric routing before refactor. Standalone +N/-N was owned by signed_number with reason signed_number_surface; unit, currency, percent-point, large-unit, fraction, colon/range/score, temperature/degree, and phone each carried owner-local sign handling. The existing range NumericDelimitedNumber parser was the closest common core, while signed.py capped its integer reader at 9,999. That cap left -12,345 unclaimed and allowed -1,000,000.0 to lose only its sign through internal decimal fallback.
- Added the shared SignedNumericCore/NumericCore parser, SignKind and SignProfile, and centralized SignedOwnerPolicy metadata. The parser reuses canonical integer/comma validation and exact fractional digit reading; DEFAULT maps to 플러스/마이너스, TEMPERATURE maps to 영상/영하, and UNSIGNED_ONLY/OWNER_CUSTOM prevent semantic broadening. Range keeps a thin compatibility wrapper and its existing public raw sign surface.
- Connected the common validation/profile renderer to standalone signed number, simple/special unit, currency, percent-point, large-unit, minus-only slash fraction, numeric-delimited range/colon paths, and Korean 대 score-pair operands. Structure detection, owner reasons, spacing, templates, operand restrictions, and phone digit-by-digit rendering remain owner-local. Signed compound slash units and all counters were not enabled.
- Restored full signed comma coverage: -12,345 now full-claims as signed_number and reads 마이너스 만이천삼백사십오; -1,000,000.0 now full-claims and reads 마이너스 백만쩜영. Fractional trailing zero remains source-exact 영.
- Added atomic invalid_signed_numeric_preserve before generic decimal/number fallback with surface INVALID_OR_UNSUPPORTED_SIGNED_NUMERIC_PRESERVE_SURFACE and reason invalid_or_unsupported_signed_numeric_surface_preserve. Repeated/conflicting signs, signed leading zero, empty integer/fraction, invalid comma grouping, unsupported signed counters, and unsupported signed suffixes no longer permit partial numeric reentry. Existing structured invalid and protected/code-like owners retain priority.
- Kept temperature/angle semantics unchanged: Celsius/Fahrenheit and temperature-like bare º use 영상/영하, Fahrenheit retains 화씨 + sign + number + 도, and angle ° uses 플러스/마이너스. Minus aliases remain owner-local rather than globally normalized.
- Kept colon/score/range/fraction/phone output and owner routing unchanged, including tilde endpoint signs, minus-only fraction support, international-phone digit-by-digit reading, and unsupported hyphen/en-dash signed range preservation.
- Kept counter policy closed: +3대, -3대, 차량 증감 +3대, +2명, and -3개 preserve atomically. Existing unsigned contextual 대 and ambiguous_numeric_dae_preserve behavior remains unchanged.
- Added parser trace metadata for signed-aware candidates where applicable: sign_profile, numeric_form, and original sign_surface, while keeping existing owner/reason/span and RenderPiece provenance contracts.

- Audited bare numeric `대`: integer `N대` was previously shape-claimed by `counter_noun` with `counter_policy_gate`, decimal `N.N대` by `decimal_registered_suffix`, and neither path consulted a left quantity noun. `N대M` and `제N대` were already separate `korean_da_score_pair` and prefixed `numeric_suffix` owners. No central `대` target-noun registry existed.
- Added centralized `REGISTERED_DAE_COUNTER_NOUNS` metadata with the exact minimal inventory `차량, 장비, 버스, 서버, 카메라`. Attached integer/decimal `대` delegates to the existing counter renderer only for an immediately preceding registered noun or the narrow adjacent `registered noun + N대 + N대{tail}` continuation. No scanner-local noun set, particle bridge, wide context window, verb allowlist, or semantic inference was added.
- Added atomic `ambiguous_numeric_dae_preserve` / `AMBIGUOUS_NUMERIC_DAE_PRESERVE_SURFACE` with reason `no_existing_owner_and_no_explicit_counter_context`. Bare, particle/ending-tailed, semantic-ambiguity, and bare decimal `대` surfaces preserve source-exact and block generic number, decimal, registered suffix, and `korean_numeric_chain` reentry.
- Kept protected/code-like precedence, all existing `N대M` supported forms/operand/rendering behavior, `제N대` owner/reason/spacing, other counters, and malformed owner preserves. Canonical examples now include `3대 -> 3대`, `20대가 -> 20대가`, `장비 1.5대 -> 장비 일쩜오 대`, and `1.5대 -> 1.5대`.
- Aligned two-block dotted routing after policy/code audit: the former `short_dotted_year_month_preserve` was shape-only (`4-digit.1-or-2-digit`) and used neither a year/month range check nor Korean left/right context. It is retired; valid bare two-block dotted surfaces now use `decimal`, including `12.12`, `7443.28`, `2025.01`, and `2025.13`.
- Kept the established preserve boundaries for `05.03` and leading-zero dotted forms, and made empty-left/duplicate-dot forms (`.5`, `3..140`, `25..50`) explicit atomic `malformed_dotted_numeric_preserve` claims so generic number fallback cannot partially rewrite them. Sentence-final `N.` remains number plus punctuation; owner-attached empty-right forms preserve through their structured owner. Protected URL/path/email/file/version/code-like surfaces and all three-or-more-block dotted date/code routing remain unchanged. Event keyword success still owns event readings before decimal fallback.
- Added structured compact large-unit final decimals under `large_unit_atomic` with reason `large_unit_structured_decimal_surface`, full-consume/no-partial-fallback guards, compact rendering, fractional zero as `영`, and source provenance split between generated Arabic readings and original Korean large units/tails.
- Added `korean_numeric_chain` after specific/administrative owners and before generic number fallback. It reads integer cores inside narrowly eligible Hangul-only tokens without registering arbitrary Hangul suffix semantics or inserting spaces. ASCII/code-like and partial-residue tokens, Korean numeric-unit structures, registered suffix/counter blocks, and ordinary digit+grammar tails remain on their existing owners/preserve paths.
- Canonical regression sentence now covers `다우존스30`, ordinary dotted decimals, `5만1839.26`, `2만5508.07`, `5극3특`, `5극 3특`, and the atomic-preserve bare `3대` owner.

- Promoted four explicit span-default outputs to canonical policy: preserve the
  full leading-zero counter surface (`01명`) and, at that time, the
  leading-zero suffix clock-hour surface (`09시`; superseded by the current
  suffix-time override), attach an immediate approximate `여` to a compact
  large-unit reading (`1만3천여 명 -> 일만삼천여 명`), and read both sides of
  a spaced middle-dot independently while preserving its boundary
  (`123 · 456 -> 백이십삼 · 사백오십육`).
- Reconciled stale `2~5시` summary examples with the existing clock-hour range
  rule and span output: `두 시에서 다섯 시`.
- Clarified malformed numeric follow-up taxonomy in the numeric matrix. The
  leading-zero decimal family now preserves without partial numeric reentry;
  signed variants additionally use the unified invalid-signed atomic preserve.
  Segmented malformed numeric reading and file/version/code protection remain
  separate design tracks.
- Hardened news attached-surface policy notes for valid decimal/comma decimal
  plus original `로`/`으로`, managed `KTX-이음` acronym-Hangul hyphen compounds,
  and the narrow `N시뉴스` broadcast title pattern without broad fallback,
  hyphen rewrite, or particle correction expansion.
- Clarified `H시뉴스` as a broadcast title core-marker pattern rather than a
  finite post-`뉴스` tail inventory: the hour may be generated while `시뉴스`
  and complete Hangul tails remain original Korean, with ASCII/identifier-like
  tails and protected contexts preserve-first.
- Added owner-local dash-like signed numeric aliases for signed numeric-aware
  owners under full-claim conditions, without global dash normalization and
  without changing range, connector, sentence dash, invalid, or protected
  preserve behavior.
- Clarified paragraph debug contract: `normalized_text` is the final paragraph-shaped TTS output; `render_pieces` may remain a pre-paragraph debug/provenance stream; `render_pieces` parity is not currently required.
- Corrected the current canonical managed lexicon reading for `OECD` to
  `오이씨디`; span policy, lexicon, and tests should use this reading.
- Added managed lexicon drift guardrails for span production: canonical managed
  lexicon/fixed dictionary entries must be present in the span lexicon, claim
  before uppercase acronym fallback, and finance index fixed terms may use
  whitelist-based numeric suffix full-claim while broad acronym+number fallback
  and protected-context reentry remain prohibited.
- Split managed dictionary inventory into
  `docs/TTS_Preprocessor_managed_dictionary.md`, added
  current/current_with_condition/pending/conflict/future/historical-only labels, and
  recorded that this pass changes documentation only, not production code.
- Connected the managed dictionary `current` inventory to span production by
  adding the missing `GUI` and `Wi-Fi` fixed entries, without promoting pending,
  conflict, future, or historical-only dictionary candidates.
- Canonicalized managed dictionary inventory into the dedicated managed
  dictionary policy, removed duplicate fixed lexical inventory tables from the
  main policy, resolved `DOCX` to `디오씨엑스`, and promoted the user-approved
  exact current entries and exact slash compounds to span production/test
  parity without adding broad acronym, slash, mixed-case, or frequency fallback.
- Added spaced slash boundary handling for Korean-eligible text: ASCII-space-wrapped `/` may split independent transform segments while raw-preserving the delimiter and avoiding protected spans, no-space slash policies, no-Hangul expansion, and cross-delimiter context sharing.

---

## 0. Latest Addendum: Numeric Surface Broad Reading

- Added `scripts/probes/decimal_fractional_zero.py` using the shared
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
  compound unit, historical, and digit-sequence owner routes.
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
- Superseded the former rollout entrypoint; the official production source entrypoint is now `engine.main.transform(text)`.
- Documented binary/API runtime routing through `bin/build_binary_entrypoint.py` and the packaged PyInstaller binary rather than deployed source imports.
- Clarified that `check_server.sh` is a health/sanity check and semantic regression coverage belongs in source/main/binary/API probes and parity tests.
- Expanded large-unit numeric input coverage for comma integer and signed decimal surfaces.
- Added mixed Arabic-Hangul large-unit full-claim handling.
- Added mixed Korean-Arabic numeric counter full-claim handling for registered
  counter suffixes such as `6천400명`, while blocking broad numeric fallback from
  producing partial outputs such as `육천400명`.
- Added narrow `N년간` year-period handling as duration/year owner behavior,
  preserving the exact original `년간` suffix and avoiding broad `N년+Hangul`
  expansion.
- Added Hangul-tail spacing and English-tail literal retention behavior for large-unit numeric surfaces.
- Clarified large-unit English-tail behavior: valid numeric-large-unit cores are read and following English tails are kept literally without inserted spacing.
- Preserved code-like English-prefix large-unit surfaces.
- Added API/runtime path coverage for standalone large-unit numeric cores and reused the large-unit scanner in the historical pipeline to block partial fallback.
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

- `docs/TTS_Preprocessor_policy.md`를 현재 canonical policy로 둔다.
- `docs/TTS_Preprocessor_policy_changelog.md`는 결정 기록으로만 사용한다.
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
- fullwidth Latin meter unit alias: `ｍ` is owner-local for unit and
  range-compatible unit owners; this is not global fullwidth Latin
  normalization.

명시 non-goal:

- broad dash alias such as en dash/em dash
- fullwidth Latin/digit normalization
- NFD Hangul eligibility
- middle-dot alias expansion beyond policy-defined forms

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
- `mHz`, `kHz`, `MHz`, and `GHz/Ghz/ghz` are registered
  case-sensitive frequency units when a numeric prefix exists.
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

Korean marker dates `YYYY년 M월 D일`, `YYYY년 M월`, and `M월 D일` accept either source whitespace or direct attachment between components. Directly attached components receive one generated ASCII space before the following reading while the original `년`, `월`, and `일` markers remain unchanged.

Examples:

- `6월 -> 유월`
- `10월 -> 시월`
- `6월19일 -> 유월 십구일`
- `2026년6월19일 -> 이천이십육년 유월 십구일`
- `2026년6월 -> 이천이십육년 유월`
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

- `010 - 1234 - 5678 -> 공일공 - 천이백삼십사 - 오천육백칠십팔`
- `001 - 23 - 456 -> 공공일 - 이십삼 - 사백오십육`
- `0.5 - 1.2 - 3 -> 영쩜오 - 일쩜이 - 삼`

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

## 15. Policy Alignment Batch 1

- Promoted the current exact standalone time readings to canonical policy:
  `0:00 -> 영시`, `24:00 -> 이십사시`.
- Changed only the declared spaced-hyphen multi-block output by retaining its
  exact source separator: `1 - 2 - 3 -> 일 - 이 - 삼`.
- Added caret power for numeric-prefix ASCII-letter units. The later decimal
  coverage/caret atomicity decision narrows this to the natural exact
  `mm·cm·km·m` allowlist:
  `^2 -> 제곱<단위>`, `^3 -> 세제곱<단위>`.
- Caret power requires no gap between unit and exponent, and the exponent must
  end the input or be followed by whitespace/Hangul. Numeric/ASCII-letter tails
  remain on the pre-existing processing path.
- Narrowed Hangul internal-exception recovery from whole sentence preservation
  to source-segment recovery: only the final failed segment is preserved.
- Whole-input original preservation remains limited to no-Hangul global bypass
  and whole-input absolute-preserve input.

Allowed output diffs:

- `1 - 2 - 3: 일 이 삼 -> 일 - 이 - 삼`
- `1 - 2 - 3 수치: 일 이 삼 수치 -> 일 - 이 - 삼 수치`
- `010 - 1234 - 5678: 공일공 천이백삼십사 오천육백칠십팔 -> 공일공 - 천이백삼십사 - 오천육백칠십팔`
- `001 - 23 - 456: 공공일 이십삼 사백오십육 -> 공공일 - 이십삼 - 사백오십육`
- `0.5 - 1.2 - 3: 영쩜오 일쩜이 삼 -> 영쩜오 - 일쩜이 - 삼`
- `2025 - 01 - 03: 이천이십오 공일 공삼 -> 이천이십오 - 공일 - 공삼`
- `공백 포함 표기 010 - 1234 - 5678도 함께 적는다.: 공백 포함 표기 공일공 천이백삼십사 오천육백칠십팔도 함께 적는다. -> 공백 포함 표기 공일공 - 천이백삼십사 - 오천육백칠십팔도 함께 적는다.`
- `7m^3: 칠 미터^삼 -> 칠 세제곱미터`

## 16. Policy Alignment Batch 2

- Promoted 14 leading-zero and owner-override audit rows to current span canonical behavior.
- Standalone `01`, `003`, `007`, and `0001` preserve source bytes; Digit Mode is not a standalone fallback.
- Identifier numeric payloads preserve, while a registered acronym and independent date owner may still transform.
- Leading-zero counter surfaces preserve instead of selecting native/hybrid counter reading.
- Unit and currency owners full-claim invalid leading-zero amounts as preserve and block partial numeric fallback.
- Historical Batch 2 decision: suffix-clock `09시` and `07시 05분` used
  `TIME_PRESERVE_SURFACE`. This item is superseded by the current registered
  suffix-time leading-zero override above.
- Registered date marker and phone owners remain narrow exceptions to the preserve matrix.
- No runtime implementation or normal output changed in this batch.
- The 14 resolved rows moved from the deferred historical audit into owning policy tests and the Batch 2 stable fixture.

Allowed output diffs: none.

## 17. Policy Alignment Batch 3

- Promoted 16 time, colon, suffix-clock, and phonetic audit rows to current span canonical behavior.
- Canonical suffix-clock `N시` output retains generated spacing before the original `시`, including afternoon/night context and attached Korean particles.
- Successful `HH:MM` time claims omit an exact zero-minute component; valid `24:MM` remains strong time.
- A one-digit minute is not HH:MM. Valid non-time-like two-block colon forms use the semantic-pair owner and `대` rendering.
- Bare and explicit ratio/score examples such as `16:9`, `한국 vs 일본 3:2`, and `화면 비율 16:9` use the same semantic-pair rendering.
- `H:MM:SS` and `HH:MM:SS` timecode-like surfaces preserve atomically in standalone and ordinary Korean sentence contexts.
- Phonetic processing does not remove suffix-clock owner spacing.
- No runtime implementation or normal output changed in this batch.
- The 16 resolved rows moved from the deferred historical audit into owning policy and trace tests and the Batch 3 stable fixture.

Allowed output diffs: none.

## 18. Policy Alignment Batch 4

- Resolved eight middle-dot, leading-zero, and dotted-event audit rows.
- A short first block of a contiguous middle-dot surface uses numeric value reading; later blocks retain digit-sequence reading with `영` for zero.
- Leading-zero suffix-clock and invalid unit surfaces preserve without leaking a partial middle-dot reading.
- Strong one-digit-right dotted events such as `12.3 비상계엄` use EVENT_SURFACE.
- Event and decimal surfaces in the same sentence are claimed independently.
- Spaced middle-dot operands normalize independently while the exact separator and spaces remain source-preserved.
- One exact runtime output transition fixes the asymmetric right-gap boundary.

Allowed output diff:

- `12· 3: 12· 삼 -> 십이· 삼`

## 19. Policy Alignment Batch 5

- Promoted five protected-bracket, signed-currency, decimal-precision, and embedded-code audit rows to current span canonical behavior.
- Square-bracket interiors are absolute preserve and block currency reentry; only the bracket delimiters are removed at presentation.
- Registered currency markers accept signed decimal-aware numeric amounts, including `$-10`.
- Ordinary decimal fractional digits have no system-level length limit and every zero remains explicit.
- `A112` is an atomic single-letter alnum code, not an emergency-number or partial general-number surface.
- Bracket and later compound-unit claims remain independent in one sentence.
- No runtime implementation or normal output changed in this batch.
- `tests/fixtures/batch5_allowed_output_diffs.json` records five stable decisions and zero allowed diffs.

Allowed output diffs: none.

## 20. Policy Alignment Batch 6

- Promoted six large-number, ordinal, approximate-marker, and counter audit rows to current span canonical behavior.
- Ordinary number width ends at `경`; unsupported `해`-width no-Hangul input preserves exactly and Hangul input recovery remains segment-local.
- Prefixed ordinals generate canonical spacing after `제`, and compact `여` remains attached to the generated number reading.
- Valid comma decimals use compact ordinary integer rendering; emergency and counter claims remain independent and counter spacing is retained.
- No runtime implementation or normal output changed in this batch.
- `tests/fixtures/batch6_allowed_output_diffs.json` records six stable decisions and zero allowed diffs.

Allowed output diffs: none.

## 21. Policy Alignment Batch 7

- Promoted five conservative prosody and typed-surface interaction rows to current span canonical behavior.
- Long topic length plus a frame phrase does not license a broad production comma.
- Sentence-initial `한편` is context-gated and is not an unconditional leading-comma connector.
- Valid two-clause `-지만` boundaries use `prosody_extra` and emit source-mapped `GENERATED_PUNCT` without reopening numeric or lexical claims.
- No runtime implementation or normal output changed in this batch.
- `tests/fixtures/batch7_allowed_output_diffs.json` records five stable decisions and zero allowed diffs.

Allowed output diffs: none.

## 22. Policy Alignment Batch 8

- Promoted six restricted hyphen range, lexical middle-dot/K-prefix, and Unicode shared-month range rows to current span canonical behavior.
- `12-15장` belongs to the registered restricted range owner; generic and unsafe two-block hyphens remain preserve.
- Lexical middle dots remain source-exact while safe adjacent acronym/dictionary claims render independently.
- K-Hangul lexical owners and the K-POP dictionary entry retain precedence over generic separator fallback.
- `~`, `～`, `∼`, and `〜` share the owner-local month range rule and apply `월` reading to both operands.
- No runtime implementation or normal output changed in this batch.
- `tests/fixtures/batch8_allowed_output_diffs.json` records six stable decisions and zero allowed diffs.
- The deferred historical policy audit is now an exact empty JSON array.

Allowed output diffs: none.

## 23. Megawatt and Power-unit Alignment

- Aligned the implemented simple-unit registry with the existing power-unit
  policy inventory: `W`, `kW`, `MW`, `Wh`, `kWh`, and `MWh` require a numeric
  prefix and use the ordinary integer/comma/decimal unit reader.
- Added `MW -> 메가와트` and `MWh -> 메가와트시` while retaining the existing
  `MHz`, `MB`, `Mbps`, and `MB/s` `메가~` readings.
- Kept the prefix case-sensitive. `ML` remains the established milliliter alias;
  at that phase `MV`, `MA`, `MJ`, `MPa`, `Mm`, and `Mg` remained unsupported.
  The current case-sensitive SI expansion later enabled `MV` and `MPa`.
- Registered power units accept attached or one-ASCII-space numeric forms.
  Alphabetic unsafe tails preserve atomically without partial number fallback.
- Bare `MW` is blocked from generic acronym spelling and preserves because the
  unit policy requires a numeric prefix.

Allowed output diffs:

- `1W: 1W -> 일 와트`
- `1kW: 1kW -> 일 킬로와트`
- `1MW: 1MW -> 일 메가와트`
- `1Wh: 1Wh -> 일 와트시`
- `1MWh: 1MWh -> 일 메가와트시`

# TTS Preprocessor Numeric Matrix Policy

## 1. Purpose

This document audits the current numeric matrix for the span-default production
path. It records canonical behavior, intended guard boundaries, and open policy
decisions for the span-default production path.

The goal is to keep common standalone numeric parsing separate from
owner-attached numeric parsing. Owner-specific exceptions must full-claim their
surface or preserve it; they must not rely on broad internal digit fallback.

Contextual number-unit owners are an owner-attached exception. A supported
positive integer or valid decimal plus an approved exact anchor is confirmed
through the existing number/counter renderer. Decimal numeric cores always use
the existing compact Sino `쩜` renderer; the contextual decision still owns
meaning-specific unit attachment and spacing. A recognized ambiguous or malformed
number-unit surface is deferred source-exact and terminally claimed; its numeric
core must not re-enter numeric suffix, counter, decimal, signed-number, or
general-number fallback. This default behavior has no rollout mode.

## 2. Official production validation path

The official production source validation path is:

```text
engine.main.transform(text)
```

The API runtime reaches the same transform through the packaged PyInstaller
binary:

```text
api.server -> api.binary_runtime -> TTS_PREPROCESSOR_BINARY
-> packaged binary -> bin/build_binary_entrypoint.py
-> engine.main.transform(text)
```

## 3. Common standalone numeric matrix

Current standalone valid forms:

| Surface | Current output | Policy note |
|---|---|---|
| `1` | `일` | valid integer |
| `+1` | `플러스 일` | signed number owner |
| `-1` | `마이너스 일` | signed number owner |
| `1000` | `천` | valid integer |
| `1,000` | `천` | valid comma integer |
| `+1,000` | `플러스 천` | signed comma integer |
| `-1,000` | `마이너스 천` | signed comma integer |
| `1.5` | `일쩜오` | unsigned decimal |
| `+1.5` | `플러스 일쩜오` | signed decimal |
| `-1.5` | `마이너스 일쩜오` | signed decimal |
| `–1.5` | `마이너스 일쩜오` | owner-local dash-like signed numeric alias; not global dash normalization |
| `0.05` | `영쩜영오` | unsigned decimal |
| `+0.05` | `플러스 영쩜영오` | signed decimal |
| `-0.05` | `마이너스 영쩜영오` | signed decimal |
| `12.12` | `십이쩜일이` | valid bare two-block dotted decimal |
| `307.16` | `삼백칠쩜일육` | valid bare two-block dotted decimal |
| `7443.28` | `칠천사백사십삼쩜이팔` | four-digit first block alone is not a year-month gate |
| `2025.01` | `이천이십오쩜영일` | no shape-only short year-month preserve |
| `2025.13` | `이천이십오쩜일삼` | ordinary decimal; month-range inference is not used |
| `25.50` | `이십오쩜오영` | unsigned standalone decimal trailing zero uses `영` |
| `+25.50` | `플러스 이십오쩜오영` | signed standalone decimal trailing zero uses `영` |
| `-25.50` | `마이너스 이십오쩜오영` | signed standalone decimal trailing zero uses `영` |
| `1,000.50` | `천쩜오영` | valid unsigned comma decimal |
| `+1,000.50` | `플러스 천쩜오영` | signed comma decimal |
| `-2,500.75` | `마이너스 이천오백쩜칠오` | signed comma decimal |

### Unified signed owner matrix

All rows below reuse the common signed numeric core unless the owner-specific
reader is explicitly named. Owner support remains opt-in and full-consume.

| Owner type | Plus | Minus | Numeric reader | Exception / limit |
|---|---|---|---|---|
| standalone number | 플러스 | 마이너스 | Sino integer/decimal | protected and math/code excluded |
| simple/special unit | 플러스 | 마이너스 | Sino integer/decimal | registered unit and existing spacing must full-claim |
| compound slash unit | preserve | preserve | existing unsigned template only | signed support is not expanded |
| currency | 플러스 | 마이너스 | Sino integer/decimal | existing prefix/suffix marker and sign placement only |
| percent | 플러스 | 마이너스 | Sino integer/decimal | existing percent unit owner |
| percent-point | 플러스 | 마이너스 | Sino or existing fraction reader | %p/%P canonical retained |
| large-unit | 플러스 | 마이너스 | Sino integer/decimal | registered 만/억/조/경 owner |
| slash fraction | existing support only | 마이너스 | fraction canonical | no plus broadening; existing minus aliases only |
| colon / score | per operand 플러스 | per operand 마이너스 | existing operand reader | structure and spacing owner unchanged |
| tilde range | per endpoint 플러스 | per endpoint 마이너스 | Sino integer/decimal | hyphen/en-dash range not expanded |
| Celsius / Fahrenheit | 영상 | 영하 | Sino integer/decimal | temperature owner precedes unit/general number |
| angle degree ° | 플러스 | 마이너스 | Sino integer/decimal | bare º remains temperature-like |
| international phone | 플러스 | owner policy | digit-by-digit | never use ordinary integer reader |
| counter | valid decimal full-claim only | valid decimal full-claim only | Sino decimal; integer counter renderer unchanged | signed integer counter remains prohibited |
| ambiguous signed 대 | preserve | preserve | none | atomic invalid/unsupported signed preserve |
| contextual number-unit | valid decimal under exact anchor | valid decimal under exact anchor | integer uses meaning-specific renderer; decimal uses Sino | ambiguous bare surface still defers; debug decision log is separate from output |

`가지` is the first always-count contextual unit: integer 1..99 uses the
existing native counter renderer, integer 0 and 100+ use the existing
Sino/large-integer path, and valid decimal uses ordinary Sino decimal. The
counter gap is one space. Range owns the full shared-suffix surface before
`가지`; signed integers, leading-zero, malformed-comma, alphanumeric, and
ordinal `가지` surfaces are deferred atomically. A valid signed decimal may be
claimed as one surface.

`분`, `번`, `점`, and `조` use exact meaning anchors. Specific clock/duration,
decimal-score, currency/large-unit, range, and score-relation owners still win.
Without an approved anchor, a recognized integer surface is deferred even when
the previous generic owner would have emitted a Sino/counter reading.

`대` keeps score-pair and ordinal precedence, the existing central machine
registry, and the existing unsigned integer 40+ threshold. Generation and
10-multiple age-band anchors select Sino reading; low bare/major-item surfaces
defer. Valid decimal uses Sino reading only under an approved exact anchor.
Signed integer, leading-zero, malformed-comma, alphanumeric, bare decimal, and
decimal age-band surfaces defer.

`부`, `동`, `호`, `판`, `단`, `등`, and `척` split sequence/identifier/
grade meanings from physical counts only through the canonical exact
noun/suffix/action registries. Existing ordinal, address, and range owners keep
precedence. Bare and malformed surfaces are atomically deferred. Sino
`부·단·등` keeps source attachment, Sino `동·호·판·척` uses the existing
counter gap, and every native count uses one counter gap.

`장`, `권`, and `편` split registered item/book/work counts from fixed
chapter/volume/part structures. `층` confirms only exact location particles,
`지하`, or registered location nouns; movement and physical-count ambiguity
defer. Valid decimal uses Sino reading under the same exact anchors while bare
decimal remains deferred. Ordinal and range owners remain earlier than all
four contextual decisions.

Common valid forms are integer, comma integer, decimal, and comma decimal.
Fractional source digits and trailing zero are exact; comma is validation-only.
The parser records semantic sign_kind separately from the source sign_surface.
DEFAULT renders 플러스/마이너스, TEMPERATURE renders 영상/영하, and
UNSIGNED_ONLY prevents inference by the common renderer.

The default/unit/temperature/degree/percent-point minus-alias inventory remains
owner-local: -, −, －, –, —, ‒, ‑. Currency, large-unit, colon/score, and tilde
operands retain ASCII - only; slash fraction retains -, −, －. No global dash
normalization or plus-like alias expansion is permitted.

Malformed or unsupported direct-sign tokens are claimed atomically by
invalid_signed_numeric_preserve after supported structured owners and before
generic decimal/number fallback. Canonical reason:
invalid_or_unsupported_signed_numeric_surface_preserve. Examples include
+01, -.5, +1., ++1, +1,00, +3대, -3대, and unsupported +10km/h. Existing
structured preserve owners still win for malformed unit/currency/percent
surfaces. Protected/code-like owners always win first.

Valid bare two-block dotted numbers default to the ordinary decimal owner after
specific event/protected owners fail. A `4-digit.1-or-2-digit` shape is not by
itself a year-month context gate; the current canonical policy and implementation
have no Korean left/right context gate for short dotted year-month. Event keyword
success still wins (`12.12 사태 -> 십이십이 사태`), while `05.03` retains its
existing leading-zero ambiguous preserve owner. Three-or-more-block dotted
surfaces keep the existing date, code, version/file, and protected routing.

Current standalone invalid/malformed forms:

| Surface | Current output | Partial fallback | Follow-up |
|---|---|---|---|
| `01` | `01` | no | none |
| `+01` | `+01` | no | none |
| `-01` | `-01` | no | none |
| `01.5` | `01.5` | no | existing leading-zero malformed preserve |
| `+01.5` | `+01.5` | no | atomic invalid signed preserve |
| `-01.5` | `-01.5` | no | atomic invalid signed preserve |
| `001.5` | `001.5` | no | existing leading-zero malformed preserve |
| `+001.5` | `+001.5` | no | atomic invalid signed preserve |
| `-001.5` | `-001.5` | no | atomic invalid signed preserve |
| `1,00` | `1,00` | no | none |
| `1,00.5` | `1,00.5` | no | none |
| `+1,00.5` | `+1,00.5` | no | none |
| `+.5` | `+.5` | no | none |
| `-.5` | `-.5` | no | none |
| `1.` | `일.` | yes | audit whether bare trailing dot should preserve |
| `+1.` | `+1.` | no | none |
| `3..140` | `삼..백사십` | yes | separate segmented reading design; not leading-zero cleanup |
| `1,0000` | `1,0000` | no | none |

## 4. Owner-attached numeric matrix

| Owner | Valid numeric forms | Sign | Decimal | Comma | Spacing | Invalid handling | Trailing zero state |
|---|---|---|---|---|---|---|---|
| unit | integer, decimal, comma integer/decimal for registered unit policy; `kHz` and `KB` inherit the same decimal eligibility; SI `m`/`M` remains case-sensitive; exact natural caret-power allowlist is limited to `mm·cm·km·m` directly followed by `^2` or `^3` | `+`/`-` plus owner-local dash-like minus aliases such as `–` only under full-claim signed unit conditions | yes for registered simple/special units | yes for valid comma integer/decimal | registered units allow attached or one ASCII space; caret unit-to-exponent has no gap | malformed numeric+unit and unsafe tails preserve; unsupported `alphabetic-unit^exponent` keeps that literal block while a separately valid numeric prefix may be read; exponent-only fallback is forbidden | `2.35kHz -> 이쩜삼오 킬로헤르츠`, `2.35KB -> 이쩜삼오 킬로바이트`, `10000.5kg -> 만쩜오 킬로그램`, `2.35m^2 -> 이쩜삼오 제곱미터`, `2.35KB^2 -> 이쩜삼오KB^2` |
| counter | integer/comma integer and owner-approved mixed Korean-Arabic numeric core followed by registered counter noun; contextual units retain exact-anchor meaning gates | valid decimal only; signed integer remains unsupported | yes through the registered decimal suffix or contextual owner; integer-only special determiners remain excluded | yes for valid comma decimal; integer policy unchanged | decimal uses the existing owner-specific unit spacing; attached tails `쯤·정도·꼴·당` remain source-exact | malformed/leading-zero/code-like/protected surfaces preserve atomically; ambiguous contextual bare decimal preserves | `+2.35명 -> 플러스 이쩜삼오 명`, `-2.35개 -> 마이너스 이쩜삼오 개`, `총 2.35번 -> 총 이쩜삼오 번`, `2.35번 확인했다 -> preserve` |
| multiplier | unsigned integer/comma integer and unsigned decimal/comma decimal followed by Korean multiplier noun `배`, e.g. `3배`, `3 배`, `1.5배`, `1,000.5 배` | no signed multiplier in this phase | yes | yes for valid comma integer/decimal | no space or one ASCII space before `배`; renders one generated space before original `배` | malformed/signed forms are not claimed by multiplier in this phase; protected/code-like contexts preserve first | decimal uses ordinary Sino decimal reading; integer `1..39` uses native/hybrid counter-style reading and `40+` uses Sino |
| duration/year-period | duration `시간`/`분`; registered decimal duration-like suffixes such as `일`, `주`, `개월`, `년`; narrow exact `N년간` year-period form | negative duration preserves | yes for valid decimal registered duration/time suffixes | yes where duration numeric reader accepts | owner-scoped; decimal registered suffixes render one generated space before the original suffix | unsafe exact year-period tails preserve, e.g. `1년간abc`; unsafe decimal suffix tails preserve, e.g. `4.5주abc` | `분`/`초` share the suffix-time Sino reader and normalize only their integer-part leading zeros, e.g. `01.5분 -> 일쩜오 분`; other decimal duration suffixes retain ordinary reading, e.g. `4.5주 -> 사쩜오 주` |
| mixed integer atomic | complete valid Arabic-Hangul integer core using `십/백/천/만/억/조/경`, after more-specific owners; a trailing Arabic block must be a positive value smaller than its immediately preceding small unit | no sign | no | valid comma blocks only where the shared integer parser accepts them | preserves source adjacency to safe Korean prose and sentence punctuation; registered counter/currency suffix owners retain priority and their spacing | ASCII identifier/code/URL/path/protected surfaces, prefixed ordinal-like forms, leading zero, malformed/repeated unit order, oversized trailing Arabic block, and partial numeric residue preserve | numeric blocks use Sino reading and original Korean unit characters retain provenance: `6천400 -> 육천사백`, `1천2백3십4 -> 일천이백삼십사`, `값은3천만5천이다 -> 값은삼천만오천이다`; `6천400명` keeps the existing counter owner |
| mixed decimal atomic | complete valid mixed integer core ending in an Arabic block, followed by `.` and one or more fractional digits | no sign | yes; ordinary positional fraction reading | inherited from the integer core | preserves source adjacency to safe Korean prose and sentence punctuation | generic decimal cannot claim only the trailing fragment; malformed/repeated dots, protected/code-like surfaces, unsafe ASCII tails, and invalid mixed integer cores preserve | full consume before generic decimal: `5천830.13 -> 오천팔백삼십쩜일삼`; Arabic blocks and decimal reading are generated while Korean numeric units retain original provenance |

Leading-zero owner decisions are explicit exceptions to ordinary owner parsing.
A leading-zero counter such as `01명` preserves the complete surface; it does
not become `한 명`. Registered suffix-time owners remove leading zeros only
inside numeric cores they validly claim. The clock-hour owner requires attached
`N시`; minute/second keep their existing spacing policy. Thus
`00시 -> 영 시`, `09시 -> 아홉 시`,
`07시 05분 -> 일곱 시 오분`, and
`23분045초 -> 이십삼분 사십오초`. Colon time remains a separate owner, so
`09:30 -> 아홉시 삼십분`.

Whitespace between a numeric core and `시` or `시간` disables the specialized
clock/duration reading for that marker. The numeric core follows ordinary
number policy: `3 시 -> 삼 시`, `3 시간 -> 삼 시간`, and ordinary
leading-zero preserve keeps `09 시 -> 09 시` and `09 시간 -> 09 시간`.

Suffix-clock compounds accept compact, spaced, and mixed horizontal spacing:
`11시23분`, `11시 23분`, `11시23분45초`, `11시 23분45초`,
`11시23분 45초`, and `11시 23분 45초` are one structured time surface.
The time owner uses the existing clock-hour mapping for `N시`, the existing
Sino-Korean reading for `N분`/`N초`, and generates one boundary space only
where the source omitted it. `23분45초` and `23분 45초` use the same
minute-second compound path. Minute/second suffix amounts share one
Sino-Korean reader and are not restricted by digit count or the `00..59`
clock range: `11시005분 -> 열한 시 오분`,
`23분045초 -> 이십삼분 사십오초`, and
`123분545초 -> 백이십삼분 오백사십오초`. The attached hour owner removes
leading zeros before applying its `0..24` range; `00시 -> 영 시` and
`09시 -> 아홉 시`, while `99시` preserves. Invalid clock hours, malformed numeric cores,
protected/code-like contexts, and unsafe tails preserve the full surface
without allowing an internal `N시`, `N분`, or `N초` to re-enter through a
generic fallback.

The approximate tail `께` is admitted only when the time owner has already
full-consumed `N시 N분`, `N분 N초`, or `N시 N분 N초`. It is not a broad safe
tail for bare `N분` or hour-only `N시`: `오전 9시 6분께 -> 오전 아홉 시
육분께`, `5분 15초께 -> 오분 십오초께`, while `6분께` and `9시께`
preserve. Honorific-person readings such as `6분께 -> 여섯 분께` remain out
of scope.

After registered suffix owners, `mixed_integer_atomic` full-claims valid mixed
integer cores missed by the narrower large-unit boundary. It reuses the shared
small/large-unit parsers, accepts safe attached Korean prose and sentence
punctuation, and renders each Arabic block as generated Sino reading while
retaining original Korean unit provenance. Canonical examples are `6천400 ->
육천사백`, `1천2백3십4 -> 일천이백삼십사`, `2만3천 -> 이만삼천`,
`3천만5천 -> 삼천만오천`, and `금액은6천원이다 -> 금액은육천 원이다`.
A trailing Arabic block must be positive and smaller than the immediately
preceding `천/백/십`, so `5천830` is valid while `5천8300` preserves.
ASCII identifiers, protected contexts, leading-zero or malformed unit order,
prefixed ordinals, oversized trailing blocks, and partial numeric residue
preserve.

`mixed_decimal_atomic` full-claims an ordinary decimal attached to a valid
mixed integer ending in an Arabic block before the generic decimal fallback.
It reuses the integer reading and the ordinary positional fractional reading:
`5천830.13 -> 오천팔백삼십쩜일삼`. Invalid or code-like mixed decimal
tokens receive an atomic preserve claim, so the trailing `830.13` fragment
cannot be converted independently while a leading Arabic block remains.

Compact structured large-unit integer cores reuse the large-unit parser in the
counter owner when followed by registered `개` or longest-match `개월`. The
counter owner full-claims the numeric core and counter, uses the complete
Sino-Korean reading for values 100 or greater, preserves the original counter,
and applies the existing counter spacing rule:
`3만개 -> 삼만 개`, `1만3천개다 -> 일만삼천 개다`, and
`1만3천개월 -> 일만삼천개월`. Unsafe ASCII, slash, code-like, or unregistered
Hangul tails remain atomic preserve boundaries and must not leak an internal
large-unit or number rewrite.

Strong standalone colon-time boundary decisions are canonical owner decisions:
`0:00 -> 영시`, `00:00 -> 영시`, and `24:00 -> 이십사시`. These forms are
not governed by the older broad “standalone time-like preserve” wording.
Other ambiguous standalone time-like forms continue to follow the existing gate.

Batch 2 fixes the broader leading-zero owner matrix as follows:

| Surface family | Canonical example | Owner boundary |
|---|---|---|
| standalone integer | `01 -> 01`, `003 -> 003`, `007 -> 007`, `0001 -> 0001` | no Digit Mode fallback; source bytes preserve |
| identifier payload | `ID: 00123 -> 아이디: 00123` | registered acronym may transform; colon and numeric payload preserve |
| counter | `01명 -> 01명` | counter does not reinterpret a multi-digit leading-zero amount |
| unit | `03kg -> 03kg` | unit contamination owner full-claims preserve; no internal number fallback |
| suffix time | `00시 -> 영 시`, `09시 -> 아홉 시`, `09 시 -> 09 시`, `07시 05분 -> 일곱 시 오분`, `23분045초 -> 이십삼분 사십오초` | attached `시` applies its `0..24` clock range; whitespace before `시`/`시간` delegates to ordinary numeric policy; `분`/`초` retain their existing spacing and common Sino-reader rules |
| currency | `₩01,000 -> ₩01,000` | currency owner full-claims invalid leading-zero amount as preserve |
| registered exceptions | `01월 -> 일월`, `03일 -> 삼일`, `6월19일 -> 유월 십구일`, `010-1234-5678 -> 공일공 일이삼사 오육칠팔` | date markers and phone blocks keep their narrow owners; directly attached Korean date components receive a generated separator space |

ASCII/Hangul identifier tails and protected/code-like contexts do not license
partial conversion of a leading-zero numeric payload.


Compact large-unit cores keep an immediately attached approximate marker
`여` attached to the generated number reading:
`1만3천여 명 -> 일만삼천여 명`.

Ordinary Arabic integer reading supports large groups through `경`; `해`-width
values are unsupported and preserve at the narrow fallback boundary. Prefixed
ordinal surfaces generate a canonical space after `제`, while ordinary comma
decimals use the compact integer reader before their exact fractional digits.
Counter owners keep their own generated suffix spacing, including
`112명 -> 백십이 명`.

Spaced separator behavior is delimiter-specific. Spaced period forms such as
`12. 3` preserve completely. Spaced middle-dot forms retain the original
spaces and middle-dot while each numeric side is read independently:
`123 · 456 -> 백이십삼 · 사백오십육`.
The exact spaced-hyphen multi-block owner preserves its source separator:
`1 - 2 - 3 -> 일 - 이 - 삼`. It does not broaden two-block, attached, date,
range, minus, or differently spaced hyphen forms.

Clock-hour `N시` is handled by the time owner with an owner-local safe Korean tail whitelist. Safe attached tails such as `을/를/은/는/이/가/로/으로/와/과/도/만/부터/까지/에/에는/에서/에도/보다/처럼/마다` and `이다/입니다/인/이면/면/이라면/라면/이라고/라고/인데/였다/이었다` are allowed without opening broad numeric suffix fallback. Lexical/code-like continuations such as `시리즈`, `시스템`, `시장`, `시험`, `시즌`, and `시abc` remain preserve-first.

| registered numeric suffix | registered Korean numeric suffix inventory, including explicit numeric suffixes such as `차`, `과`, `선` | valid decimal may use `+` or owner-local minus alias; signed integer does not enter this branch | yes for valid decimal numeric core attached to a registered/approved suffix | yes for valid comma decimal | no space before suffix; renders one generated space before original suffix | malformed decimal and unsafe/code-like tails preserve or are not claimed; arbitrary Hangul suffixes and whitespace-separated ordinary nouns are not eligible | ordinary decimal/Sino reading + original suffix, e.g. `1.5차 -> 일쩜오 차` |
| Korean numeric chain | a full Korean-eligible token made only of completed Hangul and one or more valid ASCII integer blocks; a single digit block at token start is limited to one unregistered Hangul literal such as `5극` | no sign | no; invalid decimal/comma residue blocks the owner | no | preserves all source adjacency and spacing; inserts no semantic suffix space | ASCII letters, compatibility jamo, `_`, `/`, URL/path/email/code-like structures, Korean numeric-unit literals, registered suffix/counter blocks, explicit ambiguous attached `N대` surfaces, and partial residue are excluded; registered/preserve owners win first | reads only numeric cores without assigning suffix meaning: `다우존스30 -> 다우존스삼십`, `5극3특 -> 오극삼특`; `3대` is an explicit atomic-preserve exception and `123입니다` remains the existing generic number + original Korean path |
| percent | integer, decimal, slash fraction for percent-point `%p`/`%P`; `%` supports signed decimal-aware forms | `+`/`-` plus owner-local dash-like minus aliases such as `–` only under full-claim signed percent or percent-point conditions | yes | yes where numeric reader accepts | no space or one ASCII space | malformed percent/percent-point preserves; dash-like invalid forms preserve, e.g. `–1,00.5%` | ordinary decimal fractional zero uses `영`, e.g. `25.50% -> 이십오쩜오영 퍼센트`, `–2.03% -> 마이너스 이쩜영삼 퍼센트` |
| temperature / degree | signed temperature, signed degree, unsigned degree-like unit surfaces | signed temperature uses `영상/영하`; bare degree has separate policy; dash-like minus aliases are owner-local under full-claim signed temperature/degree conditions | yes | signed parser accepts comma where valid | optional one space for signed unit variants | malformed signed temperature preserves, e.g. `+.5℃` | ordinary decimal fractional zero uses `영`, e.g. `25.50℃ -> 이십오쩜오영도`, `+25.50℃ -> 영상 이십오쩜오영도` |
| KRW currency | registered KRW code/symbol/suffix forms | `+`/`-` supported around registered markers | yes | yes | no space or one ASCII space | invalid comma/leading-zero forms preserve; no partial fallback | ordinary decimal fractional zero uses `영`, e.g. `KRW25.50 -> 이십오쩜오영 원` |
| non-KRW currency | registered USD/EUR/JPY/GBP forms within current currency matrix | partial sign support by marker form | USD/EUR decimal currently allowed; JPY integer-focused | yes where amount parser accepts | no space or one ASCII space | unsupported or malformed currency tokens preserve | current decimal fractional zero is `영`, e.g. `USD 25.50 -> 이십오쩜오영 달러` |
| large-unit | Arabic integer/comma integer, signed decimal, Arabic-Hangul/Korean mixed full surface; structured compact final decimal after at least one explicit large unit, e.g. `5만1839.26` | `+`/`-` for decimal large-unit lexical form | yes; structured mixed form allows a decimal only in the final small group | yes where the existing group parser permits | lexical decimal suffix spacing is owner-scoped; structured compact form creates no missing group space | invalid comma, leading zero, empty/extra dot, unit after final fraction, ASCII/code-like tail, mixed-unit failure, and unapproved adjacent delimiters `–—−－＋·` preserve without internal fallback | `25.50억 -> 이십오쩜오영 억`; `2.35억–원 -> preserve`; `5만1839.26 -> 오만천팔백삼십구쩜이육` |
| tilde range | two numeric sides with tilde-like delimiter; optional compatible suffix/tail; range-compatible unit aliases include meter `ｍ` | limited signed range forms in current policy | yes | yes for valid numeric blocks | suffix/tail policy owner-scoped | malformed range preserves; no partial fallback for invalid owner surface, e.g. `1~~2ｍ` | current range decimal output uses `영`, e.g. `1.50~2.50테스트 -> 일쩜오영에서 이쩜오영 테스트` |
| colon / N:M | broad non-time-like `N:M`; multi-colon supported separately | signed decimal in approved paths | yes | yes | Korean tail spacing owner-scoped | invalid/multi-delimiter/time-like/code-like guards preserve | ordinary decimal fractional zero uses `영`, e.g. `3:4.50테스트 -> 삼 대 사쩜오영 테스트` |
| Korean `대` score pair | valid readable numeric operands already supported by current production numeric owners as standalone numeric expressions; plain integer compact `N대M` keeps compact score reading | ASCII `+`/`-` signed integer/decimal operands where standalone signed owner validates them | yes | yes | supports `LEFT 대 RIGHT`, `LEFT대RIGHT`, `LEFT대 RIGHT`; `LEFT 대RIGHT` remains unsupported | malformed/unsafe operands and protected/code-like contexts are not claimed; right operand attached to registered owner suffix/unit/currency/percent/duration/multiplier/counter surface blocks this owner | ordinary decimal fractional zero follows the underlying standalone numeric reading; non-plain operands render spaced around `대`, e.g. `2.1대1.5 -> 이쩜일 대 일쩜오` |
| compound slash unit | exact registered compound slash unit surfaces, including `/`, owner-local `／` aliases, and the exact `㎧` alias for `m/s`; examples include `km/h`, `m/s`, `㎧`, `km/L`, `mg/L`, `㎎/L`, `mg/dL`, `MB/s` | no signed compound slash broadening in this phase | yes for registered slash surfaces that already support integer numeric cores | yes for valid comma integer/decimal through the compound owner parser | no space or one ASCII space before the full registered suffix | malformed numeric cores, unregistered slash pairs, unsafe tails, spaced slash boundaries, URL/path/protected contexts preserve; no partial `5.6km` rewrite | ordinary decimal/Sino reading reuses the unchanged template, e.g. `5.6km/h -> 시속 오쩜육 킬로미터`, `55㎧ -> 초속 오십오 미터` |
| compound exact unit | exact `Mbps`, `Gbps`, `rpm`, `fps`, `ppm`, `ppb`, `dBi` | unsigned; existing signed compound policy unchanged | yes | yes for valid comma integer/decimal | attached numeric prefix only | malformed numeric core, unsafe tail, URL/path/protected context preserves atomically | `2.35Mbps -> 이쩜삼오 메가비피에스`, `2.35rpm -> 이쩜삼오 알피엠` |
| pH | `pH` plus complete valid numeric core | `+` and owner-local minus aliases under pH full-claim | yes | yes for valid comma decimal | existing optional gap after `pH` | malformed comma/repeated dot/unsafe tail preserves `pH` and numeric token together; sentence-final dot stays punctuation | `pH 7.4. -> 피에이치 칠쩜사.`, `pH –7.4 -> 피에이치 마이너스 칠쩜사`, `pH 7,4 -> preserve` |
| hyphen restricted range | approved `N-M + range-compatible unit`, e.g. `1-2kg` | broad signed hyphen ranges out of scope | decimal broad signed hyphen remains out of scope | narrow owner-specific support only | attached compatible unit required for range reading | arbitrary `1-2`, `1-2테스트`, `+1.5-2kg` preserve | follows owner parser when valid; no broad trailing-zero policy |
| single-letter numeric-code | single ASCII uppercase letter followed by unsigned integer/valid decimal, with optional ASCII `-` separator; integer tail letters remain owner-local, e.g. `K1`, `K-1`, `F-15C`, `B-2.5`, `K-1.5` | no sign; ASCII `-` is a separator, not minus | yes | no comma in current owner | no space or ASCII `-` separator | plus/signed, leading-zero malformed decimal, bare dot, malformed decimal, unsafe tails, and protected contexts preserve or claim preserve to block partial decimal fallback | integer one-digit code readings use code digit forms such as `원`, `투`; decimals use ordinary `쩜`, e.g. `K-1.5 -> 케이 일쩜오` |
| managed dictionary numeric-code | exact current English managed dictionary entry followed by a short unsigned integer/valid decimal suffix, with optional ASCII `-` separator, e.g. `GPT4`, `Wi-Fi-6`, `version-1.5`; simple fallback-covered acronyms such as `AI`, `CPU`, and `USB` are not current managed dictionary entries, so `AI3`, `CPU900`, and `USB300` remain excluded | no sign; ASCII `-` is a separator, not minus | yes, but decimal integer part must be 1-2 digits | no comma in current owner | no space or ASCII `-` separator | unregistered ASCII word + numeric preserves; plus/signed, leading-zero malformed decimal, bare dot, malformed decimal, long numeric suffixes such as `KTX-2024`, `GPT-2024`, and `version-2024`, unsafe tails, and URL/path/email/JSON/backtick/square bracket/file-like contexts preserve or claim preserve to block partial fallback | registry-backed from current managed dictionary entries and reuses single-letter numeric-code reader for accepted short suffixes, e.g. `GPT-4 -> 지피티 포`, `version-1.5 -> 버전 일쩜오` |
| phone / hyphen digit blocks | phone-like exact forms and multi-block digit routes | no arithmetic sign semantics | no decimal phone | no comma phone | hyphen-separated digit blocks | unsafe/code-like/path contexts preserve | digit-by-digit; not decimal trailing-zero policy |

### Contextual numeric `대` matrix

The source-attached `N대` rule first preserves the existing score-pair and
ordinal owners. The existing unsigned-integer 40+ threshold remains, but
decimal, signed, leading-zero, malformed, and alphanumeric forms are now
contextual deferred surfaces regardless of value. Protected/code-like owners
remain higher priority.

Values below 40 retain the conservative contextual gate. The exact centralized
counter-noun inventory is `자동차`, `차량`, `장비`, `버스`, `서버`, and
`카메라`. In addition to the immediately preceding lexical noun and narrow
adjacent continuation, the gate accepts only
`registered noun + 은/는/이/가 + space + 모두/총 + space + N대`. It does not
cross punctuation or infer arbitrary nouns, verbs, or distant context.

| 유형 | 예 | canonical |
|---|---|---|
| relation | `2대1` | existing `이대일` |
| spaced relation | `2 대 1` | existing `이 대 일` |
| ordinal | `제2대` | existing `제 이대` |
| explicit registered counter | `차량 3대` | `차량 세 대` |
| topic/quantity registered counter | `자동차는 모두 3대` | `자동차는 모두 세 대` |
| decimal counter candidate | `장비 1.5대` | preserve |
| narrow adjacent continuation | `차량 2대 1대를` | `차량 두 대 한 대를` |
| Sino threshold integer | `40대`, `6,700대` | `사십 대`, `육천칠백 대` |
| decimal, any value | `40.5대` | preserve |
| ambiguous bare | `3대` | preserve |
| generation suffix | `3대째` | `삼 대째` |
| age exact anchor | `20대 남성` | `이십 대 남성` |
| generation exact noun | `가족 3대` | `가족 삼 대` |
| unapproved major-item noun | `3대 과제` | preserve |
| bare decimal | `1.5대` | preserve |
| protected/code-like | `[3대]`, backtick `3대`, `path/3대/file`, `A3대` | existing protected result |

The integer threshold path reuses the existing counter renderer and records
reason `dae_counter_sino_threshold_40_plus`. All confirmed/deferred low-value
decisions use the `contextual_number_unit` owner and terminally block decimal,
generic number, counter, and Korean numeric-chain reentry. Age and generation
use only the exact registries above; major-item inference, unprefixed ordinal,
verb-only quantity, and probabilistic context inference remain excluded.

Claim precedence is:

```text
protected / structured owner
-> explicit score or game context N대M
-> malformed contextual defer or threshold-qualified integer N대
-> explicit contextual machine/generation/age N대
-> keywordless independent N대M
-> ambiguous contextual N대 defer
-> generic number fallback
```

For a registered explicit quantity context followed by another independent
number, `numeric_dae_quantity_sequence` full-claims `N대 M`, uses the counter
renderer on the left and the ordinary compact number reader on the right.
This prevents a quantity list from being mislabeled as a keywordless score:

```text
자동차는 모두 6,700대, 12,500입니다.
-> 자동차는 모두 육천칠백 대, 만 이천오백입니다.
자동차는 모두 6,700대 12,500입니다.
-> 자동차는 모두 육천칠백 대 만이천오백입니다.
```

An explicit score keyword still wins. A context-free spaced threshold form such
as `40대 3` is handled as threshold counter plus ordinary number, while the
source-compact structured relation `40대3` remains score/relation-owned.

Signed temperature/degree right-boundary policy is owner-local. The signed
temperature/degree surfaces `+N°`, `-N°`, `+N℃`, `-N℃`, `+N℉`, `-N℉`,
`+N°C`, `-N°C`, `+N°F`, and `-N°F` are claimed only when the right boundary is
end-of-string, whitespace, punctuation, or Hangul-leading. Hangul-leading tails
remain verbatim after the generated reading, e.g. `+25℃보다 -> 영상 이십오도보다`
and `+3°테스트 -> 플러스 삼도테스트`. ASCII/code-like/slash continuations are
preserve-first, e.g. `+25℃abc`, `+25℃v2`, `+25℃/min`, `+3°abc`, and `+3°/s`.
이 규칙은 signed temperature/degree owner에만 적용하며 일반
unit/counter/currency/percent 처리, broad numeric suffix fallback, 전역
particle whitelist를 변경하지 않는다. 이 규칙은 조사 교정을 수행하지 않는다.

Registered compound slash unit decimal coverage is implemented owner-locally.
The reading templates are unchanged from the integer compound slash registry:
`90km/h -> 시속 구십 킬로미터` and
`5.6km/h -> 시속 오쩜육 킬로미터`; `5m/s` and `7.8m/s` both use the same
`초속 {number} 미터` template; `15.2km/L` and `3.2mg/L` both use the same
`리터당 {number} ...` family. Unsupported or unregistered slash pairs such as
`foo/bar`, spaced slash boundaries such as `5.6km / h`, and malformed numeric
cores such as `.5km/h`, `01.5km/h`, `1.km/h`, `1..5km/h`, and `1,00.5km/h`
remain preserve-first and must not route through a broad slash fallback.

Dash-like signed numeric alias examples:

| Surface | Expected output | Policy note |
|---|---|---|
| `–2.03%` | `마이너스 이쩜영삼 퍼센트` | signed percent/unit owner full-claims the complete surface |
| `1–2kg` | `일에서 이 킬로그램` | range owner remains authoritative; dash is not a sign alias here |
| `서울–부산` | `서울–부산` | connector dash preserve |
| `–2.03abc` | `–2.03abc` | unsafe tail preserve; no internal partial rewrite |
| `` `–2.03%` `` | `` `–2.03%` `` | protected preserve |

## 5. Invalid / malformed numeric handling

Owner-attached malformed numeric surfaces should be full-preserved when they
look like an owner candidate but fail numeric validation. Examples:

```text
1,00원 -> 1,00원
USD 1,00 -> USD 1,00
+.5℃ -> +.5℃
+.5ｍ -> +.5ｍ
1,00ｍ -> 1,00ｍ
6천400명abc -> 6천400명abc
6천400명/log -> 6천400명/log
1년간abc -> 1년간abc
1~~2테스트 -> 1~~2테스트
1~~2ｍ -> 1~~2ｍ
3::4테스트 -> 3::4테스트
1-2테스트 -> 1-2테스트
2,34억 -> 2,34억
25..50억 -> 25..50억
```

Standalone empty-left and duplicate-dot numeric forms now use an atomic
`malformed_dotted_numeric_preserve` claim before generic number fallback.
Accordingly `.5`, `3..140`, and `25..50` preserve instead of reading individual
digit fragments. A final `N.` at a sentence boundary remains ordinary number
plus punctuation; owner-attached empty-right forms such as `5만1839.` preserve
through their structured owner. Invalid comma grouping and broader file/code-like
protection remain separate owner boundaries.

## 5.1 Malformed numeric follow-up taxonomy

Malformed numeric-like surfaces are split into separate policy tracks.

### Current targeted cleanup: standalone leading-zero malformed decimals

Standalone malformed decimals whose integer part has more than one digit and
starts with `0` should preserve rather than drop the leading zero through
decimal fallback.

Examples:

```text
01.5 -> 01.5
+01.5 -> +01.5
-01.5 -> -01.5
001.5 -> 001.5
+001.5 -> +001.5
-001.5 -> -001.5
```

Reading them as `일쩜오`, `+일쩜오`, or `-일쩜오` drops leading-zero surface
information. This cleanup does not change valid `0.x` decimals such as `0.5`,
`0.03%`, `0.8초`, or `0.5명`.

### Implemented dotted malformed atomic preserve

Empty-left and duplicate-dot numeric-like surfaces are not segmented:

```text
.5 -> .5
3..140 -> 3..140
25..50 -> 25..50
2,34 -> 2,34
2,,345 -> 2,,345
2,34억 -> 2,34억
3백..4십만 -> 3백..4십만
```

use the atomic malformed-dotted preserve owner. Sentence-final `N.` remains
number plus original punctuation. Invalid comma forms remain a
separate policy area. The historical segmented design in section 11 is non-canonical. Any future segmented
reader must preserve original separators and avoid rewriting protected/code-like
tokens. Segmented malformed numeric reading is not an active implementation
target in this pass.

### Separate prerequisite: file-like/version-like/code-like protection

Before any broader segmented malformed numeric reader is expanded, file-like,
version-like, and code-like tokens must remain protected or explicitly
excluded:

```text
file-25..50.txt
version-1.5
v25..50
SKU25..50
```

These are not solved by the standalone leading-zero malformed decimal cleanup.
Current audit gaps for these surfaces are recorded in section 11.4 and must be
addressed as a prerequisite safety track before any segmented reader ships.

## 6. Partial fallback policy

The owner-attached policy is stricter than the standalone fallback policy:

1. If an owner can structurally identify a numeric-unit/currency/range/large-unit
   surface but the internal numeric form is invalid, the owner should claim a
   preserve surface.
2. Broad internal digit fallback must not rewrite inside invalid owner surfaces.
3. Protected spans outrank owner claims.
4. Standalone malformed numeric partial fallback is split into three separate
   follow-up tracks in section 5.1: leading-zero malformed decimal preserve
   cleanup, segmented malformed numeric reading design, and file-like/
   version-like/code-like protection prerequisites.

## 6.1 Spaced slash boundary handling

ASCII-space-wrapped slash delimiters inside Korean-eligible text are handled as
segment boundaries, not as a new slash owner. The delimiter and its surrounding
ASCII spaces are raw-preserved, and each non-empty segment is sent through the
existing transform pipeline/core independently.

This layer does not classify item types such as unit, temperature, currency, or
percent. Invalid owner-attached numeric surfaces such as `+.5kg`, `1,00kg`, and
`+01.5kg` remain full-preserved by their existing owner rules, while a valid
segment on the other side of the delimiter may still transform.

No-space slash surfaces remain under existing fraction/date/compound-unit/path
and URL policies. Protected spans, including URL/path/email/JSON/backtick/fenced
code and square bracket interiors, are not split. Slash-separated segments do
not share context across the delimiter. No-Hangul global bypass behavior remains
out of scope for expansion, and newline-crossing slash split is not supported.

## 7. Trailing zero current state

This section records the implemented ordinary decimal fractional-zero
canonicalization. Ordinary decimal-aware owners read fractional `0` as `영`.

| Context | Example | Current output | Zero reading |
|---|---|---|---|
| standalone unsigned decimal | `25.50` | `이십오쩜오영` | `영` |
| standalone signed decimal | `+25.50` | `플러스 이십오쩜오영` | `영` |
| unit | `25.50kg` | `이십오쩜오영 킬로그램` | `영` |
| percent | `25.50%` | `이십오쩜오영 퍼센트` | `영` |
| KRW | `KRW25.50` | `이십오쩜오영 원` | `영` |
| non-KRW | `USD 25.50` | `이십오쩜오영 달러` | `영` |
| bare unsigned temperature | `25.50℃` | `이십오쩜오영도` | `영` |
| signed temperature | `+25.50℃` | `영상 이십오쩜오영도` | `영` |
| large-unit decimal | `25.50억` | `이십오쩜오영 억` | `영` |
| tilde range | `1.50~2.50테스트` | `일쩜오영에서 이쩜오영 테스트` | `영` |
| colon pair | `3:4.50테스트` | `삼 대 사쩜오영 테스트` | `영` |

Non-KRW currency already matched the `영` policy before this implementation.
Phone/code/time-like/digit-sequence owners remain outside this table.

## 8. Protected context precedence

Protected contexts are evaluated before numeric owner rewriting. Numeric owners
must not rewrite inside:

- backtick spans
- JSON-like string values
- path-like spans
- URL spans
- email/code-like literal spans
- version/code-like prefixes and owner-specific code gates
- phone-like or hyphen digit routes when their owner claims first
- line/case/version/scripture-like colon guards

Examples:

```text
`KRW1000` -> `KRW1000`
{"price":"KRW1000"} -> {"price":"KRW1000"}
/path/2,345억/log -> /path/2,345억/log
https://example.com?q=KRW1000 -> https://example.com?q=KRW1000
case 3:4테스트 -> case 3:4테스트
```

## 9. Time-like and hyphen exceptions

This section records the finalized three-step implementation for `N:M` /
time-like canonical policy. Strong bare time-like surfaces now read as time,
ambiguous time-like surfaces remain preserve without context, explicit
ratio/score context can route ambiguous time-like forms to `대` reading, and a
feature probe covers source / production_source / optional binary / optional API
runtime paths.

### 9.1 Protected context precedence

Protected and code-like contexts must outrank broad time or `N:M` claims:

- backtick spans
- JSON-like string values
- path-like spans
- URL spans
- code-like contexts
- line/case/file/scripture-like colon contexts

`version` is a current managed dictionary entry and no longer acts as a broad
code-like marker for non-time-like two-block `N:M`; e.g. `version 1:2테스트`
reads as `버전 일 대 이 테스트`. Time-like/version-like contexts can still
preserve through the time/version protection rules.

Current production-source audit examples:

```text
`3:4테스트` -> `3:4테스트`
{"ratio":"3:4테스트"} -> {"ratio":"3:4테스트"}
/path/3:4/log -> /path/3:4/log
https://example.com?q=3:4테스트 -> https://example.com?q=3:4테스트
line 1:23 -> line 1:23
case 1:23 -> case 1:23
version 1:23 -> version 1:23
file 1:23 -> file 1:23
요한복음 3:16 -> 요한복음 3:16
```

### 9.2 HH:MM time-like definition

Target definition:

- hour is `H` or `HH`.
- hour value is `0..24`.
- minute is exactly two digits and value `00..59`.
- hour `25+`, one-digit minute, three-or-more-digit minute, and
  three-or-more-digit hour are not time-like.

Examples:

```text
00:30 -> time-like
09:30 -> time-like
13:05 -> time-like
24:50 -> time-like
25:30 -> non-time-like
13:5 -> non-time-like
1:234 -> non-time-like
123:45 -> non-time-like
```

### 9.3 Strong time-like policy

Strong time-like surfaces should read as time outside protected contexts:

```text
00:30 -> 영시 삼십분
01:40 -> 한시 사십분
02:30 -> 두시 삼십분
08:30 -> 여덟시 삼십분
09:30 -> 아홉시 삼십분
10:00 -> 열시
11:05 -> 열한시 오분
12:00 -> 열두시
3:04 -> 세시 사분
13:05 -> 십삼시 오분
24:09 -> 이십사시 구분
```

This is implemented for bare and ordinary non-protected contexts. For every
successfully claimed colon time, hour `00` is read as `영시`, hours `01..12`
use native Korean clock-hour forms, and hours `13..24` use Sino-Korean number
readings followed by `시`.

An exact `00` minute component is omitted after a successful time claim.
Existing strong admission covers valid two-digit leading-zero `0H:MM` surfaces
and valid colon times whose minute is `00..09`. Other valid time-like forms,
including `24:10..24:59`, retain the existing ambiguous context gate. A
one-digit minute is non-time-like and may fall to the broad semantic-pair owner:

```text
0:00 -> 영시
00:00 -> 영시
24:01 -> 이십사시 일분
7:5 -> 칠 대 오
```

`0:00` is the existing single-digit zero-hour boundary and `00:00` is the
two-digit leading-zero colon form. Both are owned time surfaces and render
`영시`. This clarification does not broaden other single-digit zero-hour forms.

### 9.4 Ambiguous time-like target policy

Valid `H:MM` or `HH:MM` surfaces not covered by the strong rule can be time,
ratio, or score depending on context. In particular, non-leading-zero hours
with minute `10..59` retain the existing ambiguous context gate. Valid
two-digit leading-zero `0H:MM` surfaces are strong outside protected or
higher-priority semantic contexts and are not part of this ambiguous set.

Time context should read as time:

```text
3:40에 -> 세시 사십분에
24:50까지 -> 이십사시 오십분까지
```

Ratio/score context should read as `대`:

```text
3:40 비율 -> 삼 대 사십 비율
13:40 스코어 -> 십삼 대 사십 스코어
```

No context should preserve and must not fall through to broad `N:M`:

```text
3:40 -> 3:40
13:40 -> 13:40
24:50 -> 24:50
```

Current implementation preserves ambiguous no-context surfaces, reads explicit
time-postposition cases as time, and reads ambiguous ratio/score context as
`대`.

The broad non-time-like rule also owns bare valid two-block numeric surfaces
whose shape is excluded from HH:MM, so `16:9 -> 십육 대 구`. Explicit score and
ratio context produces the same owner and rendering, for example
`한국 vs 일본 3:2 -> 한국 vs 일본 삼 대 이` and
`화면 비율 16:9 -> 화면 비율 십육 대 구`. Protected URL/path/JSON/backtick and
registered code-like claims still outrank this owner.


#### 9.4.1 Comma-separated HH:MM time-list context

Same-sentence comma-separated `H:MM` / `HH:MM` lists may share time context only
through the time owner's explicit time-list context gate. This is not a new
broad colon owner, and it must not route through broad `N:M`.

Allowed time-list context is limited to explicit time evidence such as a nearby
schedule/time keyword, a time prefix/postposition, or a preceding already
claimed Korean time expression in the same comma list:

```text
회의 시간은 13:05, 10:30, 23:59이다 -> 회의 시간은 십삼시 오분, 열시 삼십분, 이십삼시 오십구분이다
회의는 13:05, 10:30, 23:59에 진행된다 -> 회의는 십삼시 오분, 열시 삼십분, 이십삼시 오십구분에 진행된다
일정은 09:30, 14:00, 18:30입니다 -> 일정은 아홉시 삼십분, 십사시, 십팔시 삼십분입니다
```

Comma delimiters remain raw, and each `H:MM` / `HH:MM` item is independently
claimed by the time owner. No-context lists preserve:

```text
13:40, 24:50 -> 13:40, 24:50
메모는 10:30, 23:59 -> 메모는 10:30, 23:59
```

Ratio/score, scripture-like, line/case/file, protected, URL/path/JSON/
backtick/code-like contexts remain excluded and keep their existing preserve or
owner behavior.

### 9.5 Non-time-like N:M fallback

Non-time-like valid `N:M` surfaces can read as `N 대 M` when they are not inside
protected contexts:

```text
25:30 -> 이십오 대 삼십
3:4 -> 삼 대 사
13:5 -> 십삼 대 오
1:234 -> 일 대 이백삼십사
123:45 -> 백이십삼 대 사십오
```

### 9.6 Invalid colon partial fallback

Malformed colon surfaces should preserve as a structured surface and must not
rewrite internal numeric fragments:

```text
+01:2 -> +01:2
+1.:2 -> +1.:2
+.5:2 -> +.5:2
1,00:2 -> 1,00:2
01:2:3 -> 01:2:3
1:+2.:3 -> 1:+2.:3
1,00:2:3 -> 1,00:2:3
```

The policy test and runtime probe cover these current preserve cases.

### 9.7 Multi-colon scope

Multi-colon numeric surfaces remain under the existing multi-colon owner policy.
This `N:M` / time-like canonical cleanup does not redefine `A:B:C` or longer
surfaces, timecode-like preservation, block-count limits, or multi-colon
protected context behavior.


An `H:MM:SS` or `HH:MM:SS` shape is claimed as one atomic preserve surface,
including inside an ordinary Korean sentence. No inner time or semantic-pair
claim may partially rewrite it: `3:05:09 -> 3:05:09` and
`기록은 13:05:09이다 -> 기록은 13:05:09이다`.

Hyphen is not a broad numeric range delimiter:

- `1-2kg -> 일에서 이 킬로그램` is an approved restricted owner-attached range.
- `1-2`, `1-2테스트`, `+1.5-2kg`, and `-1.5-2kg` preserve.
- Phone and multi-block digit routes are separate hyphen owners, not numeric
  range inference.

## 10. Open follow-up decisions

1. Malformed large-unit segmented reading policy:
   - Current preserve: `2,34억`, `2,,345억`, `25..50억`, `3백..4십만`.
   - Future candidate behavior:
     - `2,34억 -> 이,삼십사억`
     - `2,,345억 -> 이,,삼백사십오억`
     - `25..50억 -> 이십오..오십억`
     - `3백..4십만 -> 삼백..사십만`
   - Candidate principle: do not reinterpret values; preserve malformed
     separators; read only independent valid segments around separators; keep
     protected/path/URL/JSON/backtick spans protected.
2. Standalone leading-zero malformed decimal preserve cleanup:
   - Targeted cleanup only: `01.5`, `+01.5`, `-01.5`, `001.5`, `+001.5`,
     `-001.5`.
   - Not in scope: `1.`, `3..140`, `25..50`, `2,34`, `2,,345`, `2,34억`,
     `3백..4십만`; those belong to segmented reading design or other follow-ups.
3. File-like/code-like protection prerequisite:
   - `file-25..50.txt`, `v25..50`, `SKU25..50` remain open audit gaps and must
     be resolved before any broad segmented malformed numeric reader expands.
   - `version-1.5` is no longer an open segmented-reader gap; it is a managed
     dictionary numeric-code target and reads `버전 일쩜오`.
4. Non-KRW currency trailing zero targeted fix.
5. Time-like `숫자:숫자` binary/API probe and final policy cleanup.
6. Hyphen broad expansion remains a non-goal unless separately approved.

## 11. Malformed Numeric Segmented Reading Policy Analysis (Historical, Non-Canonical)

This section records an earlier exploratory segmented-reading design. It is not
current canonical behavior for empty-left or duplicate-dot surfaces; those
surfaces preserve atomically under `malformed_dotted_numeric_preserve`. A final
single dot after a valid integer remains sentence punctuation.

This section is a policy analysis and audit inventory only. It does not define
an implementation change and it is not a large-unit-only policy. Segmented
malformed numeric reading is a separate future design track from the narrow
leading-zero malformed decimal preserve cleanup in section 5.1. The target
surface is any malformed numeric-like input that is not already owned by a
valid numeric owner, not protected, and not structurally meaningful under an
existing delimiter owner.

### 11.1 Purpose

The follow-up question is whether a late common fallback can read independent
numeric fragments around malformed separators without correcting the value. The
fallback must never rebuild a single numeric value, normalize separators, or
reinterpret invalid numeric syntax.

Examples that remain existing-owner surfaces and are not segmented-reading
targets:

```text
25.50억
2,345억
1,000.50원
1~2kg
3:4
1-2kg
2026/06/17
1/3
12.3 비상계엄
```

### 11.2 Late fallback position

A future segmented reader, if added, must be later than all existing protection,
owner, and strict invalid checks:

1. Absolute Preserve / protected span / code-like / URL / path / JSON /
   backtick exclusion.
2. Canonical structural delimiter owner / exception inventory check.
3. Existing valid owner full claim.
4. Existing owner-specific strict invalid preserve / fallback-block decision.
5. Only malformed numeric-like surfaces outside the above categories become
   segmented reading candidates.
6. Candidates that fail segmented reading conditions terminal-preserve.

This order keeps existing owner behavior stable, prevents reentry into
protected spans, avoids treating structural delimiters as malformed separators,
and preserves when classification is uncertain.

### 11.3 Structural delimiter inventory principle

Colon and hyphen are not pre-excluded by assumption. Every delimiter-like
surface must first be checked against the canonical owner / exception inventory.
The current inventory is:

| Delimiter family | Existing owner / exception inventory |
|---|---|
| colon-like | strong time-like, explicit time context, ambiguous time-like preserve, semantic `N:M`, broad non-time-like `N:M`, multi-colon, timecode-like multi-colon preserve, invalid colon fallback block, scripture / line / case / file context preserve, time-like version preserve |
| hyphen/dash-like | restricted `N-M` range with compatible unit/counter/currency suffix, standalone `N-M` preserve, signed hyphen range non-goal, date-like, file-like, version-like, K-prefix, single-letter code, phone-like, code separator fallback |
| slash-like | fraction, modern slash date, compound unit, path, URL, slash ratio non-goal |
| dot-like | decimal, event number, middle event fallback, version-like, file extension, pH, abbreviation/code-like dot, malformed dot candidate |
| comma-like | valid thousands comma, list separator, invalid comma grouping, currency comma decimal, large-unit comma integer, malformed comma candidate |
| middle-dot-like | event number, middle-dot numeric block, lexical middle-dot |
| tilde-like | numeric range, tilde-like delimiter aliases, invalid tilde fallback block, protected/path/URL/JSON/backtick internal range |

Current production-source audit examples:

| Surface | Current output | Inventory note |
|---|---|---|
| `3:15` | `3:15` | ambiguous time-like preserve |
| `09:30` | `아홉시 삼십분` | strong time-like |
| `0:00` | `영시` | exact strong standalone time boundary |
| `24:00` | `이십사시` | exact strong standalone day boundary |
| `1 - 2 - 3` | `일 - 이 - 삼` | exact spaced-hyphen multi-block; source separator retained |
| `7m^3` | `칠 세제곱미터` | registered English unit caret-power owner |
| `3:4` | `삼 대 사` | broad `N:M` |
| `1:2:3` | `일 대 이 대 삼` | multi-colon |
| `1-2` | `1-2` | standalone hyphen preserve |
| `1-2kg` | `일에서 이 킬로그램` | restricted compatible-unit range |
| `+1.5-2kg` | `+1.5-2kg` | signed hyphen range non-goal |
| `1/3` | `삼분의 일` | fraction |
| `2026/06/17` | `이천이십육년 유월 십칠일` | slash date |
| `15.2km/L` | `리터당 십오쩜이 킬로미터` | compound unit |
| `25.50` | `이십오쩜오영` | decimal |
| `12.3 비상계엄` | `십이삼 비상계엄` | event |
| `v1.2.3` | `v1.2.3` | version-like preserve |
| `1,000` | `천` | valid comma integer |
| `1,000.50` | `천쩜오영` | valid unsigned comma decimal |
| `12·3` | `십이 삼` | middle-dot numeric block |
| `12·3 비상계엄` | `십이삼 비상계엄` | middle-dot event |
| `01·09` | `일 영구` | short first block numeric reading + later digit sequence |
| `12·003` | `십이 영영삼` | later block retains every digit; zero is 영 |
| `12· 3` | `십이· 삼` | asymmetric spaced middle-dot; source separator/gap preserved |
| `12.12 사태와 12.12 수치를 함께 적었다` | `십이십이 사태와 십이쩜일이 수치를 함께 적었다` | independent event and decimal claims |
| `1~2` | `일에서 이` | tilde range |
| `1~~2` | `1~~2` | invalid tilde fallback block |
| `[₩1200]` | `₩1200` | square-bracket absolute preserve; delimiters removed at presentation |
| `$-10` | `마이너스 십 달러` | signed currency symbol-prefix amount |
| `12.0300405` | `십이쩜영삼영영사영오` | unbounded fractional digit sequence |
| `A112` | `에이 백십이` | atomic single-letter alnum code |

### 11.4 Protected / code-like exclusion

The target policy remains absolute: segmented fallback must not reenter
backtick spans, JSON-like string values, paths, URLs, email, file-like tokens,
version-like tokens, shell/code snippets, code-like tokens, or square-bracket
protected spans.

Current production-source audit:

| Surface | Current output | Policy classification |
|---|---|---|
| `` `25..50억` `` | `` `25..50억` `` | protected preserve |
| `{"value":"25..50억"}` | `{"value":"25..50억"}` | JSON-like protected preserve |
| `/path/25..50억/log` | `/path/25..50억/log` | path protected preserve |
| `https://example.com?q=25..50억` | `https://example.com?q=25..50억` | URL protected preserve |
| `file-25..50.txt` | `file-25..오십.txt` | current audit gap; future segmenter must treat file-like as excluded |
| `version-1.5` | `버전 일쩜오` | managed dictionary numeric-code target; no longer a segmented-reader audit gap |
| `v25..50` | `v25..오십` | current audit gap; code-like prefix exclusion must outrank segmented fallback |
| `SKU25..50` | `SKU25..오십` | current audit gap; code-like token exclusion must outrank segmented fallback |

The remaining file-like/code-like gaps are recorded only as audit findings and
belong to the separate protection prerequisite in section 5.1. They are not
solved by leading-zero malformed decimal cleanup. `version-1.5` is handled by
the managed dictionary numeric-code owner, not by a broad segmented fallback.

### 11.5 Severe invalid preserve criteria

Severe invalid numeric-like inputs remain preserve candidates, not segmented
reading candidates, when they have empty edge segments, leading-zero conflicts,
strong invalid decimal/comma syntax, owner-attached invalid preserve conflicts,
or high value-reinterpretation risk.

Examples:

```text
+.5
+.5억
-.5
1.
1.억
01.5
+01.5
01.5억
+01.5억
1,00.5
+1,00.5원
```

Current production-source audit:

| Surface | Current output | Policy note |
|---|---|---|
| `+.5` | `+.5` | preserve |
| `-.5` | `-.5` | preserve |
| `+.5억` | `+.5억` | owner-attached invalid preserve |
| `1.` | `일.` | ordinary number plus original sentence punctuation; owner-attached empty-right forms preserve |
| `1.억` | `1.억` | owner-attached invalid preserve |
| `01.5` | `일쩜오` | leading-zero malformed decimal preserve cleanup target |
| `+01.5` | `+일쩜오` | leading-zero malformed decimal preserve cleanup target |
| `-01.5` | `-일쩜오` | leading-zero malformed decimal preserve cleanup target |
| `001.5` | `일쩜오` | leading-zero malformed decimal preserve cleanup target |
| `01.5억` | `01.5억` | owner-attached invalid preserve |
| `+01.5억` | `+01.5억` | owner-attached invalid preserve |
| `1,00.5` | `1,00.5` | invalid comma decimal preserve |
| `+1,00.5원` | `+1,00.5원` | owner-attached invalid comma preserve |

### 11.6 Segmented reading candidate conditions

A future segmented reading candidate must satisfy all conditions:

1. It is not inside protected/code-like/path/URL/JSON/backtick content.
2. No existing valid owner can claim the full surface.
3. It is not a canonical structural delimiter owner / exception surface.
4. It is not severe invalid numeric syntax.
5. Splitting on separator-runs leaves at least one non-empty segment.
6. Every non-empty segment can be read independently.
7. The separator-run can be emitted exactly as source text, without reading,
   deletion, or normalization.
8. The whole surface is never reconstructed as one numeric value.

Candidate examples:

| Surface | Current output | Future candidate only |
|---|---|---|
| `25..50` | `25..50` | historical proposal only: `이십오..오십` |
| `3..140` | `3..140` | historical proposal only: `삼..백사십` |
| `2,34` | `2,34` | `이,삼십사` |
| `2,,345` | `2,,345` | `이,,삼백사십오` |
| `2,34억` | `2,34억` | `이,삼십사억` |
| `2,,345억` | `2,,345억` | `이,,삼백사십오억` |
| `2천8백.28억` | `2천8백.28억` | `이천팔백.이십팔억` |
| `2천8백..28억` | `2천8백..28억` | `이천팔백..이십팔억` |
| `3백..4십만` | `3백..4십만` | `삼백..사십만` |
| `2천8백28..5억` | `2천8백28..5억` | open: Korean mixed fragment boundary safety |

The future candidate column is documentation only. Tests in this pass assert
only current production-source output.

### 11.7 Common segmenter design

The common segmenter should not produce readings. It should split a source
surface into alternating segment and separator-run tokens.

Examples:

```text
2천8백.28억
segment("2천8백")
separator(".")
segment("28억")

25..50억
segment("25")
separator("..")
segment("50억")

2,,345억
segment("2")
separator(",,")
segment("345억")
```

In the historical proposal, separator-runs would have been emitted exactly as
written; these are not current canonical outputs:

```text
2,,345 -> 이,,삼백사십오
25..50 -> 이십오..오십
```

Forbidden behavior:

```text
25..50 -> 이십오 점 오십
25..50 -> 이십오쩜오영
2,,345 -> 이삼백사십오
```

Middle empty segments may be represented by the separator-run, so `2,,345` can
be `segment("2")`, `separator(",,")`, `segment("345")`. Leading or trailing
empty segments preserve, for example `.5`, `+.5`, `1.`, and `1.억`.

### 11.8 Fragment reader design

The segmenter only produces fragments. A separate fragment reader decides
whether each segment can be read independently.

Arabic numeric fragments:

| Fragment | Reading candidate |
|---|---|
| `25` | `이십오` |
| `50` | `오십` |
| `140` | `백사십` |
| `345` | `삼백사십오` |

Korean mixed numeric fragments:

| Fragment | Reading candidate |
|---|---|
| `3백` | `삼백` |
| `4십만` | `사십만` |
| `2천8백` | `이천팔백` |
| `28억` | `이십팔억` |
| `3백4십` | `삼백사십` |

The Korean mixed fragment reader should reuse existing large-unit /
Korean mixed-unit parser helpers where possible. It must not duplicate number
reading logic.

Owner suffix fragments such as `만`, `억`, `조`, and `경` can remain attached to
a fragment when that fragment is independently readable:

```text
28억 -> 이십팔억
50억 -> 오십억
4십만 -> 사십만
```

The full malformed surface must still not be merged into a single numeric
value.

### 11.9 Implementation open decisions

Open decisions before any implementation:

1. Opt-in order:
   - standalone malformed dot/comma numeric: `25..50`, `3..140`, `2,34`,
     `2,,345`
   - large-unit-like malformed dot/comma numeric: `2,34억`,
     `2천8백.28억`, `3백..4십만`
   - owner-attached unit/percent/currency surfaces only after the above
2. Severe invalid threshold:
   - `01.5`, `+01.5`, `-01.5`, `001.5`, `+001.5`, and `-001.5` belong to the
     separate leading-zero malformed decimal preserve cleanup in section 5.1,
     not to segmented reading design.
   - `1,00.5`, `1.`, and `+.5` currently stay on the preserve side of the
     segmented-reading design.
3. Initial separator set:
   - candidate separators are `.`, `..`, `,`, and `,,`, but the final set must
     follow the structural delimiter inventory.
4. Fragment reader reuse:
   - decide how far the existing large-unit / Korean mixed-unit parser helpers
     can be reused without duplicating numeric reading logic.
5. Code-like audit gaps:
   - `file-25..50.txt`, `v25..50`, and `SKU25..50` currently do not all
     exact-preserve. A segmented fallback must not ship before these exclusion
     boundaries are explicit and tested.
   - `version-1.5` is now a managed dictionary numeric-code target.

## 12. Ordinary Decimal Fractional Zero 영 Canonicalization

This section records the phase-2 implementation of ordinary decimal
fractional-zero `영` canonicalization. It documents the renderer/helper paths,
included owners, exclusions, regression guards, and remaining follow-up work.

### 12.1 Purpose

Ordinary decimal-aware owners read every fractional zero as `영`, while keeping
integer zero as `영`:

```text
0.050 -> 영쩜영오영
1.50 -> 일쩜오영
25.00 -> 이십오쩜영영
1,000.50 -> 천쩜오영
```

`공` remains reserved for owner contexts that intentionally read digit
sequences, such as phone numbers, code / identifier routes, and existing
digit-sequence owners.

### 12.2 Implemented canonical state

Current production-source output is aligned for ordinary decimal-aware owners:

| Owner / route | Example | Current output | Zero state |
|---|---|---|---|
| standalone unsigned decimal | `0.050` | `영쩜영오영` | `영` |
| standalone signed decimal | `+0.050` | `플러스 영쩜영오영` | `영` |
| standalone signed decimal | `+25.50` | `플러스 이십오쩜오영` | trailing zero `영` |
| unsigned comma decimal | `1,000.50` | `천쩜오영` | valid standalone comma decimal |
| unit | `+1.50kg` | `플러스 일쩜오영 킬로그램` | `영` |
| percent | `0.050%` | `영쩜영오영 퍼센트` | `영` |
| KRW currency | `+1,000.50원` | `플러스 천쩜오영 원` | `영` |
| non-KRW currency | `USD0.050` | `영쩜영오영 달러` | `영` |
| temperature | `-0.050℃` | `영하 영쩜영오영도` | `영` |
| large-unit | `25.50억` | `이십오쩜오영 억` | `영` |
| tilde range | `0.050~1.00` | `영쩜영오영에서 일쩜영영` | `영` |
| colon / N:M | `1.50:2.0` | `일쩜오영 대 이쩜영` | `영` |
| multi-colon | `1.50:2.0:3.050` | `일쩜오영 대 이쩜영 대 삼쩜영오영` | `영` |

The audit file records implemented behavior, protected/invalid regressions,
leading-zero regressions, and source/production-source parity:

```text
tests/span_engine/test_decimal_fractional_zero_reading.py
```

All ordinary decimal canonical cases are regular assertions. No xfail is kept
for this policy after implementation.

### 12.3 Canonical policy

Canonical policy:

1. Ordinary decimal integer part `0` reads as `영`.
2. Ordinary decimal fractional digit `0` reads as `영`.
3. No ordinary decimal-aware owner should render fractional `0` as `공`.
4. Do not use global string replacement such as
   `reading.replace("공", "영")` or `reading.replace("영", "공")`.
5. Keep digit-sequence readers separate from ordinary decimal readers.

Included decimal-aware owners:

- standalone decimal
- signed decimal
- unit decimal
- percent decimal
- KRW currency decimal
- non-KRW currency decimal
- temperature decimal
- large-unit decimal
- tilde range decimal
- colon / `N:M` decimal
- multi-colon decimal
- numeric-delimited range-compatible unit decimal

Excluded owners / non-goals:

- standalone leading-zero malformed decimal preserve cleanup
- file-like/version-like/code-like protection gaps
- malformed numeric segmented reading design
- time-like leading-zero hour/minute behavior
- phone number digit reading
- code / identifier digit reading
- date reading
- time `HH:MM` / `HH:MM:SS` reading
- version-like preserve
- invalid numeric preserve policy
- JSON-like/path/URL/backtick protection
- hyphen range policy
- currency form expansion
- large-unit input coverage expansion

### 12.4 Leading-zero malformed decimal cleanup boundary

Ordinary decimal fractional-zero canonicalization treats only an integer part
that is exactly `0` as valid ordinary decimal zero:

```text
0.5
0.05
0.050
+0.050
-0.050
```

The following remain leading-zero malformed decimal cleanup targets or existing
owner cases and must not be newly read by ordinary decimal fractional-zero
canonicalization. The narrow preserve cleanup for standalone forms is defined
in section 5.1:

```text
01.5
001.5
+01.5kg
USD01.50
01.5~2
01.5:2
```

Current regression audit preserves existing behavior for:

```text
09:30 -> 아홉시 삼십분
00:30 -> 영시 삼십분
010-1234-5678 -> 공일공 일이삼사 오육칠팔
+82-10-1234-5678 -> 플러스 팔이 일공 일이삼사 오육칠팔
01 -> 01
001 -> 001
01.5 -> 일쩜오
+01.5 -> +일쩜오
-01.5 -> -일쩜오
001.5 -> 일쩜오
+001.5 -> +일쩜오
-001.5 -> -일쩜오
v01 -> v01
version-01 -> version-01
file-01.txt -> file-01.txt
```

These are existing outputs preserved by the exclusion policy, not new ordinary
decimal behavior.

### 12.5 Renderer path implementation

Renderer/helper paths after phase 2:

| Owner / route | Renderer path | Zero behavior |
|---|---|---|
| standalone unsigned decimal | `engine/span_engine/decimal.py` scans plain decimal and valid comma decimal surfaces, then uses `numeric_reading.read_decimal_fraction_digits` | `0` is `영` |
| signed decimal | `engine/span_engine/signed.py::parse_signed_numeric`; `_fractional_reading` delegates to `numeric_reading.read_decimal_fraction_digits` | `0` is `영` |
| unit / percent | `engine/span_engine/units.py::_plus_decimal_amount_reading`; `%` routes through simple unit owner | `0` is `영` |
| percent-point | `engine/span_engine/percent_point.py` uses `numeric_reading.read_number_text`; suffix `p`/`P` is owner-local | `0` is `영`; not the main `%` owner |
| KRW currency | `engine/span_engine/currency.py::_krw_amount_reading` delegates fractional digits to `numeric_reading.read_decimal_fraction_digits`; plus comma decimal KRW can also use the aligned signed/range numeric path | `0` is `영` |
| non-KRW currency | `engine/span_engine/currency.py::_amount_reading` calls `amount_reading.read_decimal_amount_text` | `0` is `영` |
| temperature | signed temperature uses `signed.py::_parse_temperature_numeric`, which calls `parse_signed_numeric`; unsigned degree-like temperature goes through unit owner | `0` is `영` |
| large-unit | `engine/span_engine/large_unit.py::_parse_numeric_large_unit_at` and mixed large-unit decimal call `signed.parse_signed_numeric` | `0` is `영` |
| tilde range | `engine/span_engine/range.py`; broad numeric-delimited route uses `_numeric_delimited_fractional_reading`, now delegated to `numeric_reading.read_decimal_fraction_digits` | `0` is `영` |
| colon / multi-colon | `engine/span_engine/range.py::render_numeric_delimited_number` for `colon_semantic_pair` and `multi_colon_numeric` | `0` is `영` |
| numeric-delimited range-compatible unit | `engine/span_engine/range.py` range-compatible unit/hyphen path uses `_range_reading` / numeric-delimited rendering | `0` is `영` for ordinary decimal parts |
| compound slash unit | `engine/span_engine/compound_unit.py::read_decimal_for_compound_unit_only` uses `amount_reading.SINO_DIGIT_READINGS` | `0` is `영` |
| phone/code/time-like | phone and code separator routes use digit-sequence readers (`phone.py`, `hyphen.py`, `code_separator.py`, `public_number.py`, `date_time.py::_digit_block_reading`) and time owner (`date_time.py`) | intentionally separate; `공` may be correct |

### 12.6 Unsigned comma decimal

The unsigned standalone comma decimal is now claimed when comma grouping is
valid:

```text
1,000.50 -> 천쩜오영
12,345.67 -> 일만이천삼백사십오쩜육칠
1,000,000.50 -> 백만쩜오영
```

Related signed forms remain claimed through signed numeric paths:

```text
+1,000.50 -> 플러스 천쩜오영
-2,500.75 -> 마이너스 이천오백쩜칠오
```

`scan_decimal_candidates` in `engine/span_engine/decimal.py` accepts
`\d{1,3}(?:,\d{3})+\.\d+` alongside plain decimal. Invalid comma grouping
remains preserve, for example `1,00.50 -> 1,00.50` and
`1,0000.50 -> 1,0000.50`.

Valid standalone decimal and valid comma decimal surfaces may claim their
numeric core before directly attached safe Korean particles such as `로` and
`으로`. The attached particle is original text, not a correction target in this
decimal path:

```text
117.8로 -> 백십칠쩜팔로
8,384.31로 -> 팔천삼백팔십사쩜삼일로
117.8으로 -> 백십칠쩜팔으로
1,00.5로 -> 1,00.5로
01.5로 -> 01.5로
+.5로 -> +.5로
/path/117.8로/log -> /path/117.8로/log
```

### 12.7 Test status

`tests/span_engine/test_decimal_fractional_zero_reading.py` currently has:

- regular assertions for standalone/signed/unit/percent/currency/temperature/
  large-unit/range/colon/multi-colon canonical policy
- protected context regression cases
- invalid/malformed preserve cases
- leading-zero owner regression cases
- complex sentence cases for ordinary numeric, unit/percent, currency,
  temperature, large-unit, tilde range, and colon/multi-colon
- source and production-source parity for representative ordinary decimal cases

No xfail remains for the ordinary decimal fractional-zero policy.

### 12.8 Runtime probe status

`scripts/probes/decimal_fractional_zero.py` covers representative
ordinary decimal owner groups, protected contexts, invalid/malformed preserve
surfaces, and leading-zero/digit-owner regressions.

Default runners:

- source
- production_source

Optional runners:

- `--binary ./dist/tts_preprocessor`
- `--api http://host:port`

The optional binary/API matrix uses the shared `scripts/probes/runtime_matrix.py`
helper. A stale binary can fail until rebuilt through the normal release
workflow; this policy section does not require running build scripts directly.

## 13. Basic arithmetic expression matrix

The arithmetic owner is numeric/fraction-only, full-consume, read-only (no
calculation), and subordinate to registered structured/protected owners.

| Type | Surface | Canonical / route |
|---|---|---|
| add | `3+4` | `삼 더하기 사` |
| subtract | `3.2 - 5.7` | `삼쩜이 빼기 오쩜칠` |
| multiply `x` | `4.5 x 3` | `사쩜오 곱하기 삼` |
| multiply sign | `4.5×3` | `사쩜오 곱하기 삼` |
| divide | `8÷2` | `팔 나누기 이` |
| signed operands | `+3.4 x -2.3` | `플러스 삼쩜사 곱하기 마이너스 이쩜삼` |
| equality, vowel | `3+4=7` | `삼 더하기 사는 칠` |
| equality, consonant | `3+6=9` | `삼 더하기 육은 구` |
| fraction operands | `1/3+2/3` | `삼분의 일 더하기 삼분의 이` |
| slash standalone | `8/2` | existing fraction: `이분의 팔` |
| exact spaced subtract | `3 - 4` | `삼 빼기 사` |
| bare compact hyphen | `3-4`, `12-15`, `123-456` | atomic preserve |
| mixed compact subtract | `3-2+1`, `2×4-3` | `삼 빼기 이 더하기 일`, `이 곱하기 사 빼기 삼` |
| equation compact subtract | `4-3=1` | `사 빼기 삼은 일` |
| pure compact hyphen chain | `10-3-2` | existing digit-block: `일공 삼 이` |
| leading-zero code | `01-02` | existing digit-block: `공일 공이` |
| long-block code | `1234-56` | existing digit-block: `일이삼사 오육` |
| short hyphen year-month | `2025-01` | existing source-exact preserve |
| compact decimal/signed-range ambiguity | `1.5-2`, `-2.480-3.24` | existing atomic preserve |
| registered range | `12-15장` | existing range: `십이에서 십오 장` |
| registered phone | `1234-5678` | existing phone digit-block reading |
| registered managed code | `version-2` | existing managed-code reading `버전 투` |
| invalid operand | `3 + .5` | atomic preserve |
| repeated operator | `3++4` | atomic preserve |
| identifier expression | `A+B` | protected preserve |
| unsupported star | `3*4` | atomic preserve |
| unsupported uppercase X | `3X4` | atomic preserve |
| unsupported unit operand | `3kg+4kg` | atomic preserve |
| unsupported parenthesized arithmetic | `(3+4)×2` | full source preserve |
| unsupported numeric function | `sqrt(4)` | full source preserve |
| protected path | `/path/3+4/log` | protected preserve |

Owner contract:

- valid owner: `basic_arithmetic_expression` /
  `BASIC_ARITHMETIC_EXPRESSION_SURFACE` /
  `basic_arithmetic_expression_full_consume_gate`
- invalid fallback: `preserve` /
  `INVALID_BASIC_ARITHMETIC_EXPRESSION_PRESERVE_SURFACE` /
  `invalid_basic_arithmetic_expression_preserve`
- binary aliases: exactly `+`, `-`, `×`, lower-case numeric `x`, `÷`
- excluded aliases: `X`, `*`, binary `/`
- binary-minus spacing: exact one-space form unless another supported operator
  or one valid equality establishes a full-consumed arithmetic expression
- bare compact `N-N`, asymmetric minus spacing, and pure compact hyphen chains
  do not enter arithmetic
- other operator spacing: zero or one ASCII space on each side
- equality: zero or one, generated `은/는` from the final left operand reading
- protected/code-like and registered structured owners win before arithmetic
- signed/fraction/decimal/generic numeric fallback cannot reenter a claimed or
  atomically preserved expression

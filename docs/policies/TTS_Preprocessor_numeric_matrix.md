# TTS Preprocessor Numeric Matrix Policy

## 1. Purpose

This document audits the current numeric matrix for the span-default production
path. It records current behavior, intended guard boundaries, and open policy
decisions without changing transform semantics.

The goal is to keep common standalone numeric parsing separate from
owner-attached numeric parsing. Owner-specific exceptions must full-claim their
surface or preserve it; they must not rely on broad internal digit fallback.

## 2. Official production validation path

The official production source validation path is:

```text
engine.main.transform_with_rollout(text, mode="span_default", include_debug=False)
```

The API runtime reaches the same transform through the packaged PyInstaller
binary:

```text
api.server -> api.binary_runtime -> TTS_PREPROCESSOR_BINARY
-> packaged binary -> bin/build_binary_entrypoint.py
-> engine.main.transform_with_rollout(mode="span_default")
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
| `25.50` | `이십오쩜오영` | unsigned standalone decimal trailing zero uses `영` |
| `+25.50` | `플러스 이십오쩜오영` | signed standalone decimal trailing zero uses `영` |
| `-25.50` | `마이너스 이십오쩜오영` | signed standalone decimal trailing zero uses `영` |
| `1,000.50` | `천쩜오영` | valid unsigned comma decimal |
| `+1,000.50` | `플러스 천쩜오영` | signed comma decimal |
| `-2,500.75` | `마이너스 이천오백쩜칠오` | signed comma decimal |

Current standalone invalid/malformed forms:

| Surface | Current output | Partial fallback | Follow-up |
|---|---|---|---|
| `01` | `01` | no | none |
| `+01` | `+01` | no | none |
| `-01` | `-01` | no | none |
| `01.5` | `일쩜오` | yes | audit whether malformed decimal should preserve |
| `+01.5` | `+일쩜오` | yes | audit signed malformed decimal preservation |
| `-01.5` | `-일쩜오` | yes | audit signed malformed decimal preservation |
| `1,00` | `1,00` | no | none |
| `1,00.5` | `1,00.5` | no | none |
| `+1,00.5` | `+1,00.5` | no | none |
| `+.5` | `+.5` | no | none |
| `-.5` | `-.5` | no | none |
| `1.` | `일.` | yes | audit whether bare trailing dot should preserve |
| `+1.` | `+1.` | no | none |
| `3..140` | `삼..백사십` | yes | audit malformed dotted numeric preservation |
| `1,0000` | `1,0000` | no | none |

## 4. Owner-attached numeric matrix

| Owner | Valid numeric forms | Sign | Decimal | Comma | Spacing | Invalid handling | Trailing zero state |
|---|---|---|---|---|---|---|---|
| unit | integer, decimal, comma integer/decimal for supported unit policy; owner-local meter aliases include `m` and fullwidth Latin `ｍ` | `+`/`-` plus owner-local dash-like minus aliases such as `–` only under full-claim signed unit conditions | yes | yes for allowed unit matrix | no space or one ASCII space | malformed numeric+unit preserves as full surface, e.g. `+.5kg`, `+.5ｍ`, `1,00kg`, `1,00ｍ`, `–.5%`, `––2.03%` | ordinary decimal fractional zero uses `영`, e.g. `25.50kg -> 이십오쩜오영 킬로그램` |
| counter | integer/comma integer and owner-approved mixed Korean-Arabic numeric core followed by registered counter noun, e.g. `6400명`, `6,400명`, `6천400명` | no arithmetic sign semantics | yes through the registered decimal suffix owner; integer counter behavior is unchanged | yes for valid integer/comma integer; mixed compact core must parse fully | no space or one ASCII space before counter; generated space follows counter policy | unsafe mixed counter tails preserve and broad internal digit fallback is blocked, e.g. `6천400명abc`, `6천400명/log`, `4.3명abc`; standalone compact `6천400` preserves in this phase | decimal counter suffixes use ordinary decimal/Sino reading, e.g. `4.3명 -> 사쩜삼 명`; integer counters retain native/hybrid/Sino rules |
| multiplier | unsigned integer/comma integer and unsigned decimal/comma decimal followed by Korean multiplier noun `배`, e.g. `3배`, `3 배`, `1.5배`, `1,000.5 배` | no signed multiplier in this phase | yes | yes for valid comma integer/decimal | no space or one ASCII space before `배`; renders one generated space before original `배` | malformed/signed forms are not claimed by multiplier in this phase; protected/code-like contexts preserve first | decimal uses ordinary Sino decimal reading; integer `1..39` uses native/hybrid counter-style reading and `40+` uses Sino |
| duration/year-period | duration `시간`/`분`; registered decimal duration-like suffixes such as `일`, `주`, `개월`, `년`; narrow exact `N년간` year-period form | negative duration preserves | yes for valid decimal registered duration/time suffixes | yes where duration numeric reader accepts | owner-scoped; decimal registered suffixes render one generated space before the original suffix | unsafe exact year-period tails preserve, e.g. `1년간abc`; unsafe decimal suffix tails preserve, e.g. `4.5주abc` | decimal duration/time suffixes use ordinary decimal/Sino reading, e.g. `1.5분 -> 일쩜오 분`, `4.5주 -> 사쩜오 주` |
| registered numeric suffix | registered Korean numeric suffix inventory, including explicit numeric suffixes such as `차`, `과`, `선` | no arithmetic sign semantics in this branch | yes for valid decimal numeric core attached to a registered/approved suffix | yes for valid comma decimal | no space or one ASCII space before suffix; renders one generated space before original suffix | malformed decimal and unsafe/code-like tails preserve or are not claimed; arbitrary Hangul suffixes are not eligible | ordinary decimal/Sino reading + original suffix, e.g. `1.5차 -> 일쩜오 차` |
| percent | integer, decimal, slash fraction for percent-point `%p`/`%P`; `%` supports signed decimal-aware forms | `+`/`-` plus owner-local dash-like minus aliases such as `–` only under full-claim signed percent or percent-point conditions | yes | yes where numeric reader accepts | no space or one ASCII space | malformed percent/percent-point preserves; dash-like invalid forms preserve, e.g. `–1,00.5%` | ordinary decimal fractional zero uses `영`, e.g. `25.50% -> 이십오쩜오영 퍼센트`, `–2.03% -> 마이너스 이쩜영삼 퍼센트` |
| temperature / degree | signed temperature, signed degree, unsigned degree-like unit surfaces | signed temperature uses `영상/영하`; bare degree has separate policy; dash-like minus aliases are owner-local under full-claim signed temperature/degree conditions | yes | signed parser accepts comma where valid | optional one space for signed unit variants | malformed signed temperature preserves, e.g. `+.5℃` | ordinary decimal fractional zero uses `영`, e.g. `25.50℃ -> 이십오쩜오영도`, `+25.50℃ -> 영상 이십오쩜오영도` |
| KRW currency | registered KRW code/symbol/suffix forms | `+`/`-` supported around registered markers | yes | yes | no space or one ASCII space | invalid comma/leading-zero forms preserve; no partial fallback | ordinary decimal fractional zero uses `영`, e.g. `KRW25.50 -> 이십오쩜오영 원` |
| non-KRW currency | registered USD/EUR/JPY/GBP forms within current currency matrix | partial sign support by marker form | USD/EUR decimal currently allowed; JPY integer-focused | yes where amount parser accepts | no space or one ASCII space | unsupported or malformed currency tokens preserve | current decimal fractional zero is `영`, e.g. `USD 25.50 -> 이십오쩜오영 달러` |
| large-unit | Arabic integer/comma integer, signed decimal, Arabic-Hangul/Korean mixed full surface | `+`/`-` for decimal large-unit | yes for decimal large-unit lexical form | yes | tail/currency noun policies are owner-scoped | invalid comma/dot/mixed-unit structures preserve; no internal digit fallback | decimal large-unit uses `영`, e.g. `25.50억 -> 이십오쩜오영 억` |
| tilde range | two numeric sides with tilde-like delimiter; optional compatible suffix/tail; range-compatible unit aliases include meter `ｍ` | limited signed range forms in current policy | yes | yes for valid numeric blocks | suffix/tail policy owner-scoped | malformed range preserves; no partial fallback for invalid owner surface, e.g. `1~~2ｍ` | current range decimal output uses `영`, e.g. `1.50~2.50테스트 -> 일쩜오영에서 이쩜오영 테스트` |
| colon / N:M | broad non-time-like `N:M`; multi-colon supported separately | signed decimal in approved paths | yes | yes | Korean tail spacing owner-scoped | invalid/multi-delimiter/time-like/code-like guards preserve | ordinary decimal fractional zero uses `영`, e.g. `3:4.50테스트 -> 삼 대 사쩜오영 테스트` |
| Korean `대` score pair | valid readable numeric operands already supported by `span_default` numeric owners as standalone numeric expressions; plain integer compact `N대M` keeps compact score reading | ASCII `+`/`-` signed integer/decimal operands where standalone signed owner validates them | yes | yes | supports `LEFT 대 RIGHT`, `LEFT대RIGHT`, `LEFT대 RIGHT`; `LEFT 대RIGHT` remains unsupported | malformed/unsafe operands and protected/code-like contexts are not claimed; right operand attached to registered owner suffix/unit/currency/percent/duration/multiplier/counter surface blocks this owner | ordinary decimal fractional zero follows the underlying standalone numeric reading; non-plain operands render spaced around `대`, e.g. `2.1대1.5 -> 이쩜일 대 일쩜오` |
| compound slash unit | exact registered compound slash unit surfaces, including `/` and owner-local `／` aliases; examples include `km/h`, `m/s`, `km/L`, `mg/L`, `㎎/L`, `mg/dL`, `MB/s` | no signed compound slash broadening in this phase | yes for registered slash surfaces that already support integer numeric cores | yes for valid comma integer/decimal through the compound owner parser | no space or one ASCII space before the full registered suffix | malformed numeric cores, unregistered slash pairs, unsafe tails, spaced slash boundaries, URL/path/protected contexts preserve; no partial `5.6km` rewrite | ordinary decimal/Sino reading reuses the unchanged template, e.g. `5.6km/h -> 시속 오쩜육 킬로미터`, `3.2mg/L -> 리터당 삼쩜이 밀리그램` |
| hyphen restricted range | approved `N-M + range-compatible unit`, e.g. `1-2kg` | broad signed hyphen ranges out of scope | decimal broad signed hyphen remains out of scope | narrow owner-specific support only | attached compatible unit required for range reading | arbitrary `1-2`, `1-2테스트`, `+1.5-2kg` preserve | follows owner parser when valid; no broad trailing-zero policy |
| phone / hyphen digit blocks | phone-like exact forms and multi-block digit routes | no arithmetic sign semantics | no decimal phone | no comma phone | hyphen-separated digit blocks | unsafe/code-like/path contexts preserve | digit-by-digit; not decimal trailing-zero policy |

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

Standalone malformed numeric behavior is not fully aligned yet. Current
partial fallback cases such as `01.5 -> 일쩜오` and `3..140 -> 삼..백사십`
are recorded as audit findings rather than changed in this pass.

## 6. Partial fallback policy

The owner-attached policy is stricter than the standalone fallback policy:

1. If an owner can structurally identify a numeric-unit/currency/range/large-unit
   surface but the internal numeric form is invalid, the owner should claim a
   preserve surface.
2. Broad internal digit fallback must not rewrite inside invalid owner surfaces.
3. Protected spans outrank owner claims.
4. Standalone malformed numeric partial fallback is a separate follow-up audit.

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
- line/case/version/file/scripture-like colon contexts

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
09:30 -> 구시 삼십분
3:04 -> 세시 사분
13:05 -> 십삼시 오분
24:09 -> 이십사시 구분
```

This is implemented for bare and ordinary non-protected contexts. Two-digit
leading-zero hours use the stage-2 canonical shown above: `00` is `영`, `01` is
`한`, and `02..09` use Sino readings such as `09:30 -> 구시 삼십분`.

### 9.4 Ambiguous time-like target policy

`H:MM` or `HH:MM` with hour `0..24` and minute `10..59` can be time, ratio, or
score depending on context.

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

Ratio/score, scripture-like, line/case/version/file, protected, URL/path/JSON/
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
2. Standalone malformed numeric partial fallback:
   - Audit current `01.5`, `+01.5`, `-01.5`, `1.`, and `3..140`.
3. Non-KRW currency trailing zero targeted fix.
4. Time-like `숫자:숫자` binary/API probe and final policy cleanup.
5. Hyphen broad expansion remains a non-goal unless separately approved.

## 11. Malformed Numeric Segmented Reading Policy Analysis

This section is a policy analysis and audit inventory only. It does not define
an implementation change and it is not a large-unit-only policy. The target
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
| colon-like | strong time-like, explicit time context, ambiguous time-like preserve, semantic `N:M`, broad non-time-like `N:M`, multi-colon, timecode-like multi-colon preserve, invalid colon fallback block, scripture / line / case / version context preserve |
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
| `09:30` | `구시 삼십분` | strong time-like |
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
| `1~2` | `일에서 이` | tilde range |
| `1~~2` | `1~~2` | invalid tilde fallback block |

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
| `version-1.5` | `브이 이 알 에스 아이 오 엔 일쩜오` | current audit gap; version-like exclusion needs explicit policy/implementation alignment before any segmenter |
| `v25..50` | `v25..오십` | current audit gap; code-like prefix exclusion must outrank segmented fallback |
| `SKU25..50` | `SKU25..오십` | current audit gap; code-like token exclusion must outrank segmented fallback |

These gaps are recorded only as audit findings. This pass does not change
protected-span or code-like behavior.

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
| `1.` | `일.` | current standalone partial fallback gap; severe-invalid candidate for future preserve |
| `1.억` | `1.억` | owner-attached invalid preserve |
| `01.5` | `일쩜오` | current standalone leading-zero partial fallback gap |
| `+01.5` | `+일쩜오` | current signed leading-zero partial fallback gap |
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
| `25..50` | `이십오..오십` | `이십오..오십` |
| `3..140` | `삼..백사십` | `삼..백사십` |
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

Separator-runs are emitted exactly as written:

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
   - `01.5`, `+01.5`, `1,00.5`, `1.`, and `+.5` currently stay on the
     preserve side of the design.
3. Initial separator set:
   - candidate separators are `.`, `..`, `,`, and `,,`, but the final set must
     follow the structural delimiter inventory.
4. Fragment reader reuse:
   - decide how far the existing large-unit / Korean mixed-unit parser helpers
     can be reused without duplicating numeric reading logic.
5. Code-like audit gaps:
   - `file-25..50.txt`, `version-1.5`, `v25..50`, and `SKU25..50` currently do
     not all exact-preserve. A segmented fallback must not ship before these
     exclusion boundaries are explicit and tested.

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

- leading-zero ownership or malformed fallback behavior
- time-like leading-zero hour/minute behavior
- phone number digit reading
- code / identifier digit reading
- date reading
- time `HH:MM` / `HH:MM:SS` reading
- version-like preserve
- malformed numeric segmented reading
- invalid numeric preserve policy
- JSON-like/path/URL/backtick protection
- hyphen range policy
- currency form expansion
- large-unit input coverage expansion

### 12.4 Leading-zero non-goal

This policy treats only an integer part that is exactly `0` as valid ordinary
decimal zero:

```text
0.5
0.05
0.050
+0.050
-0.050
```

The following remain leading-zero malformed decimal or existing owner cases and
must not be newly read by this canonicalization:

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
09:30 -> 구시 삼십분
00:30 -> 영시 삼십분
010-1234-5678 -> 공일공 일이삼사 오육칠팔
+82-10-1234-5678 -> 플러스 팔이 일공 일이삼사 오육칠팔
01 -> 01
001 -> 001
01.5 -> 일쩜오
+01.5 -> +일쩜오
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
| legacy pipeline | `engine/parsers/numeric_date_parsers.py::read_decimal_ko` and `engine/pipeline/transform_engine.py` legacy helpers read fractional digits with `DIGIT_KO`; production `span_default` primarily uses span-engine owners, with large-unit pre-rule protection calling span-engine large-unit scanner/parser | legacy helper `0` is `영`; large-unit legacy protection follows the aligned span-engine large-unit behavior |
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

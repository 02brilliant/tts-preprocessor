# TTS Preprocessor Managed Dictionary Policy

## 1. Purpose

Managed dictionary entries are policy-approved fixed lexical exceptions. They
are not broad acronym fallback, broad code reading, numeric fallback, or a
general English-to-Korean transcription layer.

This document is the canonical inventory and status ledger for dictionary-based
fixed lexical correction. It records which surfaces are current production
requirements, which surfaces are conditional, and which surfaces remain pending,
future-only, or historical-only.

This document by itself does not change production code. Any `current` entry
missing from `span_default` is a production drift item.

## 2. Relationship to Canonical Policy

`docs/policies/TTS_Preprocessor_policy.md` remains the single canonical policy
for the full preprocessor. This document owns the managed dictionary surface
inventory, readings, status labels, compound rendering decisions, and
dictionary-specific implementation/test contract.

If a dictionary table in the main policy appears to conflict with this document,
use this document to decide inventory status and use the main policy for shared
owner, protection, validation, and runtime rules.

The official production source path remains:

```text
engine.main.transform(text)
```

## 3. Managed Dictionary vs General Fallback

Managed dictionary entries:

- are explicit fixed lexical exceptions approved by policy;
- must full-claim the approved surface when their match conditions are met;
- must run before acronym, code, numeric, and segmented fallback;
- must not be inferred from neighboring letters or digits;
- must not expand broad acronym+number fallback;
- must not rewrite unsafe partial tokens such as `USB300`, `APIv2`, or
  `A12.3B`.

General fallback remains separate:

- uppercase acronym fallback may spell safe all-caps tokens that are not
  managed dictionary entries;
- code separator owners may read explicitly supported code-like surfaces;
- numeric owners may read supported numeric surfaces;
- fallback behavior must not be used to claim that a managed dictionary entry is
  implemented unless the dictionary owner or an explicitly documented
  conditional owner owns the surface.

## 4. Claim and Protection Rules

Managed dictionary claim rules:

1. Match only at safe token boundaries unless a row explicitly defines a
   stricter match type.
2. Prefer longest exact managed dictionary match.
3. Claim before acronym fallback, code fallback, numeric fallback, and segmented
   malformed numeric fallback.
4. Full-claim the managed surface. Do not produce partial managed dictionary
   rewrites.
5. Preserve URL, path, email, JSON-like string value, inline backtick, fenced
   code, shell/code-like, and square bracket interior contexts.
6. Keep safe post-surface particle handling separate from dictionary matching.
7. Do not use this inventory to add arbitrary unknown unit, currency, product,
   or organization readings.

A no-Hangul input may enter the core transform only when the entire input is composed of exact current managed dictionary entries and approved separators/whitespace. This exception does not apply to English prose, mixed unknown tokens, code-like tokens, path/URL/email/JSON/backtick/square bracket contexts, or larger alnum tokens such as APIv2 and JSONPath.

## 5. Status Taxonomy

| Status | Meaning |
|---|---|
| `current` | Canonical fixed dictionary entry that `span_default` production must apply. |
| `current_with_condition` | Canonical behavior, but only under a whitelist, context, gate, suffix, or full-claim condition. |
| `pending_policy_decision` | Mentioned in policy or historical code, but current production status is not decided. |
| `conflict` | Reading or ownership conflicts exist inside policy, between policy and span, or between historical and span. |
| `future_candidate` | Candidate for future support; not a current production contract. |
| `historical_only_or_deprecated` | Present in historical data or historical policy, but not current `span_default` target behavior. |

## 6. Current Managed Dictionary Entries

These rows are canonical fixed lexical entries. Every row must be present in the
span production managed dictionary and covered by production-path tests.

| Surface | Reading | Status | Match type | Boundary | Notes |
|---|---|---|---|---|---|
| `2G` | 투지 | current | exact | safe token boundary | Network generation term; does not apply inside frequency/unit tokens. |
| `3G` | 쓰리지 | current | exact | safe token boundary | Network generation term; does not apply inside frequency/unit tokens. |
| `4G` | 포지 | current | exact | safe token boundary | Network generation term; does not apply inside frequency/unit tokens. |
| `4K` | 포케이 | current | exact | safe token boundary | Fixed media/display term. |
| `5G` | 파이브지 | current | exact | safe token boundary | Network generation term; `5GHz` remains owned by the frequency/unit owner. |
| `6G` | 식스지 | current | exact | safe token boundary | Network generation term; does not apply inside frequency/unit tokens. |
| `8K` | 에잇케이 | current | exact | safe token boundary | Fixed media/display term. |
| `AFC` | 에이에프씨 | current | exact | safe token boundary | Fixed sports organization term. |
| `API` | 에이피아이 | current | exact | safe token boundary | Fixed technical term. |
| `ASEAN` | 아세안 | current | exact | safe token boundary | Fixed institution term. |
| `ASR` | 에이에스알 | current | exact | safe token boundary | Fixed speech term. |
| `B2B` | 비투비 | current | exact | safe token boundary | Fixed business term. |
| `B2C` | 비투씨 | current | exact | safe token boundary | Fixed business term. |
| `BOJ` | 비오제이 | current | exact | safe token boundary | Fixed finance institution term. |
| `BOK` | 비오케이 | current | exact | safe token boundary | Fixed finance institution term. |
| `BPS` | 비피에스 | current | exact | safe token boundary | Fixed finance term. |
| `CLI` | 씨엘아이 | current | exact | safe token boundary | Fixed technical term. |
| `CPI` | 씨피아이 | current | exact | safe token boundary | Fixed economy term. |
| `CSS` | 씨에스에스 | current | exact | safe token boundary | Fixed web term. |
| `CSV` | 씨에스브이 | current | exact | safe token boundary | Fixed file/data term. |
| `DB` | 디비 | current | exact | safe token boundary | Fixed database term. |
| `DBMS` | 디비엠에스 | current | exact | safe token boundary | Fixed database term. |
| `DNS` | 디엔에스 | current | exact | safe token boundary | Fixed network term. |
| `DOC` | 디오씨 | current | exact | safe token boundary | Fixed file term. |
| `DOCX` | 디오씨엑스 | current | exact | safe token boundary | Fixed file term. |
| `DOW` | 다우 | current | exact | safe token boundary | Fixed finance index term. |
| `EBS` | 이비에스 | current | exact | safe token boundary | Fixed broadcast term. |
| `ECB` | 이씨비 | current | exact | safe token boundary | Fixed finance institution term. |
| `EPS` | 이피에스 | current | exact | safe token boundary | Fixed finance term. |
| `ETF` | 이티에프 | current | exact | safe token boundary | Fixed finance product term. |
| `ETN` | 이티엔 | current | exact | safe token boundary | Fixed finance product term. |
| `FAO` | 에프에이오 | current | exact | safe token boundary | Fixed institution term. |
| `FAQ` | 에프에이큐 | current | exact | safe token boundary | Fixed help term. |
| `FOMC` | 에프오엠씨 | current | exact | safe token boundary | Fixed finance term. |
| `FTA` | 에프티에이 | current | exact | safe token boundary | Fixed policy/economy term. |
| `Fed` | 연준 | current | exact | safe token boundary | Fixed finance institution term. |
| `FHD` | 에프에이치디 | current | exact | safe token boundary | Fixed media term. |
| `FIFA` | 피파 | current | exact | safe token boundary | Fixed sports organization term. |
| `GDP` | 지디피 | current | exact | safe token boundary | Fixed economy term. |
| `GPT` | 지피티 | current | exact | safe token boundary | Fixed AI/product acronym term. |
| `GPU` | 지피유 | current | exact | safe token boundary | Fixed hardware term. |
| `GUI` | 지유아이 | current | exact | safe token boundary | Fixed UI term. |
| `GraphQL` | 그래프큐엘 | current | exact | safe token boundary | Fixed technical term. |
| `HD` | 에이치디 | current | exact | safe token boundary | Fixed media term. |
| `HDD` | 에이치디디 | current | exact | safe token boundary | Fixed hardware term. |
| `HDMI` | 에이치디엠아이 | current | exact | safe token boundary | Fixed hardware term. |
| `HDR` | 에이치디알 | current | exact | safe token boundary | Fixed media term. |
| `HTML` | 에이치티엠엘 | current | exact | safe token boundary | Fixed web term. |
| `HTTP` | 에이치티티피 | current | exact | safe token boundary | Fixed web protocol term. |
| `HTTPS` | 에이치티티피에스 | current | exact | safe token boundary | Fixed web protocol term. |
| `HWP` | 에이치더블유피 | current | exact | safe token boundary | Fixed file term. |
| `IAEA` | 아이에이이에이 | current | exact | safe token boundary | Fixed institution term. |
| `IDE` | 아이디이 | current | exact | safe token boundary | Fixed development tool term. |
| `IMF` | 아이엠에프 | current | exact | safe token boundary | Fixed institution term. |
| `IOC` | 아이오씨 | current | exact | safe token boundary | Fixed sports organization term. |
| `IPO` | 아이피오 | current | exact | safe token boundary | Fixed finance term. |
| `IP` | 아이피 | current | exact | safe token boundary | Fixed network term. |
| `IPTV` | 아이피티비 | current | exact | safe token boundary | Fixed media/network term. |
| `JS` | 제이에스 | current | exact | safe token boundary | Fixed web term. |
| `JSON` | 제이슨 | current | exact | safe token boundary | Fixed data format term. |
| `JTBC` | 제이티비씨 | current | exact | safe token boundary | Fixed broadcast term. |
| `JWT` | 제이더블유티 | current | exact | safe token boundary | Fixed security token term. |
| `K-POP` | 케이팝 | current | exact | safe token boundary | Fixed media term. |
| `KBL` | 케이비엘 | current | exact | safe token boundary | Fixed sports organization term. |
| `KBO` | 케이비오 | current | exact | safe token boundary | Fixed sports organization term. |
| `KBS` | 케이비에스 | current | exact | safe token boundary | Fixed broadcast term. |
| `KFA` | 케이에프에이 | current | exact | safe token boundary | Fixed sports organization term. |
| `KOSDAQ` | 코스닥 | current | exact | safe token boundary | Fixed finance index. |
| `KOSPI` | 코스피 | current | exact | safe token boundary | Fixed finance index. |
| `KTX` | 케이티엑스 | current | exact | safe token boundary | Fixed rail service acronym. |
| `LAN` | 랜 | current | exact | safe token boundary | Fixed network term. |
| `LLM` | 엘엘엠 | current | exact | safe token boundary | Fixed AI term. |
| `LTE` | 엘티이 | current | exact | safe token boundary | Fixed network term. |
| `MBC` | 엠비씨 | current | exact | safe token boundary | Fixed broadcast term. |
| `MFN` | 엠에프엔 | current | exact | safe token boundary | Fixed policy/economy term. |
| `MLB` | 엠엘비 | current | exact | safe token boundary | Fixed sports league term. |
| `MoM` | 엠오엠 | current | exact | safe token boundary | Fixed finance comparison term. |
| `NASA` | 나사 | current | exact | safe token boundary | Fixed institution term. |
| `NASDAQ` | 나스닥 | current | exact | safe token boundary | Fixed finance index. |
| `NATO` | 나토 | current | exact | safe token boundary | Fixed institution term. |
| `NBA` | 엔비에이 | current | exact | safe token boundary | Fixed sports league term. |
| `NFC` | 엔에프씨 | current | exact | safe token boundary | Fixed network/payment term. |
| `NFL` | 엔에프엘 | current | exact | safe token boundary | Fixed sports league term. |
| `NHL` | 엔에이치엘 | current | exact | safe token boundary | Fixed sports league term. |
| `NLP` | 엔엘피 | current | exact | safe token boundary | Fixed AI/language term. |
| `NPU` | 엔피유 | current | exact | safe token boundary | Fixed hardware term. |
| `NoSQL` | 노에스큐엘 | current | exact | safe token boundary | Fixed database term. |
| `OAuth` | 오어스 | current | exact | safe token boundary | Fixed auth term. |
| `OECD` | 오이씨디 | current | exact | safe token boundary | Fixed institution/economy term. |
| `OPEC` | 오펙 | current | exact | safe token boundary | Fixed institution term. |
| `OS` | 오에스 | current | exact | safe token boundary | Fixed technical term. |
| `OTT` | 오티티 | current | exact | safe token boundary | Fixed media term. |
| `PBR` | 피비알 | current | exact | safe token boundary | Fixed finance term. |
| `PCIe` | 피씨아이이 | current | exact | safe token boundary | Fixed hardware term. |
| `PDF` | 피디에프 | current | exact | safe token boundary | Fixed file term. |
| `PER` | 피이알 | current | exact | safe token boundary | Fixed finance term. |
| `PPI` | 피피아이 | current | exact | safe token boundary | Fixed economy term. |
| `PPT` | 피피티 | current | exact | safe token boundary | Fixed file term. |
| `PPTX` | 피피티엑스 | current | exact | safe token boundary | Fixed file term. |
| `Q&A` | 큐앤에이 | current | exact | safe token boundary | Fixed question-answer term. |
| `QoQ` | 큐오큐 | current | exact | safe token boundary | Fixed finance comparison term. |
| `RAM` | 램 | current | exact | safe token boundary | Fixed hardware term. |
| `release` | 릴리즈 | current | exact | safe token boundary | Fixed software/release term. |
| `REST` | 레스트 | current | exact | safe token boundary | Fixed technical term. |
| `ROE` | 알오이 | current | exact | safe token boundary | Fixed finance term. |
| `ROM` | 롬 | current | exact | safe token boundary | Fixed hardware term. |
| `S&P` | 에스앤피 | current | exact | safe token boundary | Fixed finance index. |
| `SBS` | 에스비에스 | current | exact | safe token boundary | Fixed broadcast term. |
| `SDK` | 에스디케이 | current | exact | safe token boundary | Fixed technical term. |
| `SDR` | 에스디알 | current | exact | safe token boundary | Fixed media term. |
| `SQL` | 에스큐엘 | current | exact | safe token boundary | Fixed database term. |
| `SSD` | 에스에스디 | current | exact | safe token boundary | Fixed hardware term. |
| `SSH` | 에스에스에이치 | current | exact | safe token boundary | Fixed network protocol term. |
| `SSL` | 에스에스엘 | current | exact | safe token boundary | Fixed security protocol term. |
| `STT` | 에스티티 | current | exact | safe token boundary | Fixed speech term. |
| `TCP` | 티씨피 | current | exact | safe token boundary | Fixed network protocol term. |
| `TLS` | 티엘에스 | current | exact | safe token boundary | Fixed security protocol term. |
| `TSV` | 티에스브이 | current | exact | safe token boundary | Fixed data format term. |
| `TTS` | 티티에스 | current | exact | safe token boundary | Fixed speech term. |
| `TXT` | 티엑스티 | current | exact | safe token boundary | Fixed file term. |
| `UDP` | 유디피 | current | exact | safe token boundary | Fixed network protocol term. |
| `UHD` | 유에이치디 | current | exact | safe token boundary | Fixed media term. |
| `UI` | 유아이 | current | exact | safe token boundary | Fixed technical term. |
| `UN` | 유엔 | current | exact | safe token boundary | Fixed institution term. |
| `UNESCO` | 유네스코 | current | exact | safe token boundary | Fixed institution term. |
| `UNICEF` | 유니세프 | current | exact | safe token boundary | Fixed institution term. |
| `URI` | 유알아이 | current | exact | safe token boundary | Fixed web term. |
| `URL` | 유알엘 | current | exact | safe token boundary | Fixed web term. |
| `UWB` | 유더블유비 | current | exact | safe token boundary | Fixed network term. |
| `UX` | 유엑스 | current | exact | safe token boundary | Fixed technical term. |
| `VOD` | 브이오디 | current | exact | safe token boundary | Fixed media term. |
| `VPN` | 브이피엔 | current | exact | safe token boundary | Fixed network term. |
| `version` | 버전 | current | exact | safe token boundary | Fixed software/version term. |
| `WAN` | 더블유에이엔 | current | exact | safe token boundary | Fixed network term. |
| `WHO` | 더블유에이치오 | current | exact | safe token boundary | Fixed institution term. |
| `WIFI` | 와이파이 | current | exact | safe token boundary | Fixed network alias. |
| `WLAN` | 더블유랜 | current | exact | safe token boundary | Fixed network term. |
| `WTO` | 더블유티오 | current | exact | safe token boundary | Fixed institution/economy term. |
| `Wi-Fi` | 와이파이 | current | exact | safe token boundary | Fixed network term. |
| `WiFi` | 와이파이 | current | exact | safe token boundary | Fixed network alias. |
| `XLS` | 엑스엘에스 | current | exact | safe token boundary | Fixed file term. |
| `XLSX` | 엑스엘에스엑스 | current | exact | safe token boundary | Fixed file term. |
| `XML` | 엑스엠엘 | current | exact | safe token boundary | Fixed data format term. |
| `YAML` | 야믈 | current | exact | safe token boundary | Fixed data format term. |
| `YoY` | 와이오와이 | current | exact | safe token boundary | Fixed finance comparison term. |
| `gRPC` | 지알피씨 | current | exact | safe token boundary | Fixed technical term. |

### 6.1 Exact Slash Compound Entries

Slash compounds are not handled by a broad slash fallback. Only the exact
surfaces below are managed dictionary entries.

| Surface | Reading | Status | Match type | Boundary | Notes |
|---|---|---|---|---|---|
| `3G/4G/5G` | 쓰리지/포지/파이브지 | current | exact slash compound | safe token boundary | Preserve `/` in the rendered reading. |
| `UI/UX` | 유아이 유엑스 | current | exact slash compound | safe token boundary | Lexicalized compound; render with a space, not `/`. |
| `UX/UI` | 유엑스 유아이 | current | exact slash compound | safe token boundary | Lexicalized compound; render with a space, not `/`. |
| `B2B/B2C` | 비투비 비투씨 | current | exact slash compound | safe token boundary | Lexicalized compound; render with a space, not `/`. |

## 7. Current Conditional Entries

These entries are current only under the listed owner/gate condition. They must
full-claim the entire conditional surface and must preserve protected contexts.

| Surface family | Reading policy | Status | Match type | Boundary | Notes |
|---|---|---|---|---|---|
| `S&P` + numeric suffix | 에스앤피 + number reading | current_with_condition | whitelist finance index suffix | full claim | `S&P500`, `S&P 500`; no broad acronym+number fallback. |
| `NASDAQ` + numeric suffix | 나스닥 + number reading | current_with_condition | whitelist finance index suffix | full claim | `NASDAQ100`, `NASDAQ 100`. |
| `KOSPI` + numeric suffix | 코스피 + number reading | current_with_condition | whitelist finance index suffix | full claim | `KOSPI200`, `KOSPI 200`. |
| `KOSDAQ` + numeric suffix | 코스닥 + number reading | current_with_condition | whitelist finance index suffix | full claim | `KOSDAQ150`, `KOSDAQ 150`. |
| `112`, `119` emergency numbers | emergency digit reading | current_with_condition | emergency context gate | full claim | Context and allowed tail required; otherwise number/counter policy applies. |
| public numbers such as `110`, `120`, `1339` | public digit reading | current_with_condition | public-number context gate | full claim | Context required; gate failure falls back to general number. |
| `K-` + complete Hangul lexical prefix | 케이 + original Hangul | current_with_condition | K-Hangul lexical owner | full claim | `K-푸드`, `K-뷰티`; unsafe tails preserve. |
| managed acronym + `-` + complete Hangul lexical token | managed/acronym reading + raw hyphen + original Hangul | current_with_condition | managed acronym-Hangul hyphen lexical compound | full claim | Left side must be a current managed dictionary entry, e.g. `KTX-이음`; not a broad hyphen rewrite. Code-like/path/URL/protected contexts preserve. |
| current English managed dictionary entry + short numeric-code suffix | managed reading + numeric-code reading | current_with_condition | `managed_acronym_numeric_code` | full claim | Left side must be a current exact managed dictionary entry that starts and ends with ASCII alphabetic text and contains only ASCII letters/digits or `-`. This is registry-backed from the span managed dictionary inventory, not an owner-local base allowlist. Entries that should not inherit numeric-code suffixes must not remain current managed dictionary entries. Simple fallback-covered acronyms such as `AI`, `CPU`, and `USB` are not current managed dictionary entries, so `AI3`, `CPU900`, and `USB300` preserve because broad acronym+number fallback is forbidden. Supports no separator or ASCII `-`, e.g. `GPT4`, `GPT-4`, `KTX1`, `KBS-1`, `NASA1`, `GUI2`, `YAML-2`, `REST1`, `RAM2`, `ROM3`, `OAuth2`, `WAN1`, `WLAN2`, `Wi-Fi6`, `version-1.5`, `release-1.5`. The hyphen is a separator, not a minus sign, and is not read. Numeric block is a short unsigned code suffix only: integer suffixes must be 1-2 digits; decimal suffixes must have a 1-2 digit integer part and at least one fractional digit. No plus, signed number, leading-zero malformed decimal, bare dot, malformed comma, segmented malformed numeric, or unsafe tail. Long numeric suffixes such as `KTX-2024`, `GPT-2024`, and `version-2024` preserve. Unregistered ASCII word + numeric surfaces such as `abc-1.5`, `build-25`, and `foo2` preserve. URL/path/email/JSON/backtick/fenced code/shell-like/square bracket/file-like contexts preserve. |
| `ISO·IEC` | 아이에스오·아이이씨 | current_with_condition | lexical compound | safe token boundary | Fixed lexical compound; not broad middle-dot normalization. |

## 8. Pending / Conflict / Future Entries

These rows are not current implementation targets unless a later policy task
changes their status.

| Surface or family | Reading candidate | Status | Reason |
|---|---|---|---|
| `SNP500` | 에스엔피 오백 | historical_only_or_deprecated | Historical alias exists, but current finance suffix policy is based on `S&P`. |
| file-extension family not listed as current | policy table readings | future_candidate | Requires file/path context design before implementation. |
| event fixed phrases from historical dictionary | event readings | pending_policy_decision | Event owner/gate behavior is separate from managed dictionary inventory. |
| broad historical inline dictionary leftovers | historical readings | historical_only_or_deprecated | Historical dictionary snapshots are not the canonical span inventory. |
| `AI`, `CPU`, `USB` | uppercase acronym fallback readings | historical_only_or_deprecated | Removed from current managed dictionary because uppercase acronym fallback provides the same standalone and particle output, while broad acronym+number fallback remains forbidden (`AI3`, `CPU900`, `USB300` preserve). |

## 9. Implementation Contract

Implementation must keep these boundaries:

- `engine/span_engine/lexicon.py` or an equivalent span-owned registry must be
  the production source for current managed dictionary entries.
- Historical dictionary snapshots are not sufficient production
  coverage for `span_default`.
- Current managed dictionary entries must claim before uppercase acronym
  fallback.
- Conditional entries must be implemented by their explicit owner/gate, not by
  broad fallback.
- Protected spans must block managed dictionary reentry.
- New current entries require smoke, collision, and protected-context coverage.
- Pending, future, and historical-only rows must not be silently promoted to
  current by implementation.

## 10. Test Contract

For every `current` entry:

- assert the expected `normalized_text` through
  `engine.main.transform(...)`;
- assert dictionary-owner provenance where the entry is implemented by the
  dictionary owner;
- assert safe boundary behavior with adjacent Hangul particles and punctuation;
- assert unsafe mixed-token preserve for alnum, hyphen, slash, path, URL, JSON,
  backtick, fenced code, and square bracket contexts where relevant.

For every `current_with_condition` family:

- assert positive examples that pass the owner/gate;
- assert negative examples for missing context, unsafe tail, protected context,
  and partial-fallback prevention;
- assert the owner full-claims the whole surface.

For every `pending_policy_decision` row:

- do not add implementation tests that encode a new semantic expected until the
  policy decision is recorded;
- audit current output only if needed, and label it as audit/current-state
  coverage rather than canonical expected behavior.

## 11. Notes for Future Migration

Recommended migration order:

1. Keep current inventory parity guarded by narrow dictionary entries and
   protected-context tests.
2. Resolve file-extension or event entries not listed as current before
   implementation.
3. Define profile/context gates before enabling additional finance-context
   candidates or event fixed phrases.
4. Keep broad acronym fallback unchanged unless a separate policy explicitly
   changes it.
5. Treat historical-only dictionary rows as audit input, not as automatic migration
   requirements.

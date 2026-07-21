# Production Refactor P3: Number Fallback Gate Audit

## Scope and invariant

This audit covers the production path ending at
`engine.span_engine.claim_scanner._is_supported_number`. P3 does not change the
numeric policy, `CLAIM_ORDER_DOC`, scanner call order, parser dispatch, overlap
resolution, trace fields, source spans, protected ranges, fallback scope,
public API, binary CLI, or comparison facade. Golden 13 and policy Batch 1
through 8 are byte-exact contracts; P3 permits no output diff and introduces no
allowed-diff fixture.

## Production call graph

```text
engine.main.transform
  -> production_adapter.transform
    -> transform.transform_with_trace
      -> claim_scanner.claim_surfaces
        -> protected and typed owner scanners in CLAIM_ORDER_DOC order
        -> _claim_numbers                         # final generic owner
          -> _ASCII_INTEGER_RE.finditer
          -> excluded/protected range rejection
          -> _is_supported_number
          -> registry.can_claim
          -> SurfaceCandidate(owner="number",
                              surface_type=NUMBER_SURFACE,
                              reason="phase7_minimal_ascii_number")
      -> parser._parse_candidate
        -> number owner -> read_spaced_integer_text
      -> render/trace/validation
```

`_is_supported_number` is therefore not a general numeric parser. It is the
last reopening gate after all earlier owners and preserves have had their
chance to claim a surface. Returning `False` can either defer to an earlier
owner, protect an atomic unsupported surface, or prevent partial conversion.

## Claim order contract

The scanner implementation and the snapshot test agree on this exact order:

| Layer | Owners, in order |
| --- | --- |
| protected and lexical | bracket, protected_literal, dictionary, finance_index, k_hangul_lexical, lexical_compound, acronym_hangul_hyphen, single_letter_alnum_code, managed_acronym_numeric_code, two_block_hyphen_code, mixed_alnum_code_separator, acronym_fallback |
| numeric atomic | large_unit_atomic, currency, date, time, colon_semantic_pair, korean_da_score_pair, multi_colon_numeric, event, emergency |
| separator and range | spaced_separator_preserve, spaced_hyphen_numeric_blocks, numeric_delimited_hyphen_range, range |
| numeric typed | percent_point, duration, multiplier, unit_contamination_preserve, fraction, signed_temperature, signed_degree, signed_number, ph, compound_slash_unit, compound_exact_unit, special_unit, simple_unit, decimal_registered_suffix, numeric_suffix, decimal, middle_dot_numeric, public_number, counter_noun, phone, hyphen_digit_blocks, jamo, administrative_suffix |
| fallback | number |

Moving, registering, or consolidating owners is outside P3. The order remains
pinned by `test_claim_order_documentation_snapshot`.

## `claim_scanner.py` function manifest

The table uses AST line spans and a structural-node count (conditionals, loops,
try/match and boolean-expression nodes) as a comparison aid, not as a policy
quality metric.

| Function | LOC / structural nodes | Role and direct production caller | P3 disposition |
| --- | ---: | --- | --- |
| `claim_surfaces` | 72 / 4 | public scanner orchestrator; production transform | ordered policy program; do not refactor |
| `_claim_dictionary` | 34 / 8 | dictionary claims; `claim_surfaces` | policy-distinct |
| `_claim_acronym_fallback` | 34 / 5 | fallback acronym claims; `claim_surfaces` | policy-distinct |
| `_claim_numbers` | 25 / 4 | final ASCII integer scan; `claim_surfaces` | keep orchestration unchanged |
| `_claim_scanned_candidates` | 14 / 3 | shared claim attachment; `claim_surfaces` | out of P3 scope |
| `_claim_large_unit_candidates` | 18 / 4 | large-unit special boundary; `claim_surfaces` | policy-distinct |
| dictionary/acronym boundary helpers | 55 / mixed | only their owning claimers | unrelated to number gate |
| `_is_supported_number` | 104 / 53 | final-number eligibility; `_claim_numbers` | P3 target; high risk |
| compact `대` relation helpers | 56 / mixed | `_is_supported_number` | already semantic helpers; keep separate |
| mixed-Hangul/ordinal helpers | 30 / mixed | `_is_supported_number` | policy-distinct |
| `_is_url_or_path_context` | 20 / 8 | `_is_supported_number` | protected-context helper; keep |
| primitive character helpers | 9 / mixed | number-boundary helpers | keep |

All module-level functions are internal except `claim_surfaces` and the
documented order constant. P3-C must re-run reachability after any extraction.

## Number fallback branch matrix

| Gate, in execution order | Example boundary | Result | Owner/policy reason |
| --- | --- | --- | --- |
| integer normalization | `01`, invalid comma grouping | reject | leading-zero and malformed integer surfaces preserve; typed owners may have already full-claimed |
| left `.`/`·` relation | dotted or signed left operand | reject | decimal, event and middle-dot atomicity; do not convert an interior block |
| URL/path context | URL/path numeric component | reject | protected source surface |
| compact Korean magnitude tail | Arabic block followed by compact `천/백/십` | reject | prevent a partial mixed-numeric rewrite |
| invalid spaced ordinal prefix | unsupported `제  N` boundary | reject | ordinal surface remains atomic unless numeric-suffix owner accepted it |
| compact `N대N` | first/second operand | conditional allow | only complete safe Korean score/relation context may expose the number blocks |
| Hangul-embedded recognized context | complete Hangul prefix plus valid numeric block | allow | documented embedded-number fallback |
| preceding jamo/ASCII/Hangul/blocking delimiter/currency symbol | identifier or unsupported currency adjacency | reject | no interior numeric partial conversion |
| preceding range delimiter | second range block after failed full claim | reject | range surface atomicity |
| end of input | ordinary valid integer | allow | minimal number owner |
| following jamo | numeric+jamo token | reject | code/phonetic boundary |
| whitespace plus range delimiter | `1 ~ 2` | reject | earlier range owner owns the full surface |
| whitespace plus registered unit | `3 kg` | reject | earlier simple/special unit owner owns the full surface |
| whitespace plus registered compound exact unit | `3 km/h` | reject | earlier compound owner owns the full surface |
| unsafe administrative tail | numeric administrative-like token | reject | administrative owner/protection |
| attached registered unit prefix followed by slash | `3m/s`, `3cm/s`; unsupported `3kg/s` | reject | compound-unit ownership or atomic unsupported unit-like surface; number must not split the prefix |
| following ASCII alphanumeric | `123abc`, `A112` | reject | identifier/code surface atomicity |
| terminal comma | `123,` or comma before whitespace | conditional allow | punctuation is external only at a safe terminal boundary |
| following blocking punctuation | colon, hyphen, tilde and other blockers | reject | date/time/range/score/phone atomicity |
| following decimal/middle dot | `12.3`, `12·3`, spaced middle dot | conditional reject/allow | earlier decimal/event/middle-dot contracts; only the documented safe spaced-right operand can expose the left number |
| following Hangul | `112명`, `112 신고`, ordinary 조사/tail | conditional allow/reject | emergency/public exceptions, counter/suffix blocking, or ordinary number+josa fallback |
| no later blocker | ordinary number boundary | allow | minimal number owner |

### Full-claim and partial-fallback consequences

- A successful earlier candidate occupies the source span through the registry;
  `_claim_numbers` cannot overlap it.
- An absolute-preserve/protected range is excluded before this predicate runs.
- A failed earlier parser does not automatically license an interior number:
  the adjacency, delimiter, unit-like, identifier and Korean-tail gates decide
  whether partial fallback is safe.
- A rejected candidate may intentionally expose an independent ordinary number,
  for example a safe number followed by ordinary Korean text or punctuation.
- No-Hangul bypass and segment-local transform fallback live above the scanner;
  extracting a predicate here must not change either mechanism.

## Exact-equivalent extraction candidates

### Candidate P3-A: spaced earlier-owner deferral

Three consecutive branches share the same prerequisite
`next_char.isspace()` and differ only in a side-effect-free predicate over the
already-computed `next_non_space`:

1. range/tilde delimiter,
2. supported simple unit,
3. supported compound exact unit.

A private pure helper can return the disjunction in the same order. Inputs,
short-circuit behavior, return value and failure result are identical. It adds
no scan beyond the three scans already performed. It must remain named and
documented as deferral to an earlier owner, not as generic whitespace safety.

### Candidate P3-B: attached unit-prefix slash blocker

The unit-prefix length lookup, suffix slice, `lstrip`, and slash test form one
side-effect-free boolean decision. A private pure helper taking `raw_text` and
the number end offset can preserve the exact `None` and slash semantics. This
is not a general compound-unit parser: it only prevents the final number owner
from splitting a surface the earlier unit graph owns or intentionally
preserves.

Both candidates remain in `claim_scanner.py`. A new support module would add an
import boundary without reducing policy coupling.

## Similar but policy-distinct; keep separate

- Previous and next ASCII-alphanumeric checks look symmetric but protect
  different scanner progress and partial-fallback directions.
- Dot and middle-dot checks share punctuation but have different event,
  decimal, sign, attached/spaced and operand-completeness rules.
- Range-delimiter checks before and after the number are not symmetric: one
  protects a later block after failed ownership while the other defers the
  current first block to an earlier owner.
- Hangul prefix and Hangul suffix gates encode different embedded-number,
  public/emergency, counter/unit and particle policies.
- URL/path, bracket/protected exclusion and identifier adjacency must not be
  generalized into one “unsafe text” helper; their source-span and failure
  semantics differ.
- Leading-zero normalization, signed owners, comma validation and decimals are
  separate parsing domains. They must not be folded into a generic numeric
  validity predicate.
- Compact `N대N` first/second helpers intentionally have directional logic and
  remain separate.

## Unsafe functions and branches

`claim_surfaces` is an executable precedence specification. `_claim_numbers`
is short but its excluded-range and registry checks fix overlap semantics.
`_is_supported_number` as a whole is unsafe to split by category because its
ordered early returns distinguish deferral, preserve and allowed fallback.
Only the two local, contiguous, pure boolean regions above qualify for P3.

## Characterization plan

Before each extraction, public transform and trace tests must pin:

- earlier owner independence: spaced range, unit and compound unit;
- ordinary spaced-text number fallback;
- attached compound-unit and unsupported unit-like slash atomicity;
- leading-zero preserve and date/time/counter/currency overrides;
- phone, emergency, public number, signed number and code ownership;
- URL/path/JSON/backtick/bracket and absolute-preserve boundaries;
- exact owner, `surface_type`, reason and `SourceSpan` for generated claims;
- rejected earlier-owner candidates that intentionally do or do not expose a
  number fallback.

Existing tests with the same input remain when they assert different output,
precedence, trace, provenance, fallback or import-boundary contracts.

## Checkpoint A evidence

- Number/leading-zero/precedence/protected/fallback target: 444 passed.
- Batch 1 through 8, Golden, empty audit, production isolation, and comparison
  support: 117 passed.
- Full source suite: 6,198 passed and 109 binary tests deselected.
- Fixed 83-case paired-before samples with 20 corpus rounds per sample:
  1308.78, 1369.25, 1310.39, 1317.81 and 1342.69 microseconds per input;
  median/min/max 1317.81/1308.78/1369.25.
- Production code changes and output differences at this point: zero.

The same-session paired result takes precedence over historical WSL values.
Both proposed helpers remove no protections and are expected to be performance
neutral; a repeated median regression of at least five percent rejects the
extraction.

## Checkpoints B and C result

- Fourteen public characterization cases were added before production changes.
  They pin exact normalized text, owner, `surface_type`, reason and source span
  for spaced range/unit deferral, ordinary number fallback, attached slash
  units, unsupported unit-like atomic preserve, identifier adjacency,
  leading-zero preserve, URL protection and square-bracket protection.
- P3-A replaced three consecutive whitespace-plus-owner checks with private
  pure `_has_spaced_owned_number_tail`. The delimiter, simple-unit and compound
  exact-unit predicates remain in their original order and short-circuit in
  that order.
- P3-B replaced the local supported-unit-prefix length/slice/slash block with
  private pure `_has_supported_unit_slash_tail`. It uses the same substring,
  `None`, `lstrip`, and leading-slash conditions and does not parse or register
  units.
- `_is_supported_number` changed from 104 LOC / 53 structural nodes to 97 LOC /
  47 structural nodes by this audit's AST metric. The module is 786 LOC with 26
  functions; the extra private names make the policy decisions explicit rather
  than creating a generic registry or support module.
- Final AST and repository audits found zero private top-level zero-load
  functions, zero real unused imports and zero exact duplicate function bodies.
  The reported `annotations` import is the semantic `__future__` directive, not
  an unused runtime import. Each new helper has exactly one production caller.
- Historical tests with overlapping inputs were retained because they assert
  different output snapshots, precedence, trace/span, protected-boundary,
  fallback, comparison, or import-isolation contracts. No test satisfied the
  full exact-duplicate deletion rule.
- No private symbol, test, import, or file was deleted in P3-C because no safe
  zero-reach or exact-duplicate leaf was proven.

P3-A target validation was 426 passed; P3-B target validation was 516 passed.
The canonical Batch/Golden/audit/isolation set was 117 passed after each
extraction.

## Final validation

- Full source suite: 6,212 passed and 109 binary tests deselected.
- Explicit PyInstaller rebuild and local binary smoke: passed.
- Rebuilt-binary selected set: 109 passed and 6,212 source tests deselected,
  including canonical binary output and archive production-module isolation.
- Golden 13 plus Batch 1 through 8 (70): all 83 source, rebuilt-binary, API and
  expected strings were directly compared and byte-exact.
- Fixed 83-case paired-after samples were 1234.02, 1249.66, 1392.83, 1630.86
  and 1339.89 microseconds per input; median/min/max
  1339.89/1234.02/1630.86. The median is about 1.7 percent above the same-session
  paired-before 1317.81 and below the five-percent stop threshold. The maximum
  is a WSL/CPU scheduling outlier; the helpers add no input-length scan.
- Production output differences: zero. Batch fixture states, Golden expected
  values, legacy audit `[]`, public entrypoints and comparison isolation are
  unchanged. No allowed-diff fixture was added or modified.


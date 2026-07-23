# Production Refactor P2 range audit

Status: Checkpoints A, B, and C complete (2026-07-15)

## Scope and method

This audit covers only the production range graph rooted at
engine.main.transform. It combines AST LOC/structural counts, direct call edges,
package exports, owner/trace tests, protected-span boundaries, and the canonical
Batch 1 through 8 and Golden contracts. Similar syntax is not equivalence unless
input domain, half-open source span, full-consume rule, failure/preserve result,
owner precedence, and rendered provenance are all identical.

## Production call path and precedence

    engine.main.transform
      -> production_adapter.transform_for_production
         -> span_engine.transform.transform_with_trace
            -> claim_scanner.claim_surfaces
               -> protected, lexical, date/time, colon owners
               -> spaced-separator and spaced-hyphen preserve owners
               -> scan_numeric_delimited_hyphen_range_candidates
               -> scan_range_candidates
               -> unit/counter/number fallback owners
            -> parser._parse_candidate -> parse_range_candidate
            -> render_tokens_with_surfaces
            -> validation and trace assembly

Scanner order is observable policy. P2 must not reorder these calls or replace
them with a generic registry.

## Owner and boundary matrix

| Surface family | Accepted surface | Full-consume and precedence boundary | Candidate result | Failure/preserve behavior | Owning coverage |
| --- | --- | --- | --- | --- | --- |
| basic tilde range | unsigned integer/decimal with ~, ∼, ～, 〜 | rejects leading zero, ASCII/Hangul left adjacency, repeats and unsafe decimal tail | range / RANGE_SURFACE / range_full_consume_gate | unsafe ASCII tail becomes atomic RANGE_PRESERVE_SURFACE | phase12 basic/preserve/safe-particle; Batch 8 aliases |
| range with unit | registered unit after right operand | unit and owner-local tail must full-consume | range_with_unit / RANGE_WITH_UNIT_SURFACE | invalid unit tail preserves through the range-like token end | phase12 unit/provenance/precedence; decimal/signed blocks |
| shared Korean suffix | date/time, duration, page/document or counter suffix | suffix stays an original source span; reading/spacing is suffix-specific | range / RANGE_SURFACE / range_shared_korean_suffix_gate | unsupported duration continuation or unsafe tail defers | phase12 shared suffix/provenance; clock-duration; Batch 8 |
| restricted hyphen/en-dash | parsed pair plus registered unit or Korean suffix | standalone two-block hyphen preserves; sign disallowed outside tilde; leading zero fails atomically | range or range_with_unit; numeric_delimited_hyphen_range reasons | signed disallowed registered surfaces become preserve claims | numeric-delimited two-block/decimal/signed; Batch 8 |
| broad numeric tilde | signed/comma/decimal operands, optional inline whitespace, tilde aliases | only tilde-like delimiters; registered suffix owners are deferred | range / RANGE_SURFACE / tilde_numeric_range_broad_gate | malformed tilde surface preserves atomically at safe external boundary | tail-spacing, signed and malformed regressions |
| colon semantic pair | colon/fullwidth colon with semantic or safe broad context | strong time remains time; media/code/scripture context preserves | colon_semantic_pair / COLON_SEMANTIC_PAIR_SURFACE | blocked, invalid or render-failed pair preserves completely | colon/time Batch 3 and numeric-delimited tests |
| multi-colon numeric | 3 to 8 blocks | external boundary; timecode and code/scripture context preserve | multi_colon_numeric / MULTI_COLON_NUMERIC_SURFACE | invalid/too-many/timecode surfaces preserve atomically | multi-colon/timecode and Batch 3 |
| protected/code-like | URL, path, JSON, backtick, bracket, lexical hyphen | earlier protected/excluded claims reject overlapping range candidates | original protected surface | no internal range partial conversion | bracket, JSON, typed lexical and precedence tests |

Successful readings live in candidate metadata. Parser dispatch only retrieves
that string. Generated readings use the candidate core span; declared suffix
spans remain original Korean. Helper extraction must not change core_span,
full_span, suffix_spans, metadata, owner, surface type, or reason.

## Function-by-function manifest

Structural values are LOC/branch-loop-boolean nodes. Caller and callee columns
list functions inside range.py only.

| Function | LOC/structural | Direct caller(s) | Direct local callee(s) | API | Owner/contract family |
| --- | ---: | --- | --- | --- | --- |
| is_range_separator | 4/1 | scan_range_candidates | none | public/exported | range-local utility |
| scan_range_candidates | 54/11 | entry/export only | _basic_candidate, _consume_numeric_like, _has_unsafe_ascii_tail, _is_ascii_digit, _korean_suffix_candidate, _preserve_candidate, _range_like_token_end, _unit_candidate, _valid_numbers, is_range_separator | public/exported | range scanners; range/range_with_unit |
| scan_numeric_delimited_hyphen_range_candidates | 135/28 | entry/export only | _basic_tilde_numeric_delimited_candidate, _can_start_numeric_delimited_number, _consume_numeric_delimited_number_like, _consume_optional_inline_whitespace, _hyphen_korean_suffix_candidate, _hyphen_unit_candidate, _is_numeric_delimited_range_delimiter, _is_signed_numeric_delimited_pair, _preserve_candidate, _range_like_token_end, _scan_invalid_tilde_numeric_range_preserve_candidates, _signed_range_preserve_candidate, _valid_hyphen_range_numbers, parse_numeric_delimited_number | public/exported | range scanners; range/range_with_unit |
| scan_colon_semantic_pair_candidates | 104/20 | entry/export only | _can_start_numeric_delimited_number, _colon_semantic_pair_reading, _consume_numeric_delimited_number_like, _has_colon_pair_blocked_context, _has_colon_semantic_pair_context, _has_explicit_invalid_time_context, _is_raw_strong_time_like_colon_pair, _is_raw_time_like_colon_pair, _is_time_like_colon_pair, _preserve_candidate, _valid_colon_semantic_pair_left_boundary, _valid_colon_semantic_pair_right_boundary, parse_numeric_delimited_number | public/exported | colon semantic/multi-colon scanner |
| scan_multi_colon_numeric_candidates | 69/15 | entry/export only | _can_start_colon_numeric_like_fragment, _has_multi_colon_blocked_context, _is_timecode_like_three_block, _preserve_candidate, _scan_multi_colon_numeric_like_surface, _valid_multi_colon_boundary, parse_numeric_delimited_number, render_numeric_delimited_number | public/exported | colon semantic/multi-colon scanner |
| parse_range_candidate | 10/2 | parse_range_with_korean_suffix_candidate, parse_range_with_unit_candidate | none | public/exported | parser bridge; metadata reading only |
| parse_range_with_unit_candidate | 6/1 | entry/export only | parse_range_candidate | public/exported | parser bridge; metadata reading only |
| parse_range_with_korean_suffix_candidate | 6/1 | entry/export only | parse_range_candidate | public/exported | parser bridge; metadata reading only |
| hyphen_range_compatible_korean_suffix_reading | 4/1 | _hyphen_korean_suffix_candidate | none | public/exported | generated reading and metadata provenance |
| hyphen_range_compatible_korean_suffixes_by_length | 2/0 | _hyphen_korean_suffix_candidate, _signed_range_preserve_candidate | none | public/exported | range-local utility |
| _unit_candidate | 29/3 | scan_range_candidates | _preserve_candidate, _range_like_token_end, _range_reading, _valid_after_surface | private | candidate construction or atomic preserve |
| _hyphen_unit_candidate | 41/4 | scan_numeric_delimited_hyphen_range_candidates | _preserve_candidate, _range_like_token_end, _range_reading, _valid_after_surface | private | candidate construction or atomic preserve |
| _hyphen_korean_suffix_candidate | 45/10 | scan_numeric_delimited_hyphen_range_candidates | _range_reading, _valid_after_korean_suffix, hyphen_range_compatible_korean_suffix_reading, hyphen_range_compatible_korean_suffixes_by_length | private | candidate construction or atomic preserve |
| _basic_tilde_numeric_delimited_candidate | 30/4 | scan_numeric_delimited_hyphen_range_candidates | _needs_hangul_tail_space, _range_reading, _valid_after_basic_tilde_range | private | candidate construction or atomic preserve |
| _korean_suffix_candidate | 41/8 | scan_range_candidates | _is_unsupported_duration_range_suffix_tail, _range_duration_suffix_reading, _range_reading, _range_shared_suffix_reading, _valid_after_korean_suffix | private | candidate construction or atomic preserve |
| _basic_candidate | 14/1 | scan_range_candidates | _range_reading, _valid_after_basic_range | private | candidate construction or atomic preserve |
| _range_reading | 14/1 | _basic_candidate, _basic_tilde_numeric_delimited_candidate, _hyphen_korean_suffix_candidate, _hyphen_unit_candidate, _korean_suffix_candidate, _unit_candidate | _numeric_delimited_or_numeric_like_reading | private | generated reading and metadata provenance |
| _numeric_delimited_or_numeric_like_reading | 10/2 | _range_reading | _numeric_like_reading, _range_numeric_delimited_number_reading, render_numeric_delimited_number | private | generated reading and metadata provenance |
| _range_numeric_delimited_number_reading | 11/4 | _numeric_delimited_or_numeric_like_reading | _apply_numeric_sign, render_numeric_delimited_number | private | generated reading and metadata provenance |
| _range_shared_suffix_reading | 5/0 | _korean_suffix_candidate | _numeric_like_reading_with_suffix, _numeric_like_suffix_prefix_reading | private | generated reading and metadata provenance |
| _range_duration_suffix_reading | 4/0 | _korean_suffix_candidate | _duration_hour_prefix_reading | private | generated reading and metadata provenance |
| _numeric_like_reading_with_suffix | 2/0 | _range_shared_suffix_reading | _numeric_like_shared_suffix_part | private | generated reading and metadata provenance |
| _numeric_like_suffix_prefix_reading | 2/0 | _range_shared_suffix_reading | _numeric_like_shared_suffix_part | private | generated reading and metadata provenance |
| _numeric_like_shared_suffix_part | 14/7 | _numeric_like_reading_with_suffix, _numeric_like_suffix_prefix_reading | _month_reading, _numeric_like_reading | private | range-local utility |
| _month_reading | 6/2 | _numeric_like_shared_suffix_part | none | private | generated reading and metadata provenance |
| _duration_hour_prefix_reading | 7/3 | _range_duration_suffix_reading | _numeric_like_reading | private | generated reading and metadata provenance |
| _consume_numeric_like | 14/6 | scan_range_candidates | _is_ascii_digit | private | source consumer; half-open source span |
| _consume_numeric_delimited_number_like | 28/10 | scan_colon_semantic_pair_candidates, scan_numeric_delimited_hyphen_range_candidates | _is_ascii_digit | private | source consumer; half-open source span |
| _can_start_numeric_delimited_number | 2/1 | scan_colon_semantic_pair_candidates, scan_numeric_delimited_hyphen_range_candidates | _is_ascii_digit | private | owner-local policy predicate |
| _can_start_colon_numeric_like_fragment | 2/1 | scan_multi_colon_numeric_candidates | _is_ascii_digit | private | colon semantic/timecode boundary |
| _scan_multi_colon_numeric_like_surface | 16/5 | scan_multi_colon_numeric_candidates | _consume_colon_numeric_like_fragment | private | source consumer; half-open source span |
| _consume_colon_numeric_like_fragment | 24/11 | _scan_multi_colon_numeric_like_surface | _is_ascii_digit | private | source consumer; half-open source span |
| _is_numeric_delimited_range_delimiter | 2/1 | scan_numeric_delimited_hyphen_range_candidates | none | private | owner-local policy predicate |
| _consume_optional_inline_whitespace | 5/2 | _scan_invalid_tilde_numeric_range_preserve_candidates, scan_numeric_delimited_hyphen_range_candidates | none | private | source consumer; half-open source span |
| _scan_invalid_tilde_numeric_range_preserve_candidates | 62/20 | scan_numeric_delimited_hyphen_range_candidates | _consume_optional_inline_whitespace, _is_ascii_digit, _is_inside_numeric_like_fragment, _preserve_candidate, _trim_valid_sentence_punctuation_from_invalid_tilde_raw, _valid_invalid_tilde_preserve_boundary, parse_numeric_delimited_number | private | candidate construction or atomic preserve |
| _is_inside_numeric_like_fragment | 5/2 | _scan_invalid_tilde_numeric_range_preserve_candidates | _is_ascii_digit | private | owner-local policy predicate |
| _trim_valid_sentence_punctuation_from_invalid_tilde_raw | 20/7 | _scan_invalid_tilde_numeric_range_preserve_candidates | parse_numeric_delimited_number | private | tilde alias/preserve/tail boundary |
| _valid_invalid_tilde_preserve_boundary | 17/12 | _scan_invalid_tilde_numeric_range_preserve_candidates | none | private | tilde alias/preserve/tail boundary |
| _valid_numbers | 20/13 | scan_range_candidates | _valid_numeric_like | private | owner-local policy predicate |
| _valid_hyphen_range_numbers | 24/11 | scan_numeric_delimited_hyphen_range_candidates | _is_signed_numeric_delimited_pair | private | owner-local policy predicate |
| _is_signed_numeric_delimited_pair | 6/3 | _valid_hyphen_range_numbers, scan_numeric_delimited_hyphen_range_candidates | none | private | owner-local policy predicate |
| _signed_range_preserve_candidate | 19/4 | scan_numeric_delimited_hyphen_range_candidates | _preserve_candidate, hyphen_range_compatible_korean_suffixes_by_length | private | candidate construction or atomic preserve |
| _valid_colon_semantic_pair_left_boundary | 11/5 | scan_colon_semantic_pair_candidates | none | private | colon semantic/timecode boundary |
| _valid_colon_semantic_pair_right_boundary | 14/8 | scan_colon_semantic_pair_candidates | none | private | colon semantic/timecode boundary |
| _valid_multi_colon_boundary | 19/11 | scan_multi_colon_numeric_candidates | none | private | colon semantic/timecode boundary |
| _has_multi_colon_blocked_context | 31/4 | scan_multi_colon_numeric_candidates | _text_endswith_ascii_word | private | colon semantic/timecode boundary |
| _text_endswith_ascii_word | 6/4 | _has_colon_pair_blocked_context, _has_multi_colon_blocked_context | none | private | owner-local policy predicate |
| _is_timecode_like_three_block | 16/9 | scan_multi_colon_numeric_candidates | _is_ascii_digits, _is_two_digit_00_to_59 | private | colon semantic/timecode boundary |
| _is_two_digit_00_to_59 | 2/1 | _is_timecode_like_three_block | none | private | colon semantic/timecode boundary |
| parse_numeric_delimited_number | 45/15 | _scan_invalid_tilde_numeric_range_preserve_candidates, _trim_valid_sentence_punctuation_from_invalid_tilde_raw, scan_colon_semantic_pair_candidates, scan_multi_colon_numeric_candidates, scan_numeric_delimited_hyphen_range_candidates | _is_ascii_digits | public/exported | numeric-delimited value grammar/render |
| render_numeric_delimited_number | 11/3 | _colon_semantic_pair_reading, _numeric_delimited_or_numeric_like_reading, _range_numeric_delimited_number_reading, scan_multi_colon_numeric_candidates | _apply_numeric_sign, _numeric_delimited_fractional_reading | public/exported | numeric-delimited value grammar/render |
| _apply_numeric_sign | 6/2 | _range_numeric_delimited_number_reading, render_numeric_delimited_number | none | private | numeric-delimited value grammar/render |
| _numeric_delimited_fractional_reading | 2/0 | render_numeric_delimited_number | none | private | numeric-delimited value grammar/render |
| _is_time_like_colon_pair | 12/8 | scan_colon_semantic_pair_candidates | none | private | colon semantic/timecode boundary |
| _is_raw_time_like_colon_pair | 11/8 | scan_colon_semantic_pair_candidates | none | private | colon semantic/timecode boundary |
| _is_raw_strong_time_like_colon_pair | 3/1 | scan_colon_semantic_pair_candidates | none | private | colon semantic/timecode boundary |
| _has_explicit_invalid_time_context | 10/5 | scan_colon_semantic_pair_candidates | none | private | owner-local policy predicate |
| _has_colon_pair_blocked_context | 11/6 | scan_colon_semantic_pair_candidates | _text_endswith_ascii_word | private | colon semantic/timecode boundary |
| _has_colon_semantic_pair_context | 13/4 | scan_colon_semantic_pair_candidates | _text_endswith_semantic_pair_keyword, _text_startswith_semantic_pair_keyword | private | colon semantic/timecode boundary |
| _text_endswith_semantic_pair_keyword | 8/3 | _has_colon_semantic_pair_context | _valid_semantic_pair_keyword_left_boundary | private | colon semantic/timecode boundary |
| _text_startswith_semantic_pair_keyword | 7/3 | _has_colon_semantic_pair_context | _valid_semantic_pair_keyword_right_boundary | private | colon semantic/timecode boundary |
| _valid_semantic_pair_keyword_left_boundary | 6/3 | _text_endswith_semantic_pair_keyword | none | private | colon semantic/timecode boundary |
| _valid_semantic_pair_keyword_right_boundary | 8/4 | _text_startswith_semantic_pair_keyword | none | private | colon semantic/timecode boundary |
| _colon_semantic_pair_reading | 13/1 | scan_colon_semantic_pair_candidates | _needs_hangul_tail_space, render_numeric_delimited_number | private | colon semantic/timecode boundary |
| _needs_hangul_tail_space | 7/3 | _basic_tilde_numeric_delimited_candidate, _colon_semantic_pair_reading | _has_attached_tail | private | shared pure tail-spacing mechanism; owner tuple remains caller-local |
| _has_attached_tail | 13/4 | _needs_hangul_tail_space | none | private | shared pure tail-spacing mechanism; owner tuple remains caller-local |
| _has_leading_zero | 2/1 | _valid_numeric_like | none | private | owner-local policy predicate |
| _valid_numeric_like | 11/6 | _valid_numbers | _has_leading_zero, _is_ascii_digits | private | owner-local policy predicate |
| _numeric_like_reading | 6/1 | _duration_hour_prefix_reading, _numeric_delimited_or_numeric_like_reading, _numeric_like_shared_suffix_part | none | private | generated reading and metadata provenance |
| _valid_after_surface | 16/9 | _hyphen_unit_candidate, _unit_candidate | _is_ascii_digit | private | owner-local tail/full-consume boundary |
| _has_unsafe_ascii_tail | 2/1 | scan_range_candidates | none | private | owner-local tail/full-consume boundary |
| _range_like_token_end | 12/4 | _hyphen_unit_candidate, _unit_candidate, scan_numeric_delimited_hyphen_range_candidates, scan_range_candidates | none | private | owner-local tail/full-consume boundary |
| _preserve_candidate | 8/0 | _hyphen_unit_candidate, _scan_invalid_tilde_numeric_range_preserve_candidates, _signed_range_preserve_candidate, _unit_candidate, scan_colon_semantic_pair_candidates, scan_multi_colon_numeric_candidates, scan_numeric_delimited_hyphen_range_candidates, scan_range_candidates | none | private | candidate construction or atomic preserve |
| _valid_after_basic_range | 19/12 | _basic_candidate | _is_ascii_digit | private | owner-local tail/full-consume boundary |
| _valid_after_basic_tilde_range | 15/9 | _basic_tilde_numeric_delimited_candidate | _is_ascii_digit | private | tilde alias/preserve/tail boundary |
| _valid_after_korean_suffix | 11/5 | _hyphen_korean_suffix_candidate, _korean_suffix_candidate | none | private | owner-local tail/full-consume boundary |
| _is_unsupported_duration_range_suffix_tail | 5/2 | _korean_suffix_candidate | none | private | owner-local policy predicate |
| _is_ascii_digit | 2/1 | _can_start_colon_numeric_like_fragment, _can_start_numeric_delimited_number, _consume_colon_numeric_like_fragment, _consume_numeric_delimited_number_like, _consume_numeric_like, _is_ascii_digits, _is_inside_numeric_like_fragment, _scan_invalid_tilde_numeric_range_preserve_candidates, _valid_after_basic_range, _valid_after_basic_tilde_range, _valid_after_surface, scan_range_candidates | none | private | owner-local policy predicate |
| _is_ascii_digits | 2/2 | _is_timecode_like_three_block, _valid_numeric_like, parse_numeric_delimited_number | _is_ascii_digit | private | owner-local policy predicate |

## Implemented exact-equivalent extractions

### P2-A: numeric sign prefix application — implemented

render_numeric_delimited_number and _range_numeric_delimited_number_reading
contain the same mutually exclusive mapping from number.sign and an already
rendered integer string: minus prefixes 마이너스, plus prefixes 플러스, and
None leaves the reading unchanged. Integer, zero-style and fractional policies
remain in their callers. A pure _apply_numeric_sign helper can replace only
these identical branches.

### P2-B: Hangul tail spacing with an owner-supplied tail set — implemented

_has_attached_basic_tilde_tail and _has_attached_colon_pair_tail have
AST-identical bodies except for the tuple they iterate. The two _needs_* helpers
also have identical Hangul/end checks. Pure _has_attached_tail and
_needs_hangul_tail_space helpers may replace the four definitions while the two
policy tuples remain separate and explicit at current call sites.

No scanner state machine is approved for extraction in P2.

## Similar but policy-distinct; keep separate

- _unit_candidate and _hyphen_unit_candidate use different registries, reasons,
  delimiter styles, whitespace and zero rendering.
- _basic_candidate and _basic_tilde_numeric_delimited_candidate differ in
  suffix deferral, arbitrary-Hangul spacing and valid-tail rules.
- The four _valid_after_* predicates deliberately accept different tails.
- The three numeric consumers accept different sign, comma, decimal and
  colon-adjacent forms.
- Numeric, hyphen, colon and multi-colon boundaries run at different precedence
  layers.
- The two public parse_range_with_* owner guards are API contracts, not duplicate
  implementation noise.
- Month, clock-hour, duration-hour and ordinary range readings encode different
  Korean spacing and numeral policies.

## Large/complex functions unsafe for P2

scan_numeric_delimited_hyphen_range_candidates combines malformed tilde
preservation, sign/delimiter validation, unit and suffix precedence, and broad
tilde fallback. scan_range_candidates and both colon scanners likewise combine
observable atomic-preserve rules. They remain cohesive in P2.

## Characterization and performance plan

Before P2-A, tests must pin signed/unsigned parse/render plus signed tilde-unit
and colon-pair owner/reason/span behavior. Before P2-B, a public-output and trace
matrix must distinguish the basic-tilde and colon attached-tail sets, including
particles, arbitrary Korean tails, string end, whitespace, punctuation and
ASCII tails. Existing URL/path/JSON/backtick/bracket tests retain the full-claim
boundary.

Both candidates replace repeated pure branches inside one module and add no
input-length scan. Paired before/after measurements on the fixed 83-case corpus
take precedence over the noisy historical WSL median.

## Checkpoint A validation

- Range/hyphen/tilde/numeric-delimited/precedence target: 580 passed and 4,774 deselected.
- Batch 1 through 8, Golden, empty audit, production isolation, and comparison support: 117 passed.
- Full source suite: 6,177 passed and 109 binary tests deselected.
- Pre-change fixed 83-case samples with 20 corpus rounds per sample: 1251.50, 1248.87, 1291.99, 1343.52, and 1296.05 microseconds per input; median/min/max 1291.99/1248.87/1343.52.
- Production code changes and output differences at this checkpoint: zero.

## Checkpoints B and C result

- Added 21 public-output, owner/reason/span, provenance, sign, and tail-spacing characterization cases before changing production code.
- P2-A replaced the two identical sign-prefix branches with private pure `_apply_numeric_sign`; integer, comma, zero-style, and fractional rendering stayed in their original callers.
- P2-B replaced four duplicated owner-specific functions with `_needs_hangul_tail_space` and `_has_attached_tail`. `_BROAD_RANGE_ATTACHED_TAILS` and `_COLON_PAIR_ATTACHED_TAILS` remain separate and explicit at the two call sites.
- Removed two statically unused imports (`TILDE_LIKE_DELIMITERS` and `normalize_integer_text`) after AST load and repository reference checks.
- `range.py` changed from 1,710 LOC before P2 to 1,694 LOC, with 79 functions. Final AST audit reports zero private top-level zero-load symbols, zero unused imports, and zero exact duplicate function bodies.
- Historical tests sharing inputs such as `3~8cm`, `1~11월`, and `12-15장` were retained: they separately cover output snapshots, owner precedence, source provenance, protected surfaces, comparison reports, or phase-boundary regression. No test met the full exact-duplicate removal rule.

Checkpoint B/C target results were 82 tests for P2-A, 110 tests for P2-B, and 33 tests after unused-import removal. Final range target was 601 passed and 4,774 deselected; canonical Batch/Golden/audit/isolation contracts were 117 passed.

Paired post-change 83-case samples were 1268.45, 1204.53, 1217.84, 1205.73, and 1217.34 microseconds per input. Median/min/max were 1217.34/1204.53/1268.45, versus the same-session pre-change 1291.99/1248.87/1343.52. The median improved by about 5.8 percent; WSL and CPU scheduling remain uncontrolled.

## Final validation

- Full source suite: 6,198 passed and 109 binary tests deselected.
- Explicit PyInstaller rebuild and smoke: passed.
- Rebuilt-binary selected set: 109 passed and 6,198 source tests deselected, including archive production-module isolation.
- Golden 13 plus Batch 1 through 8 (70): all 83 source, rebuilt-binary-via-API, and expected strings were byte-exact.
- Legacy audit remains the exact JSON empty array. Batch fixture counts and applied statuses are unchanged.
- Production output differences and new allowed diffs: zero.
- Final range private zero-load symbol audit: zero. `tests/_policy_case.py` masking: absent. `git diff --check`: passed. `.orig`/`.rej`: absent.

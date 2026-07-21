# Production Refactor P4: Parser Owner Dispatch Audit

## Scope and invariant

This audit covers the production parser graph rooted at
`engine.span_engine.parser.parse_candidates`. P4 permits no change to
`CLAIM_ORDER_DOC`, claim-scanner call order, registry overlap, owner metadata,
source spans, parse failure, preserve behavior, render provenance, transform
fallback, public API, binary CLI, comparison facade, Golden output, or Batch 1
through 8. No allowed output diff is introduced.

## Production call graph

```text
engine.main.transform
  -> production_adapter.transform_for_production
    -> transform.transform_with_trace
      -> _transform_core_with_trace
        -> claim_scanner.claim_surfaces
        -> parser.parse_candidates
          -> _parse_candidate in candidate start order
          -> owner-local parser or custom Surface builder
          -> omit candidate when parsing returns None
        -> render.render_tokens_with_surfaces
          -> custom render_pieces, or one GENERATED_READING piece
        -> particle exception
        -> validation.validate_shadow
        -> prosody and bracket filtering
        -> successful Surface entries become parser trace logs
```

`parse_candidates` does not catch owner-parser exceptions. An exception escapes
to the transform-level fallback contract. A `None` result is different: the
candidate produces no `Surface`, its source remains in the original token
render, and no parser-success log is emitted.

## Function manifest

The structural count includes conditional/loop/try/match and boolean-expression
AST nodes. It is a comparison aid, not a policy score.

| Function | LOC / structural nodes | Caller | Contract and disposition |
| --- | ---: | --- | --- |
| `parse_candidates` | 14 / 5 | production core and public package export | type validation, candidate-order iteration, omit `None`; keep cohesive |
| `_parse_candidate` | 98 / 41 | `parse_candidates` | explicit owner dispatch and common string-reading Surface assembly; unsafe to convert to registry |
| `_make_k_hangul_lexical_surface` | 31 / 2 | `_parse_candidate` | mixed generated/original core-span pieces |
| `_make_acronym_hangul_hyphen_surface` | 16 / 2 | `_parse_candidate` | owner-local three-piece provenance from lexicon parser |
| `_make_large_unit_surface` | 16 / 2 | `_parse_candidate` | owner-local numeric/suffix provenance from large-unit parser |
| `_make_multiplier_surface` | 18 / 3 | `_parse_candidate` | expands from core span to full span and consumes original suffix; policy-distinct |

`parse_candidates` is intentionally public through `engine.span_engine`; the
other functions remain private.

## Scanner owner to parser dispatch manifest

### Literal, protected and lexical

| Scanner/candidate owner | Parser path | Success surface | Failure/preserve behavior |
| --- | --- | --- | --- |
| `preserve` | no dispatch branch by design | none | original source render, no parser log; claim remains `claim_type=preserve` |
| `dictionary` | `dictionary_reading(raw)` | common core-span generated surface | `None` omits surface |
| `finance_index` | finance-index parser | common core-span generated surface | `None` omits surface |
| `k_hangul_lexical` | dedicated builder | generated `케이` plus original Hangul pieces | invalid reading returns `None` |
| `lexical_compound` | lexical reading | common core-span generated surface | `None` omits surface |
| `acronym_hangul_hyphen` | dedicated builder | generated acronym, original hyphen and Hangul pieces | missing owner metadata returns `None` |
| `acronym_fallback` | uppercase spelling | common core-span generated surface | `None` omits surface |
| `single_letter_alnum_code` | code parser | common core-span generated surface | owner/full-consume mismatch returns `None` |
| `managed_acronym_numeric_code` | managed-code parser | common core-span generated surface | invalid metadata returns `None` |
| `two_block_hyphen_code` | code parser | common core-span generated surface | invalid metadata returns `None` |
| `mixed_alnum_code_separator` | code parser | common core-span generated surface | invalid metadata returns `None` |

Protected literals and brackets claim/exclude source spans before parsing. The
protected-literal scanners emit `owner=preserve`, so no generated Surface is
created. Bracket ranges are not parser candidates.

### Date, time, semantic pairs and special numbers

| Owner | Parser | Span/render result | Distinct failure contract |
| --- | --- | --- | --- |
| `date` | date parser | common core span | typed date metadata required |
| `time` | time parser | common core span | strong/preserve time ownership already decided by scanner |
| `colon_semantic_pair` | range parser | common core span | reading metadata required |
| `multi_colon_numeric` | range parser | common core span | reading metadata required |
| `korean_da_score_pair` | owner parser returning `Surface` | custom delimiter provenance | parser validates multiple metadata spans |
| `event` | event parser | common core span | event metadata required |
| `emergency` | emergency parser | common core span | contextual owner metadata required |
| `public_number` | public-number parser | common core span | public-number gate remains scanner-owned |
| `phone` | `phone_reading(raw)` | common core span | raw pattern parse only |

### Range, separator and middle dot

| Owner | Parser | Contract |
| --- | --- | --- |
| `spaced_hyphen_numeric_blocks` | spaced-hyphen parser | source separator and spaces reflected in reading |
| `range` | range parser | owner-local reading metadata, core span |
| `range_with_unit` | range parser | range-scanner subtype; shared suffix/unit already full-consumed |
| `colon_semantic_pair` | range parser | semantic-pair subtype |
| `multi_colon_numeric` | range parser | timecode/semantic subtype |
| `middle_dot_numeric` | middle-dot parser | block-mode metadata required |
| `hyphen_digit_blocks` | raw hyphen digit reading | core span only |

`numeric_delimited_hyphen_range` is the scanner stage name, not a candidate
owner; it emits `range` or `range_with_unit`. `spaced_separator_preserve`
emits `preserve` and intentionally has no parser branch.

### Currency, decimal, ratio and multiplier

| Owner | Parser/builder | Result |
| --- | --- | --- |
| `large_unit_atomic` | dedicated large-unit builder | core-span Surface with numeric/suffix provenance pieces |
| `currency` | currency parser | common core-span generated Surface |
| `percent_point` | percent/point parser | common core-span generated Surface |
| `duration` | duration parser | common core-span generated Surface |
| `multiplier` | dedicated full-span builder | full-span Surface; generated numeric plus original multiplier suffix |
| `fraction` | fraction parser | common core-span Surface |
| `decimal_registered_suffix` | registered-suffix parser | common core-span Surface |
| `numeric_suffix` | numeric-suffix parser | common core-span Surface |
| `decimal` | decimal parser | common core-span Surface |
| `number` | spaced integer reader | final generic core-span Surface |

Leading-zero, comma, fractional-width, sign and atomic-preserve decisions are
made by scanners/owner parsers. The dispatch must not reinterpret them.

### Unit, counter and signed owners

| Owner group | Parser | Shared dispatch reason |
| --- | --- | --- |
| `caret_power_unit`, `simple_unit`, `special_unit` | unit parser | the unit parser rechecks exactly this owner set and reading metadata |
| `compound_slash_unit` | compound-slash parser | compound inventory and metadata remain owner-local |
| `compound_exact_unit` | compound-exact parser | exact compound inventory remains owner-local |
| `counter_noun` | counter parser | counter metadata and core numeric span |
| `signed_temperature`, `signed_degree`, `signed_number` | signed parser | signed parser owns sign/unit-specific policy |
| `ph` | pH parser | pH-specific metadata and unsafe-tail preserve |
| `jamo` | jamo parser | jamo metadata and raw boundary |
| `administrative_suffix` | administrative parser | numeric core and administrative suffix metadata |

The caret-power scanner call occurs between compound-exact and special-unit
calls. `caret_power_unit` is a unit subtype supported by the parser; it is not a
separate entry in the frozen high-level `CLAIM_ORDER_DOC` snapshot. P4 does not
change either the tuple or execution order.

## Candidate-field and provenance contract

| Field | Parser-graph use | Decision |
| --- | --- | --- |
| `core_span` | raw slicing, common Surface span, nearly every owner parser | required |
| `full_span` | multiplier Surface and scanner iteration/full-consume logic | required; must not replace core span generically |
| `owner` | dispatch, owner-parser validation, Surface/RenderPiece owner | required |
| `surface_type` | Surface and RenderPiece metadata | required |
| `reason` | Surface metadata, then claim remains independently traced | required |
| `metadata` | nearly all typed owner parsers and custom render-piece builders | required |
| `suffix_spans` | multiplier and other owner-local parse/render helpers | required |
| `trailing_particle_span` | model/API contract, currently not populated or consumed by production parser | no proven deletion: public model tests and external construction remain possible |

The `Surface.trailing_particle*` model fields likewise remain public model
contracts. Production particle adjustment currently operates after rendering
over source-mapped pieces; P4 does not migrate that policy into parser dispatch.

## Parse, render and trace failure matrix

| Parser result | Surface list | Render | Parser log | Transform fallback |
| --- | --- | --- | --- | --- |
| string reading | common core-span Surface | one `GENERATED_READING` piece | success | none |
| custom Surface | owner-defined core/full span and pieces | exact custom provenance pieces | success | none |
| `None` | candidate omitted | original token source remains | none | none |
| exception | parse loop aborts | not rendered in core attempt | none for failed attempt | propagates to transform whole-input or segment-local policy |
| `owner=preserve` | no parser branch, hence `None` | original boundary/literal | none | none |

Only successful Surfaces generate parser trace entries. Their trace reason is
`phase7_owner_parse`, while the policy reason remains in the claim and Surface
metadata. P4 must preserve this separation.

## Exact-equivalent extraction candidate

### P4-A: core-span Surface assembly for custom render-piece owners

`_make_k_hangul_lexical_surface`,
`_make_acronym_hangul_hyphen_surface`, and `_make_large_unit_surface` all finish
with the same side-effect-free assembly after their owner-specific reading and
piece creation succeeds:

- `surface_type = candidate.surface_type or owner_default`;
- `owner = candidate.owner`;
- `raw` and `span = candidate.core_span`;
- caller-supplied `reading` and `render_pieces`;
- `metadata = {"reason": candidate.reason}`.

A private pure `_make_core_render_surface` can accept only those already
validated values. Owner parsing, `None` checks, piece construction, default
surface types and call order remain in the three callers. The multiplier is
excluded because it deliberately switches to `full_span` and full-span raw.

No second exact-equivalent candidate is selected. The common string-reading
Surface assembly is already centralized once at the end of `_parse_candidate`;
the owner parser groups are already grouped only where they call the same
parser. A dispatch dictionary or callable registry would change exception,
inspection and order characteristics without removing an exact duplicate.

## Policy-distinct; keep separate

- K-Hangul, acronym-Hangul and large-unit piece generation use different source
  partitions and validation metadata even though their final Surface fields
  match.
- Multiplier resembles large-unit rendering but consumes `full_span`, including
  the original suffix; combining it with core-span owners would change overlap
  and source provenance.
- `korean_da_score_pair` returns a complete custom Surface from its owner module
  and validates multiple numeric/delimiter spans; it must not enter the helper.
- Raw-only dictionary/acronym/phone/hyphen readers and candidate-aware parsers
  differ in accepted domain and exception behavior.
- Signed, unit and range groups already reflect identical parser functions, but
  their groups are not interchangeable with one another.
- `preserve` is an intentional absence of Surface, not a failed generated
  reading and not a parser owner to register.
- `core_span`, `full_span`, suffix spans, metadata and particle model fields
  must not be normalized into one generic candidate payload.

## Unsafe functions

`_parse_candidate` is an executable dispatch contract. Replacing its ordered
branches with a generic registry, changing unknown-owner behavior, or adding
exception masking is outside P4. `parse_candidates` fixes candidate ordering and
silent omission of `None`; it remains unchanged.

## Characterization plan

Before P4-A, public transform/trace tests must pin:

- K-Hangul mixed generated/original pieces and exact source spans;
- acronym-Hangul generated acronym, original hyphen and Hangul pieces;
- large-unit numeric/suffix pieces and exact source spans;
- multiplier full-span behavior as a negative control;
- a normal string-reading owner using the common generated piece;
- preserve candidate output with no parser log;
- exact claim owner/type/surface/reason/span, parser success fields, Surface
  reading, RenderPiece metadata and validation success;
- invalid direct candidates returning no Surface, while exceptions continue to
  escape rather than being masked.

## Checkpoint A evidence

- Parser/provenance/trace/fallback/precedence/protected target: 1,187 passed and
  4,783 deselected.
- Batch 1 through 8, Golden, empty audit, production isolation and comparison
  support: 117 passed.
- Full source suite: 6,212 passed and 109 binary tests deselected.
- Fixed 83-case paired-before samples with 20 corpus rounds per sample:
  1479.39, 1396.56, 1312.06, 1234.67 and 1322.84 microseconds per input;
  median/min/max 1322.84/1234.67/1479.39.
- Production code changes and output differences at this checkpoint: zero.

The same-session paired result takes precedence over historical WSL values.
P4-A adds no input-length scan. A repeated median regression of at least five
percent rejects the extraction.


## Checkpoints B and C result

- Seven public characterization tests were added before production changes.
  They pin normalized output, claim owner/type/surface/reason/span, parser
  success metadata, exact RenderPiece provenance/source spans, validation,
  preserve-without-Surface behavior, invalid-candidate omission and exception
  propagation.
- P4-A added private pure `_make_core_render_surface` and used it only after
  K-Hangul, acronym-Hangul and large-unit owner parsing and piece generation had
  succeeded. The three callers retain their own default surface type, `None`
  checks, piece construction and ordering.
- `_parse_candidate`, `parse_candidates`, the common string-reading Surface
  path, multiplier full-span builder and Korean-`대` score custom Surface were
  unchanged. No dispatch registry or exception fallback was added.
- `parser.py` changed from 265 LOC / 6 functions to 279 LOC / 7 functions. The
  custom builders changed from 31/16/16 LOC to 30/14/14 LOC and share one
  explicit 17-LOC assembly contract. `_parse_candidate` remains 98 LOC / 41
  structural nodes because P4 intentionally does not hide owner dispatch.
- Final AST audit found zero private top-level zero-load functions, zero unused
  imports and zero exact duplicate function bodies. The new helper has exactly
  three internal callers.
- No parser dispatch was proven stale. Literal and dynamically assigned unit,
  signed, hyphen and range sub-owners all have scanner factories and owning
  tests. `preserve` intentionally has no parser branch.
- `SurfaceCandidate.trailing_particle_span` has no current production parser
  consumer, but it remains a public validated model field with direct tests; it
  is not proven private dead code and was retained.
- Repository-wide test AST audit found historical duplicates. P4 removed only
  two exact owner/parser-trace duplicates: `+3°` signed-degree trace and `90km`
  simple-unit trace. Their identical assertions remain in the explicit
  signed/special-unit and compound/simple-unit precedence owning tests. Other
  groups retain distinct import, comparison, phase-regression, fixture or
  boundary contracts, or fall outside P4 scope.
- No production symbol, owner branch, import, candidate field or file was
  deleted in P4-C.

P4-A focused validation was 214 passed, expanded parser/provenance/trace target
was 1,194 passed with 4,783 deselected, and the canonical set was 117 passed.
After test cleanup, the two owning files plus P4 characterization were 20
passed; the canonical set remained 117 passed.

## Final validation

- Full source suite: 6,217 passed and 109 binary tests deselected.
- Explicit PyInstaller rebuild and local binary smoke: passed.
- Rebuilt-binary selected set: 109 passed and 6,217 source tests deselected,
  including archive production-module isolation.
- Golden 13 plus Batch 1 through 8 (70): all 83 source, rebuilt-binary, API and
  expected strings were directly compared and byte-exact.
- Fixed 83-case isolated paired-after samples were 1251.20, 1215.37, 1234.78,
  1205.90 and 1221.06 microseconds per input; median/min/max
  1221.06/1205.90/1251.20. The median is about 7.7 percent below the same-session
  paired-before 1322.84. A discarded concurrent pytest measurement was not used
  because CPU contention made it non-comparable. WSL/CPU scheduling remains
  uncontrolled.
- Production output differences: zero. Batch fixture states, Golden expected
  values, legacy audit `[]`, parser order, public entrypoints and comparison
  isolation are unchanged. No allowed-diff fixture was added or modified.

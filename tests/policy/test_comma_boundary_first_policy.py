import pytest

from engine.main import transform
from engine.span_engine.transform import transform_with_trace
from tests._policy_case import TextCase, assert_exact
from tests._span_prosody import apply_span_prosody


SENTENCE_LOCAL_CASES = [
    TextCase(
        case_id="sentence-local-leading-time-and-subordinate",
        text="오늘 아침 우리는 바로 출발한다. 회의를 마치고 나서 우리는 바로 이동한다",
        expected="오늘 아침, 우리는 바로 출발한다. 회의를 마치고 나서, 우리는 바로 이동한다",
        rule="prosody / sentence-local budget",
        reason="Each sentence must be analyzed independently so both local boundaries can survive without a cross-sentence pass.",
    ),
    TextCase(
        case_id="sentence-local-connector-and-time-frame",
        text="그리고 우리는 바로 출발한다. 내일 서울에서 우리는 다시 만난다",
        expected="그리고, 우리는 바로 출발한다. 내일 서울에서, 우리는 다시 만난다",
        rule="prosody / sentence-local budget",
        reason="A connector boundary in one sentence must not change the comma budget of the next sentence.",
    ),
]


LEADING_CONNECTOR_POSITIVE_CASES = [
    TextCase(
        case_id="leading-connector-geurigo",
        text="그리고 우리는 바로 출발한다",
        expected="그리고, 우리는 바로 출발한다",
        rule="prosody / leading connector",
        reason="Sentence-initial connectors are the strongest allowlisted boundary type.",
    ),
    TextCase(
        case_id="leading-connector-hajiman",
        text="하지만 일정은 유지된다",
        expected="하지만, 일정은 유지된다",
        rule="prosody / leading connector",
        reason="An initial adversative connector should receive one conservative comma.",
    ),
    TextCase(
        case_id="leading-connector-geureona",
        text="그러나 계획은 바뀌지 않는다",
        expected="그러나, 계획은 바뀌지 않는다",
        rule="prosody / leading connector",
        reason="그러나 is explicitly listed in the connector allowlist.",
    ),
    TextCase(
        case_id="leading-connector-ttaraseo",
        text="따라서 후속 조치를 검토한다",
        expected="따라서, 후속 조치를 검토한다",
        rule="prosody / leading connector",
        reason="따라서 is a sentence-initial connector and should receive a comma when the predicate follows clearly.",
    ),
]


LEADING_TIME_FRAME_CASES = [
    TextCase(
        case_id="leading-time-frame-two-eojeol",
        text="오늘 아침 우리는 바로 출발한다",
        expected="오늘 아침, 우리는 바로 출발한다",
        rule="prosody / leading time frame",
        reason="A sentence-initial time frame chunk may take one comma when a full predicate follows.",
    ),
    TextCase(
        case_id="leading-time-frame-time-plus-frame",
        text="내일 서울에서 우리는 다시 만난다",
        expected="내일 서울에서, 우리는 다시 만난다",
        rule="prosody / leading time frame",
        reason="A narrow initial time-plus-frame adverbial may receive one comma before the main clause.",
    ),
]


LEADING_TIME_FRAME_NEGATIVE_CASES = [
    TextCase(
        case_id="leading-time-frame-short-simple-negative",
        text="오늘 바로 출발한다",
        expected="오늘 바로 출발한다",
        rule="prosody / leading time frame negative",
        reason="A short simple sentence should stay comma-free even when it starts with a time-like token.",
    ),
    TextCase(
        case_id="leading-time-frame-basic-topic-negative",
        text="오늘 회의는 예정대로 시작된다",
        expected="오늘 회의는 예정대로 시작된다",
        rule="prosody / leading time frame negative",
        reason="A basic topic-predicate sentence must not be split just because the first eojeol is time-like.",
    ),
    TextCase(
        case_id="leading-time-frame-existing-punctuation-negative",
        text="오늘 아침, 우리는 바로 출발한다",
        expected="오늘 아침, 우리는 바로 출발한다",
        rule="prosody / leading time frame negative",
        reason="If punctuation already marks the boundary, prosody must not add a second comma.",
    ),
]


SUBORDINATE_CLAUSE_POSITIVE_CASES = [
    TextCase(
        case_id="subordinate-go-naseo",
        text="회의를 마치고 나서 우리는 바로 출발한다",
        expected="회의를 마치고 나서, 우리는 바로 출발한다",
        rule="prosody / subordinate clause",
        reason="A marked clause ending in 고 나서 may receive a comma before the following main clause.",
    ),
    TextCase(
        case_id="subordinate-han-dwi",
        text="자료를 정리한 뒤 우리는 결과를 공유한다",
        expected="자료를 정리한 뒤, 우리는 결과를 공유한다",
        rule="prosody / subordinate clause",
        reason="A clause ending in 한 뒤 is an allowlisted subordinate boundary when the right side is a full predicate.",
    ),
    TextCase(
        case_id="subordinate-gyeongu",
        text="예산을 검토하는 경우 우리는 즉시 보고한다",
        expected="예산을 검토하는 경우, 우리는 즉시 보고한다",
        rule="prosody / subordinate clause",
        reason="A marked conditional clause should be allowed one comma at its end.",
    ),
    TextCase(
        case_id="subordinate-jiman",
        text="비가 오지만 우리는 출발한다",
        expected="비가 오지만, 우리는 출발한다",
        rule="prosody / subordinate clause",
        reason="A clear subordinate clause ending in 지만 may receive one comma before the main clause.",
    ),
]


SUBORDINATE_CLAUSE_NEGATIVE_CASES = [
    TextCase(
        case_id="subordinate-suffix-like-noun-negative",
        text="검토하는 경우의 수를 줄인다",
        expected="검토하는 경우의 수를 줄인다",
        rule="prosody / subordinate clause negative",
        reason="A suffix-like noun phrase such as 경우의 수 must not be mistaken for a clause boundary.",
    ),
    TextCase(
        case_id="subordinate-suffix-like-noun-chunk-negative",
        text="정리한 뒤쪽 자료를 검토한다",
        expected="정리한 뒤쪽 자료를 검토한다",
        rule="prosody / subordinate clause negative",
        reason="A lexical noun continuation such as 뒤쪽 must not trigger a subordinate comma.",
    ),
]


SERIAL_PARALLEL_POSITIVE_CASES = [
    TextCase(
        case_id="serial-parallel-four-items",
        text="사과와 배와 포도 그리고 귤을 챙겼다",
        expected="사과와 배와 포도, 그리고 귤을 챙겼다",
        rule="prosody / serial parallel",
        reason="Three-plus parallel items may receive one comma at the final coordinator boundary.",
    ),
    TextCase(
        case_id="serial-parallel-tools",
        text="연필과 공책과 지우개 그리고 자를 챙겼다",
        expected="연필과 공책과 지우개, 그리고 자를 챙겼다",
        rule="prosody / serial parallel",
        reason="A natural-language 3-plus list can take one conservative comma before the final item.",
    ),
]


SERIAL_PARALLEL_NEGATIVE_CASES = [
    TextCase(
        case_id="serial-parallel-binary-negative",
        text="사과와 배를 샀다",
        expected="사과와 배를 샀다",
        rule="prosody / serial parallel negative",
        reason="A simple binary phrase must remain comma-free.",
    ),
    TextCase(
        case_id="serial-parallel-binary-topic-negative",
        text="연필과 공책은 준비했다",
        expected="연필과 공책은 준비했다",
        rule="prosody / serial parallel negative",
        reason="A single binary coordination inside a topic phrase is not a 3-plus serial boundary.",
    ),
    TextCase(
        case_id="serial-parallel-numeric-negative",
        text="1과 2 그리고 3을 적었다",
        expected="1과 2 그리고 3을 적었다",
        rule="prosody / serial parallel negative",
        reason="Numeric enumerations are protected from serial comma insertion.",
    ),
    TextCase(
        case_id="serial-parallel-code-negative",
        text="A-1과 B-2 그리고 C-3을 비교한다",
        expected="A-1과 B-2 그리고 C-3을 비교한다",
        rule="prosody / serial parallel negative",
        reason="Code-like identifiers must not be treated as natural-language list items.",
    ),
]


TOPIC_NEGATIVE_CASES = [
    TextCase(
        case_id="topic-basic-host-negative",
        text="주최 측은 일정을 발표했다",
        expected="주최 측은 일정을 발표했다",
        rule="prosody / topic negative",
        reason="A basic topic-predicate sentence must remain comma-free.",
    ),
    TextCase(
        case_id="topic-basic-world-ranking-negative",
        text="세계 4위 선수는 오늘 출전한다",
        expected="세계 4위 선수는 오늘 출전한다",
        rule="prosody / topic negative",
        reason="A topic phrase with a simple predicate is not an explicit shift boundary.",
    ),
    TextCase(
        case_id="topic-basic-plan-negative",
        text="회의 계획은 곧 발표된다",
        expected="회의 계획은 곧 발표된다",
        rule="prosody / topic negative",
        reason="Length alone must not trigger a topic comma.",
    ),
    TextCase(
        case_id="topic-basic-host-frame-negative",
        text="주최 측은 오늘 일정을 발표했다",
        expected="주최 측은 오늘 일정을 발표했다",
        rule="prosody / topic negative",
        reason="A following frame token does not by itself create an explicit topic-shift boundary.",
    ),
]


LONG_TOPIC_CONSERVATIVE_CASES = [
    TextCase(
        case_id="long-topic-explicit-shift-quarter",
        text="연구팀 운영 계획은 이번 분기부터 전면 조정된다",
        expected="연구팀 운영 계획은 이번 분기부터 전면 조정된다",
        rule="prosody / canonical conservative topic boundary",
        reason="Length and a following frame phrase do not license an unregistered production topic comma.",
        classification="canonical",
    ),
    TextCase(
        case_id="long-topic-explicit-shift-stage",
        text="대외 협력 운영 방안은 이후 단계에서 다시 검토된다",
        expected="대외 협력 운영 방안은 이후 단계에서 다시 검토된다",
        rule="prosody / canonical conservative topic boundary",
        reason="Production prosody preserves the topic boundary because no registered insertion rule claims it.",
        classification="canonical",
    ),
]


BINARY_PHRASE_NEGATIVE_CASES = [
    TextCase(
        case_id="binary-phrase-fruit",
        text="사과와 배를 샀다",
        expected="사과와 배를 샀다",
        rule="prosody / binary phrase negative",
        reason="A single A와 B phrase must be preserved without internal comma insertion.",
    ),
    TextCase(
        case_id="binary-phrase-supplies",
        text="책과 연필을 챙겼다",
        expected="책과 연필을 챙겼다",
        rule="prosody / binary phrase negative",
        reason="A simple binary object phrase is explicitly protected.",
    ),
    TextCase(
        case_id="binary-phrase-topic",
        text="비용과 일정은 확정됐다",
        expected="비용과 일정은 확정됐다",
        rule="prosody / binary phrase negative",
        reason="A single binary topic phrase must not receive a prosodic comma.",
    ),
    TextCase(
        case_id="binary-phrase-location",
        text="서울과 부산을 잇는다",
        expected="서울과 부산을 잇는다",
        rule="prosody / binary phrase negative",
        reason="A binary location phrase must remain intact.",
    ),
]


NUMERIC_DENSITY_CASES = [
    TextCase(
        case_id="numeric-density-heavy-default-no-comma",
        text="2025년 1월 3일 13:05에 100원을 결제한다",
        expected="이천이십오년 일월 삼일 십삼시 오분에 백 원을 결제한다",
        rule="prosody / numeric density negative",
        reason="A numeric-heavy protected sentence should default to no comma.",
    ),
    TextCase(
        case_id="numeric-density-heavy-strong-boundary-one-exception",
        text="그리고 2025년 1월 3일 13:05에 100원을 결제한다",
        expected="그리고, 이천이십오년 일월 삼일 십삼시 오분에 백 원을 결제한다",
        rule="prosody / numeric density exception",
        reason="A heavy protected sentence may still allow one strong connector boundary.",
    ),
]


PROTECTED_SPAN_CASES = [
    TextCase(
        case_id="protected-span-event-dot",
        text="12.12 사태 자료를 검토한다",
        expected="십이십이 사태 자료를 검토한다",
        rule="prosody / protected span negative",
        reason="An event-dot phrase is protected and must remain internally intact.",
    ),
    TextCase(
        case_id="protected-span-emergency",
        text="119에 바로 신고한다",
        expected="일일구에 바로 신고한다",
        rule="prosody / protected span negative",
        reason="A normalized emergency number is protected from internal comma insertion.",
    ),
    TextCase(
        case_id="protected-span-middle-dot",
        text="공01 · 공09 자료를 확인한다",
        expected="공01 · 공09 자료를 확인한다",
        rule="prosody / protected span negative",
        reason="A structured middle-dot surface must remain comma-free.",
    ),
]


DIRECT_PROTECTED_SURFACE_CASES = [
    TextCase(
        case_id="protected-surface-ip",
        text="192.168.0.1 주소를 확인한다",
        expected="192.168.0.1 주소를 확인한다",
        rule="prosody / protected surface negative",
        reason="IP-like expressions are protected spans in the surface string.",
    ),
    TextCase(
        case_id="protected-surface-path",
        text="C:/Program Files/Test 경로를 연다",
        expected="C:/Program Files/Test 경로를 연다",
        rule="prosody / protected surface negative",
        reason="Path-like expressions must remain untouched by comma insertion.",
    ),
    TextCase(
        case_id="protected-surface-phonetic-currency",
        text="백 원을 냈다",
        expected="백 원을 냈다",
        rule="prosody / protected surface negative",
        reason="A phonetic-bound currency phrase must stay intact.",
    ),
]


EXISTING_PUNCTUATION_NEGATIVE_CASES = [
    TextCase(
        case_id="existing-punctuation-leading-connector",
        text="그러나, 우리는 출발한다",
        expected="그러나, 우리는 출발한다",
        rule="prosody / existing punctuation negative",
        reason="An existing comma must suppress duplicate insertion at the same boundary.",
    ),
    TextCase(
        case_id="existing-punctuation-leading-time-frame",
        text="오늘 아침, 우리는 바로 출발한다",
        expected="오늘 아침, 우리는 바로 출발한다",
        rule="prosody / existing punctuation negative",
        reason="A boundary adjacent to existing punctuation must be discarded.",
    ),
    TextCase(
        case_id="existing-punctuation-multi-sentence",
        text="그리고, 우리는 바로 출발한다. 하지만, 일정은 유지된다",
        expected="그리고, 우리는 바로 출발한다. 하지만, 일정은 유지된다",
        rule="prosody / existing punctuation negative",
        reason="Already punctuated sentence boundaries must not receive extra prosody commas in a later pass.",
    ),
]


PHONETIC_BOUNDARY_NEGATIVE_CASES = [
    TextCase(
        case_id="phonetic-boundary-time",
        text="13:05에 출발한다",
        expected="십삼시 오분에 출발한다",
        rule="prosody / phonetic boundary negative",
        reason="A phonetic time binding must survive prosody without internal comma insertion.",
    ),
    TextCase(
        case_id="phonetic-boundary-currency",
        text="100원을 냈다",
        expected="백 원을 냈다",
        rule="prosody / phonetic boundary negative",
        reason="A phonetic currency binding must remain unsplit.",
    ),
    TextCase(
        case_id="phonetic-boundary-time-in-clause",
        text="회의는 13:05에 시작한다",
        expected="회의는 십삼시 오분에 시작한다",
        rule="prosody / phonetic boundary negative",
        reason="Prosody must not insert commas inside or adjacent to a phonetic time chunk.",
    ),
]


EMERGENCY_NUMBER_NEGATIVE_CASES = [
    TextCase(
        case_id="emergency-number-topic",
        text="긴급번호 119는 경찰 신고 번호다",
        expected="긴급번호 일일구는 경찰 신고 번호다",
        rule="prosody / emergency number negative",
        reason="The confirmed emergency number reading must remain intact.",
    ),
    TextCase(
        case_id="emergency-number-connector",
        text="그리고 긴급번호 119에 바로 신고한다",
        expected="그리고, 긴급번호 일일구에 바로 신고한다",
        rule="prosody / emergency number negative",
        reason="Only the sentence-initial connector may receive a comma around an emergency-number phrase.",
    ),
]


MIDDLE_DOT_NEGATIVE_CASES = [
    TextCase(
        case_id="middle-dot-no-connector",
        text="공01 · 공09 자료를 확인한다",
        expected="공01 · 공09 자료를 확인한다",
        rule="prosody / middle dot negative",
        reason="A structured middle-dot surface must stay untouched when no strong boundary exists.",
    ),
    TextCase(
        case_id="middle-dot-connector-only",
        text="그리고 공01 · 공09 자료를 확인한다",
        expected="그리고, 공01 · 공09 자료를 확인한다",
        rule="prosody / middle dot negative",
        reason="Only the connector boundary may receive a comma; the middle-dot span must stay intact.",
    ),
]


BOUNDARY_COORDINATE_CASES = [
    TextCase(
        case_id="boundary-coordinate-space-positive",
        text="그리고 우리는 바로 출발한다",
        expected="그리고, 우리는 바로 출발한다",
        rule="prosody / boundary coordinate",
        reason="The allowlisted boundary is the whitespace between the connector and the following token.",
    ),
    TextCase(
        case_id="boundary-coordinate-no-space-connector-negative",
        text="그리고우리는 바로 출발한다",
        expected="그리고우리는 바로 출발한다",
        rule="prosody / boundary coordinate",
        reason="The first implementation may insert commas only at whitespace boundaries, not inside tokens.",
    ),
    TextCase(
        case_id="boundary-coordinate-no-space-time-negative",
        text="오늘아침 우리는 바로 출발한다",
        expected="오늘아침 우리는 바로 출발한다",
        rule="prosody / boundary coordinate",
        reason="A token-internal boundary must remain closed even when it resembles a time frame.",
    ),
    TextCase(
        case_id="boundary-coordinate-no-space-protected-negative",
        text="일일구에바로 신고한다",
        expected="일일구에바로 신고한다",
        rule="prosody / boundary coordinate",
        reason="No comma may be inserted inside an unspaced protected surface.",
    ),
]


NON_DESTRUCTIVE_RAW_INPUTS = [
    "그리고 우리는 바로 출발한다",
    "오늘 아침 우리는 바로 출발한다",
    "회의를 마치고 나서 우리는 바로 출발한다",
    "12.12 사태 자료를 검토한다",
    "그리고 긴급번호 119에 바로 신고한다",
    "공01 · 공09 자료를 확인한다",
]


@pytest.mark.parametrize("case", SENTENCE_LOCAL_CASES, ids=lambda case: case.case_id)
def test_sentence_local_budget_cases(case: TextCase):
    assert_exact(apply_span_prosody(case.text), case)


def test_multi_sentence_prosody_is_recorded_only_as_generated_punctuation():
    source = "주최 측은 일정을 발표했다. 세계 4위 선수는 오늘 출전한다"
    output = transform_with_trace(source)
    assert output.normalized_text == transform(source)
    assert output.trace is not None
    assert not output.trace.prosody_logs


@pytest.mark.parametrize("case", LEADING_CONNECTOR_POSITIVE_CASES, ids=lambda case: case.case_id)
def test_leading_connector_positive_cases(case: TextCase):
    assert_exact(apply_span_prosody(case.text), case)


@pytest.mark.parametrize("case", LEADING_TIME_FRAME_CASES, ids=lambda case: case.case_id)
def test_leading_time_frame_positive_cases(case: TextCase):
    assert_exact(apply_span_prosody(case.text), case)


@pytest.mark.parametrize("case", LEADING_TIME_FRAME_NEGATIVE_CASES, ids=lambda case: case.case_id)
def test_leading_time_frame_negative_cases(case: TextCase):
    assert_exact(apply_span_prosody(case.text), case)


@pytest.mark.parametrize("case", SUBORDINATE_CLAUSE_POSITIVE_CASES, ids=lambda case: case.case_id)
def test_subordinate_clause_positive_cases(case: TextCase):
    assert_exact(apply_span_prosody(case.text), case)


@pytest.mark.parametrize("case", SUBORDINATE_CLAUSE_NEGATIVE_CASES, ids=lambda case: case.case_id)
def test_subordinate_clause_negative_cases(case: TextCase):
    assert_exact(apply_span_prosody(case.text), case)


@pytest.mark.parametrize("case", SERIAL_PARALLEL_POSITIVE_CASES, ids=lambda case: case.case_id)
def test_serial_parallel_positive_cases(case: TextCase):
    assert_exact(apply_span_prosody(case.text), case)


@pytest.mark.parametrize("case", SERIAL_PARALLEL_NEGATIVE_CASES, ids=lambda case: case.case_id)
def test_serial_parallel_negative_cases(case: TextCase):
    assert_exact(apply_span_prosody(case.text), case)


@pytest.mark.parametrize("case", TOPIC_NEGATIVE_CASES, ids=lambda case: case.case_id)
def test_topic_basic_negative_cases(case: TextCase):
    assert_exact(apply_span_prosody(case.text), case)


@pytest.mark.parametrize("case", LONG_TOPIC_CONSERVATIVE_CASES, ids=lambda case: case.case_id)
def test_long_topic_unregistered_shift_preservation_cases(case: TextCase):
    assert_exact(apply_span_prosody(case.text), case)


@pytest.mark.parametrize("case", BINARY_PHRASE_NEGATIVE_CASES, ids=lambda case: case.case_id)
def test_binary_phrase_negative_cases(case: TextCase):
    assert_exact(apply_span_prosody(case.text), case)


@pytest.mark.parametrize("case", NUMERIC_DENSITY_CASES, ids=lambda case: case.case_id)
def test_numeric_density_cases(case: TextCase):
    assert_exact(transform(case.text), case)


@pytest.mark.parametrize("case", PROTECTED_SPAN_CASES, ids=lambda case: case.case_id)
def test_protected_span_cases(case: TextCase):
    assert_exact(transform(case.text), case)


@pytest.mark.parametrize("case", DIRECT_PROTECTED_SURFACE_CASES, ids=lambda case: case.case_id)
def test_direct_protected_surface_cases(case: TextCase):
    assert_exact(apply_span_prosody(case.text), case)


@pytest.mark.parametrize("case", EXISTING_PUNCTUATION_NEGATIVE_CASES, ids=lambda case: case.case_id)
def test_existing_punctuation_negative_cases(case: TextCase):
    assert_exact(apply_span_prosody(case.text), case)


@pytest.mark.parametrize("case", PHONETIC_BOUNDARY_NEGATIVE_CASES, ids=lambda case: case.case_id)
def test_phonetic_boundary_negative_cases(case: TextCase):
    assert_exact(transform(case.text), case)


@pytest.mark.parametrize("case", EMERGENCY_NUMBER_NEGATIVE_CASES, ids=lambda case: case.case_id)
def test_emergency_number_negative_cases(case: TextCase):
    assert_exact(transform(case.text), case)


@pytest.mark.parametrize("case", MIDDLE_DOT_NEGATIVE_CASES, ids=lambda case: case.case_id)
def test_middle_dot_negative_cases(case: TextCase):
    assert_exact(transform(case.text), case)


@pytest.mark.parametrize("case", BOUNDARY_COORDINATE_CASES, ids=lambda case: case.case_id)
def test_boundary_coordinate_cases(case: TextCase):
    assert_exact(apply_span_prosody(case.text), case)


@pytest.mark.parametrize("raw_text", NON_DESTRUCTIVE_RAW_INPUTS)
def test_prosody_remains_non_destructive_for_normalization_and_phonetic(raw_text: str):
    output = transform_with_trace(raw_text)
    assert output.trace is not None
    generated_commas = [
        piece
        for piece in output.render_pieces
        if piece.provenance == "GENERATED_PUNCT" and piece.text == ","
    ]
    comma_logs = [
        log
        for log in output.trace.prosody_logs
        if log.action == "insert_generated_punct"
    ]
    assert len(generated_commas) == len(comma_logs)
    assert output.normalized_text == transform(raw_text)

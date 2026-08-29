# TTS Preprocessor 단계 정책

이 문서는 TTS Preprocessor의 0~4단계 책임과 단계 간 계약의 단일 기준점이다. 구현·프롬프트·테스트·배포 문서는 이 정의와 다르게 단계를 설명해서는 안 된다.

## 프로젝트 목적

뉴스·방송 TTS가 정확하고 자연스러운 표준 한국어를 읽도록 입력 스크립트를 전처리한다. 결정적으로 판단할 수 있는 표면은 규칙 엔진이 처리하고, 문맥과 의미가 필요한 보류 표면만 LLM이 처리한다. 정상 한국어를 잘못 바꾸는 false positive를 발음 누락보다 위험하게 취급한다.

## 단계 계약

| 실행 단계 | 규칙 profile | LLM prompt | 책임 |
|---|---|---|---|
| 0 | 없음 | 없음 | 원문 passthrough |
| 1 | `simplified` | 없음 | TTS 필수 최소 규칙. 일반 영문 fallback 제외 |
| 2 | `default` | 없음 | 전체 deterministic normalization |
| 3 | `default` | level 1, `LLM_prompt.txt` | 잔여 숫자·영문·단위 문맥 처리, 제한적 복합명사 경계·쉼표. 기존 한글 보존 |
| 4 | `default` | level 2, `LLM_prompt_lv2.txt` | 3단계 + deterministic 발음 overlay + 폐쇄형 `이다` 축약 |

3~4단계는 각각 원문을 입력받아 내부에서 2단계 규칙 엔진을 한 번 실행한다. 다른 LLM 단계의 출력 문자열을 다음 단계 입력으로 사용하지 않는다.

단계의 포함 관계는 문자열을 순차 전달한다는 뜻이 아니라 처리 책임을 상속한다는 뜻이다. 4단계는 2단계 결과에 4단계 전용 deterministic 발음 overlay를 적용한 뒤 3단계의 명확한 잔여 읽기와 4단계 폐쇄형 변경을 수행한다. 추가 후보가 없더라도 하위 단계의 확정 작업을 생략하지 않는다.

## 규칙 엔진 숫자 발화 경계

1·2단계의 공통 owner가 숫자 읽기와 단위·counter·서수 표면 사이에 새 경계를
생성할 때는 공백 대신 ASCII 하이픈 U+002D(`-`)을 사용한다. 입력이 붙임형인지
ASCII 공백 한 칸을 포함했는지와 관계없이 같은 owner가 확정하면 동일한 표면으로
정규화한다. 하이픈 앞뒤에는 공백을 두지 않는다.

예: `1번째→첫-번째`, `제7번째→제-일곱-번째`,
`1~3번째→첫-번째에서 세-번째`, `3명/3 명→세-명`,
`5kg/5 kg→오-킬로그램`, `10bp→십-베이시스 포인트`,
`제1회→제-일회`, `제3 조→제-삼 조`.

이는 숫자 내부 공백, 부호·범위 문법의 공백, 날짜 성분 사이의 구조 공백을
전부 하이픈으로 바꾸는 규칙이 아니다. `N째`, `년·월·일`, `도`, `분기`,
붙임 시간 표면처럼 owner가 붙임을 확정한 표면은 기존 형태를 유지한다. 규칙
엔진이 생성한 숫자 발화 경계 하이픈은 provenance snapshot에서 locked reading의
일부이며, 3·4단계 LLM은 이를 공백으로 되돌리거나 삭제할 수 없다.

## 1단계와 2단계

2단계는 운영 서비스의 기준 규칙 엔진이다. 2단계 규칙을 추가하더라도 1단계 간소화 profile에서 제외된 항목은 1단계에 자동 포함하지 않는다. 2단계 출력에 영향을 주는 새 normalization 규칙은 사용자 검토 후 적용한다.

규칙 엔진은 rule definition, candidate detection, surface claim, rendering, provenance, validation, profile inclusion을 분리한다.

## 3단계

보호 영역 밖에 남은 숫자·영문·단위·기호를 문맥에 따라 처리한다. 입력의 기존 한글 어휘·조사·어미·시제·높임·부정은 변경하지 않는다. 일반 한국어 G2P 전사는 금지한다. 매우 긴 복합명사의 내부 의미 경계가 확실할 때 한글 글자와 순서를 유지한 ASCII 하이픈 하나를 넣을 수 있고, 의미 단위의 제한적인 쉼표를 추가할 수 있다. 두 변경은 발음식 한글 변경이 아니라 TTS 발화 경계를 표시하는 운율 처리다.

복합명사 발화 경계 후보는 조사·어미·서술어 활용부를 제외한 6음절 이상의 긴 명사 stem에만 생성한다. 고유명사·모델명·경로·코드·protected/locked span에는 적용하지 않으며, 하이픈 추가와 함께 한글 글자를 바꿀 수 없다. 이 후보가 있으면 3단계부터 LLM 호출 근거가 된다.

## 4단계

3단계의 통제된 상위 집합이다. 내부 호출 흐름은 다음과 같다.

```text
2단계 normalized_text + snapshot
        ↓
4단계 전용 deterministic pronunciation overlay
        ↓
stage4_base_text + overlay 결과가 locked된 snapshot
        ↓
cheap gate → 필요할 때만 Gemma 통합 1-pass
        ↓
provenance-aware validator
        ↓
speech_text 또는 stage4_base_text fallback
```

overlay는 코드에 등록된 exact whole-word 또는 승인된 조사·어미 경계만 바꾼다. 기존 폐쇄형 ㄴ 첨가·어휘화된 합성어 된소리와, 공식 근거가 확인된 `의견란, 임진란, 생산량, 결단력, 공권력, 동원령, 상견례, 횡단로, 이원론, 입원료, 구근류, 백분율`을 포함한다. 추가 exact 목록은 `한여름→한녀름, 직행열차→직행녈차, 영업용→영업뇽, 서울역→서울력, 휘발유→휘발류, 눈동자→눈똥자, 신바람→신빠람, 강가→강까, 강줄기→강쭐기`다. 더 긴 고유명사·제품명·합성어 내부, protected/locked span, 미승인 유사어에는 적용하지 않는다. 이 처리는 LLM 추론이 아니며 2단계 `normalized_text` 출력에는 영향을 주지 않는다. 외부 응답의 `normalized_text`는 계속 2단계 결과이고 `speech_text`에만 overlay 이후 결과가 반영된다.

LLM은 overlay 결과를 locked input으로 받아 다시 원형으로 되돌리거나 다른 발음형으로 바꿀 수 없다. LLM이 추가로 허용받는 한국어 변경은 받침 없는 일반 체언의 승인된 `이다` 계열 축약뿐이며, 3단계의 복합명사 발화 경계와 제한적 운율을 그대로 상속한다.

일반 연음·비음화·유음화·구개음화·된소리되기·ㅎ 축약·겹받침·활용형 음운 변화는 출력 철자에 반영하지 않는다.

### 향후 4단계 강화 참고 메모

별도 시험 단계와 문맥 동형어 `대가` 처리를 검토했으나 문맥 오판 위험에 비해 추가 품질 범위가 한 단어로 작아 제거했다. `대가`는 4단계에서도 원형을 유지한다. `인기→인끼`도 `개인기·무인기`와의 lexical identity를 현재 matcher만으로 안전하게 확정할 수 없어 등록하지 않는다. exact 발음 목록을 2단계로 승격하는 방안은 운영 중인 2단계 출력 변경과 TTS 자체 G2P 중복 위험 때문에 적용하지 않았다. 모든 `-량/-력/-률` 계열, 일반 사이시옷·일반 G2P, 조사 `의`, `효과` 같은 복수 표준발음도 false positive를 안전하게 제한할 근거가 없어 제외했다. 형태소 분석기와 raw substring 확장은 도입하지 않으며, 항상 2-pass도 latency와 오류 연쇄 대비 입증된 이득이 없어 채택하지 않았다. 향후 강화는 exact 항목의 공식 근거·positive/negative/contrast test가 확보된 경우 overlay 목록을 보수적으로 확장하는 순서로 검토한다.

## Pronunciation lexicon

4단계 전용 발음 사전은 2단계 규칙 사전과 분리한다. exact whole-word 또는 승인된 단일 조사·어미 경계, longest match, 더 긴 고유명사 내부 오적용 방지를 기본으로 한다. 복합 조사·연속 어미처럼 detector가 안전한 경계로 승인하지 않은 결합은 원형을 보존한다. protected/locked span이 아니고 exact 표면과 경계가 확인된 항목은 LLM 호출 전에 deterministic overlay로 적용하고 결과를 locked 처리한다. 각 항목은 stage, category, 공식 source를 가지며 사전 변경은 positive, negative, contrast test와 함께 이루어져야 한다.

4단계 overlay의 `ㄴ/ㄹ` exact 목록은 `의견란, 임진란, 생산량, 결단력, 공권력, 동원령, 상견례, 횡단로, 이원론, 입원료, 구근류`이며 국립국어원 표준 발음법 제20항의 예시를 따른다. `백분율[백뿐뉼]`은 제29항 근거로 별도 등록한다.

추가 목록 중 `한여름·직행열차·영업용`은 제29항의 ㄴ 첨가, `서울역·휘발유`는 제29항과 후속 유음화가 반영된 exact 최소 overlay다. `눈동자·신바람·강가·강줄기`는 제28항의 합성어 경음화 exact 예다. 지정된 부분만 표기하며 일반 음운 변화를 연쇄 전사하지 않는다.

공식 근거:

- [국립국어원 표준 발음법 제20항 관련 답변](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=&pageIndex=1&qna_seq=313452)
- [국립국어원 `백분율` 발음 답변](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=313432)
- [국립국어원 표준 발음법 제29항 관련 답변](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=307219)
- [국립국어원 표준 발음법 제28항 관련 답변](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?pageIndex=1&qna_seq=313557)

## Provenance와 locked span

규칙 엔진의 `RenderPiece`를 최종 normalized 좌표로 투영한 내부 snapshot을 3~4단계 validator에 전달한다. 규칙 엔진이 생성한 숫자·단위·통화·영문·약어 읽기와 그 내부의 ASCII 숫자 발화 경계, protected surface는 locked다. 4단계에서는 overlay가 좌표를 다시 투영하고 생성 발음 span을 `GENERATED_STAGE4_PRONUNCIATION`으로 locked 처리한다. metadata는 외부 API나 LLM 본문에 노출하지 않는다.

## Validator와 fallback

공통 검증 대상은 protected/locked span, 문장·문단 순서, 줄바꿈, 고정 구두점, Unicode, 공백, dash, 잔여 발화 표면이다.

- 3단계: 기존 한국어 변경 금지
- 4단계: overlay 결과를 locked하고 3단계 + 승인된 `이다` 축약만 LLM 변경으로 허용

Critical은 의미·숫자·보호 표면·locked reading·문장 구조 훼손이다. High는 예상 밖 한국어 rewrite, lexicon 위반, 미승인 발음 전사다. Medium은 잔여 발화 표면과 운율·형식 문제다.

4단계의 Critical/High 검증 실패는 retry 없이 LLM 입력인 `stage4_base_text`로 fallback한다. 따라서 확정 overlay 발음은 보존된다. 안전한 최종 `speech_text`는 fallback 값을 유지하되, 웹 UI는 선택적 `rejected_speech_text`와 `validation_failure`를 사용해 거절된 LLM 원출력과 변경 구간을 표시한다. 3단계의 기존 provider/validation 오류 계약은 유지한다.

## 외부 인터페이스

API는 level 0~4를 받는다. model 선택은 3~4단계에서만 허용한다. 외부 응답의 `normalized_text → speech_text` 계약과 기존 timing/gate 필드를 유지한다. 4단계 fallback 응답에는 UI 표시용 선택 필드 `rejected_speech_text`와 `validation_failure`를 추가할 수 있으며, 이때도 `speech_text`는 안전한 fallback 값이다.

## 품질 승인 기준

- 2단계 기존 출력 byte-exact 100% 동일
- Semantic Mutation 0
- Protected Span Mutation 0
- Numeric Reading Error 0
- 3단계 Unexpected Korean Rewrite 0
- 4단계 whitelist 밖 Korean Rewrite 0
- prompt placeholder 정확히 한 개
- 전체 비바이너리 테스트와 인터페이스 계약 테스트 통과

새 발음 규칙에서 false positive가 발생하면 범위를 확대하지 않고 해당 항목을 비활성화한다.

## 새 normalization 승인 절차

2단계 출력이 달라지는 숫자·단위·사전·한국어·운율 규칙과 1단계 profile 포함 범위 변경은 별도 승인 대상이다. 제안에는 현재 문제, 예상 개선, false positive 위험, 1·2단계 영향, positive/negative/contrast test 계획을 포함한다.

현재 승인 대기 항목은 다음과 같다. 이번 구현에서는 어느 항목도 1·2단계 출력에 적용하지 않았다.

| 후보 규칙 | 적용 단계 | 현재 문제 | 예상 개선 | false positive 위험 | 1단계 적용 여부 | 2단계 영향 | 권장 테스트 |
|---|---|---|---|---|---|---|---|
| 4단계 overlay exact 발음의 규칙 엔진 승격 | 향후 2단계 | 실제 TTS 오독률·음성 청취 근거 미수집 | 모든 단계에서 결정적 발음 | 출력 철자 변경 및 TTS 자체 G2P와 중복 | 아니요 | 있음 | 현 TTS A/B 음성, 조사 결합, 고유명사 내부 negative |
| 모든 `-률/-율`, `-량`, `-력`, `-란`, `-령`, `-료`, `-류` suffix 일반화 | 미정 | 어휘별 발음 차이 | 사전 누락 감소 가능 | 매우 높음 | 아니요 | 적용 시 있음 | 어휘별 공식 발음 corpus와 대규모 contrast |
| 일반 사이시옷·일반 ㄴ 첨가·일반 된소리 전사 | 미정 | TTS 오독 실측 없음 | 일부 발음 개선 가능 | 일반 G2P 과교정이 큼 | 아니요 | 적용 시 있음 | 실제 음성 오독 cluster와 negative corpus |
| 조사 `의` 뉴스 발화 스타일 | 미정 | 청취 평가 없음 | 낭독 자연성 가능 | 스타일 강제·의미 경계 훼손 | 아니요 | 적용 시 있음 | 뉴스 성우 블라인드 청취 평가 |
| `효과` 등 복수 표준 발음 고정 | 미정 | 운영 의도·TTS 현 발음 미확인 | 발음 일관성 가능 | 허용 발음 임의 제거 | 아니요 | 적용 시 있음 | 운영 사전·음성 평가·회귀 fixture 확인 |

sampling 파라미터와 seed 명시도 별도 품질 승인 대상이다. 현재 실제 평가에서 반복 변동 1건이 관찰됐지만 어떤 값을 선택해야 하는지는 입증되지 않았으므로 서버 기본값을 유지한다.

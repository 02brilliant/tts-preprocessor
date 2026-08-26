# TTS Preprocessor 단계 정책

이 문서는 TTS Preprocessor의 0~5단계 책임과 단계 간 계약의 단일 기준점이다. 구현·프롬프트·테스트·배포 문서는 이 정의와 다르게 단계를 설명해서는 안 된다.

## 프로젝트 목적

뉴스·방송 TTS가 정확하고 자연스러운 표준 한국어를 읽도록 입력 스크립트를 전처리한다. 결정적으로 판단할 수 있는 표면은 규칙 엔진이 처리하고, 문맥과 의미가 필요한 보류 표면만 LLM이 처리한다. 정상 한국어를 잘못 바꾸는 false positive를 발음 누락보다 위험하게 취급한다.

## 단계 계약

| 실행 단계 | 규칙 profile | LLM prompt | 책임 |
|---|---|---|---|
| 0 | 없음 | 없음 | 원문 passthrough |
| 1 | `simplified` | 없음 | TTS 필수 최소 규칙. 일반 영문 fallback 제외 |
| 2 | `default` | 없음 | 전체 deterministic normalization |
| 3 | `default` | level 1, `LLM_prompt.txt` | 잔여 숫자·영문·단위 문맥 처리. 기존 한국어 보존 |
| 4 | `default` | level 2, `LLM_prompt_lv2.txt` | 3단계 + 폐쇄형 발음 예외·이다 축약·운율 |
| 5 | `default` | level 3, `llm_prompt_lv3.txt` | 4단계 + 폐쇄형 발음 사전·문맥 동형어·ㄴ/ㄹ 예외. 시험 옵션 |

3~5단계는 각각 원문을 입력받아 내부에서 2단계 규칙 엔진을 한 번 실행한다. 다른 LLM 단계의 출력 문자열을 다음 단계 입력으로 사용하지 않는다.

## 1단계와 2단계

2단계는 운영 서비스의 기준 규칙 엔진이다. 2단계 규칙을 추가하더라도 1단계 간소화 profile에서 제외된 항목은 1단계에 자동 포함하지 않는다. 2단계 출력에 영향을 주는 새 normalization 규칙은 사용자 검토 후 적용한다.

규칙 엔진은 rule definition, candidate detection, surface claim, rendering, provenance, validation, profile inclusion을 분리한다.

## 3단계

보호 영역 밖에 남은 숫자·영문·단위·기호를 문맥에 따라 처리한다. 입력의 기존 한글 어휘·조사·어미·시제·높임·부정은 변경하지 않는다. 일반 한국어 G2P 전사는 금지하며, 의미 단위의 제한적인 쉼표만 추가할 수 있다.

## 4단계

3단계의 통제된 상위 집합이다. 코드에 등록된 폐쇄형 ㄴ 첨가와 어휘화된 합성어 된소리, 받침 없는 일반 체언의 승인된 `이다` 계열 축약, 긴 복합명사 발화 경계, 제한적 운율만 추가한다.

일반 연음·비음화·유음화·구개음화·된소리되기·ㅎ 축약·겹받침·활용형 음운 변화는 출력 철자에 반영하지 않는다.

## 5단계

사용자가 명시적으로 선택하는 시험 옵션이며 기본값이 아니다.

```text
2단계 normalized_text + internal provenance
        ↓
cheap candidate detector
        ↓
Gemma4-31B 통합 1-pass
        ↓
provenance-aware deterministic validator
        ↓
speech_text 또는 normalized_text fallback
```

5단계는 4단계 목록에 exact whole-word ㄴ/ㄹ 예외와 `대가` 문맥 동형어를 추가한다. `-률/-율`, `-량`, `-력`, `-란`, `-령`, `-료`, `-류`를 suffix 규칙으로 일반화하지 않는다. 일반 사이시옷, 조사 `의` 발화 스타일, 복수 허용 발음, 일반 G2P는 자동 처리하지 않는다.

항상 2-pass를 사용하지 않는다. 향후 contrast corpus에서 1-pass 문맥 동형어 정확도가 승인 기준을 만족하지 못하고 conditional decision pass가 유의미한 품질 향상을 보일 때만 다시 검토한다. decision pass가 도입되더라도 전체 문장을 rewrite하지 않고 span별 결정만 생성하며 다음 pass는 원본 `normalized_text`를 사용한다.

## Pronunciation lexicon

LLM용 발음 사전은 2단계 규칙 사전과 분리한다. exact whole-word 또는 승인된 조사·어미 경계, longest match, 더 긴 고유명사 내부 오적용 방지를 기본으로 한다. 단일 발음 항목과 문맥 동형어를 구분하며 각 항목은 stage, category, 공식 source를 가진다. 사전 변경은 positive, negative, contrast test와 함께 이루어져야 한다.

초기 5단계 `ㄴ/ㄹ` exact 목록은 `의견란, 임진란, 생산량, 결단력, 공권력, 동원령, 상견례, 횡단로, 이원론, 입원료, 구근류`이며 국립국어원 표준 발음법 제20항의 예시를 따른다. `백분율[백뿐뉼]`은 제29항 근거로 별도 등록한다. `대가(代價)[대까]`는 보수·값·희생의 결과라는 안전한 문맥에서만 변경 후보가 되며, 분야의 거장·전문가 문맥과 불확실한 문맥은 원형을 강제한다.

공식 근거:

- [국립국어원 표준 발음법 제20항 관련 답변](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=&pageIndex=1&qna_seq=313452)
- [국립국어원 `백분율` 발음 답변](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=313432)
- [한국어기초사전 `대가(代價)`](https://krdict.korean.go.kr/m/eng/searchResultView?ParaSenseSeq=&ParaWordNo=14261&fileNo=&imgCount=&multiMediaSeq=&nation=eng&searchKind=&searchKindValue=&shortenUrl=&studySeq=)

## Provenance와 locked span

규칙 엔진의 `RenderPiece`를 최종 normalized 좌표로 투영한 내부 snapshot을 3~5단계 validator에 전달한다. 규칙 엔진이 생성한 숫자·단위·통화·영문·약어 읽기와 protected surface는 locked다. metadata는 외부 API나 LLM 본문에 노출하지 않는다.

## Validator와 fallback

공통 검증 대상은 protected/locked span, 문장·문단 순서, 줄바꿈, 고정 구두점, Unicode, 공백, dash, 잔여 발화 표면이다.

- 3단계: 기존 한국어 변경 금지
- 4단계: 3단계 + 코드에 등록된 4단계 mutation만 허용
- 5단계: 4단계 + 코드에 등록된 5단계 mutation만 허용

Critical은 의미·숫자·보호 표면·locked reading·문장 구조 훼손이다. High는 예상 밖 한국어 rewrite, lexicon 위반, 미승인 발음 전사다. Medium은 잔여 발화 표면과 운율·형식 문제다.

5단계의 Critical/High 검증 실패는 retry 없이 전체 `normalized_text`로 fallback한다. 3·4단계의 기존 provider/validation 오류 계약은 유지한다.

## 외부 인터페이스

API는 level 0~5를 받는다. model 선택은 3~5단계에서만 허용한다. 외부 응답의 `normalized_text → speech_text` 계약과 기존 timing/gate 필드를 유지한다. 5단계 실행 파일명은 `tts-preprocessor-llm-pronunciation`이며 Windows에서는 `.exe`가 붙는다.

## 품질 승인 기준

- 2단계 기존 출력 byte-exact 100% 동일
- Semantic Mutation 0
- Protected Span Mutation 0
- Numeric Reading Error 0
- 3단계 Unexpected Korean Rewrite 0
- 4·5단계 whitelist 밖 Korean Rewrite 0
- prompt placeholder 정확히 한 개
- 전체 비바이너리 테스트와 인터페이스 계약 테스트 통과

새 발음 규칙에서 false positive가 발생하면 범위를 확대하지 않고 해당 항목을 비활성화한다.

실제 Gemma4-31B 제한 표본 결과와 측정 한계는 `docs/Gemma4_31B_level_evaluation_2026-08-26.md`에 기록한다.

## 새 normalization 승인 절차

2단계 출력이 달라지는 숫자·단위·사전·한국어·운율 규칙과 1단계 profile 포함 범위 변경은 별도 승인 대상이다. 제안에는 현재 문제, 예상 개선, false positive 위험, 1·2단계 영향, positive/negative/contrast test 계획을 포함한다.

현재 승인 대기 항목은 다음과 같다. 이번 구현에서는 어느 항목도 1·2단계 출력에 적용하지 않았다.

| 후보 규칙 | 적용 단계 | 현재 문제 | 예상 개선 | false positive 위험 | 1단계 적용 여부 | 2단계 영향 | 권장 테스트 |
|---|---|---|---|---|---|---|---|
| 5단계 exact ㄴ/ㄹ 사전의 규칙 엔진 승격 | 향후 2단계 | 실제 TTS 오독률·음성 청취 근거 미수집 | LLM 없이 결정적 발음 | 출력 철자 변경 및 TTS 자체 G2P와 중복 | 아니요 | 있음 | 현 TTS A/B 음성, 조사 결합, 고유명사 내부 negative |
| 모든 `-률/-율`, `-량`, `-력`, `-란`, `-령`, `-료`, `-류` suffix 일반화 | 미정 | 어휘별 발음 차이 | 사전 누락 감소 가능 | 매우 높음 | 아니요 | 적용 시 있음 | 어휘별 공식 발음 corpus와 대규모 contrast |
| 일반 사이시옷·일반 ㄴ 첨가·일반 된소리 전사 | 미정 | TTS 오독 실측 없음 | 일부 발음 개선 가능 | 일반 G2P 과교정이 큼 | 아니요 | 적용 시 있음 | 실제 음성 오독 cluster와 negative corpus |
| 조사 `의` 뉴스 발화 스타일 | 미정 | 청취 평가 없음 | 낭독 자연성 가능 | 스타일 강제·의미 경계 훼손 | 아니요 | 적용 시 있음 | 뉴스 성우 블라인드 청취 평가 |
| `효과` 등 복수 표준 발음 고정 | 미정 | 운영 의도·TTS 현 발음 미확인 | 발음 일관성 가능 | 허용 발음 임의 제거 | 아니요 | 적용 시 있음 | 운영 사전·음성 평가·회귀 fixture 확인 |

sampling 파라미터와 seed 명시도 별도 품질 승인 대상이다. 현재 실제 평가에서 반복 변동 1건이 관찰됐지만 어떤 값을 선택해야 하는지는 입증되지 않았으므로 서버 기본값을 유지한다.

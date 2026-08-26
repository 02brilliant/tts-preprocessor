# Gemma4-31B 3~5단계 비교 평가 (2026-08-26)

단계 정책은 `docs/TTS_Preprocessor_level_policy.md`를 따른다. 이 문서는 구현 완료 시점의 제한된 실제 모델 점검 기록이며 대규모 음성 청취 평가를 대신하지 않는다.

## 환경과 방법

- 모델 ID: `gemma4-31B-it (vLLM)`
- upstream model: `google/gemma-4-31B-it`
- provider: OpenAI-compatible vLLM Chat Completions
- 표본: 13개. 숫자·단위, protected URL/SKU, 일반 G2P negative, 4단계 ㄴ 첨가·된소리·축약, 5단계 ㄴ/ㄹ·백분율·대가 3문맥, 신고 contrast, 2문단 병렬 요청
- A/C: 평가 당시 배포돼 있던 기존 3·4단계 API
- B/D/E: 현재 작업 트리의 개선 3·4단계와 신규 5단계를 같은 vLLM endpoint에서 직접 실행
- 모든 품질 결과는 현재의 엄격한 단계별 validator로 다시 판정했다.
- 서버가 반환한 `usage.prompt_tokens`와 `usage.completion_tokens`만 기록했다. 기존 배포 API가 usage를 외부에 노출하지 않으므로 A/C의 합계는 미측정이다.
- 요청 body는 기존 계약대로 `model`, `messages`, `stream=false`만 보낸다. temperature, top-p, top-k, repetition penalty, seed는 명시하지 않아 서버 기본값을 사용했다.
- timeout 기본값은 300초, 문단 병렬 상한은 8이다. 2문단 표본은 2개 upstream 요청을 병렬 실행했다.
- GPU 종류·수, quantization, tensor parallel, context limit, prompt/KV cache 정책과 GPU utilization은 이 저장소나 응답에 노출되지 않아 측정하지 못했다.

## 1·2단계 출력 보호

수정 전 `tests/fixtures/production_golden.jsonl` 13건을 1단계와 2단계에 각각 실행해 `id`, `level1`, `level2`의 compact UTF-8 JSON을 baseline으로 고정했다. 수정 전후 payload는 모두 3,178 bytes이며 SHA-256은 `ecdc04e6e443503e4d759d304bb469d958bcc6adc3afd9903206c15400ef79c0`로 byte-exact 동일하다.

## 최종 실행 결과

| 설정 | 표본 | LLM 호출 표본 / upstream 호출 | validator 실패 | 발음 FP / FN | fallback | provider p50 / p95 ms | prompt / completion tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| A 기존 3단계 | 13 | 4 / 4 | 0 | 0 / 0 | 0 | 446.596 / 546.190 | 미노출 |
| B 개선 3단계 | 13 | 4 / 5 | 0 | 0 / 0 | 0 | 392.136 / 492.490 | 8,924 / 79 |
| C 기존 4단계 | 13 | 13 / 13 | 0 | 0 / 0 | 0 | 331.469 / 564.887 | 미노출 |
| D 개선 4단계 | 13 | 13 / 14 | 0 | 0 / 0 | 0 | 269.356 / 487.790 | 30,179 / 163 |
| E 신규 5단계 | 13 | 13 / 14 | 0 | 0 / 0 | 0 | 307.075 / 490.995 | 57,283 / 166 |

13개뿐인 표본에서 관측한 p99는 신뢰 가능한 tail latency가 아니므로 승인 지표로 사용하지 않는다. 최종 실행에서 관측된 요청 전체 p99 값은 A/B/C/D/E 순서로 914.140 / 494.158 / 934.482 / 489.471 / 495.831 ms였으나, A/C는 HTTP·바이너리 실행 경로이고 B/D/E는 직접 source evaluation 경로이므로 전체 latency를 서로 직접 비교해서는 안 된다. 위 표의 provider elapsed가 더 가까운 비교값이다.

개선 4단계의 이전 반복 1회에서 13건 중 1건이 `UNEXPECTED_KOREAN_REWRITE`로 거절됐고 같은 상태의 재실행에서는 재현되지 않았다. 이후 4단계 prompt에 5단계 전용 어휘 변경 금지를 명시했고 최종 반복은 0건이었다. sampling을 명시하지 않는 기존 계약에서는 비결정성이 남으므로 더 큰 반복 평가가 필요하다.

## 동일 입력의 prompt token 측정

짧은 동일 입력 `국물은 같이 읽고 있습니다.`를 각 Git 기준 prompt와 개선 prompt에 넣어 서버 usage를 측정했다.

| prompt | Git 기준 | 개선 | 변화 |
|---|---:|---:|---:|
| 3단계 | 13,891 | 1,778 | -12,113 (-87.2%) |
| 4단계 | 17,632 | 2,153 | -15,479 (-87.8%) |
| 5단계 초안→완성본 | 3,967 | 4,089 | +122 (+3.1%) |

현재 파일 크기는 다음과 같다.

| 파일 | lines | words | bytes |
|---|---:|---:|---:|
| `LLM_prompt.txt` | 169 | 704 | 6,092 |
| `LLM_prompt_lv2.txt` | 170 | 800 | 7,321 |
| `llm_prompt_lv3.txt` | 385 | 1,769 | 14,449 |

## Validator CPU 비용

대표적인 숫자·단위·발음 후보·protected URL이 섞인 normalized text를 stage 5에서 2,000회 검증했다. 로컬 arm64 Python 3.13에서 평균 0.177 ms, p95 0.191 ms였다. 단일 최대 12.248 ms는 런타임 잡음이 포함된 관측값이다. LLM provider latency와 비교하면 일반 요청의 validator CPU 비용은 작다.

## 결론

- 5단계는 한 번의 통합 LLM pass와 deterministic fallback으로 충분했다. 이 표본에서는 항상 2-pass가 필요하다는 근거가 없다.
- 5단계는 4단계보다 prompt token이 약 1.9배이므로 시험 옵션을 유지한다.
- 문단 병렬화는 2문단 표본에서 upstream 호출을 2개로 늘리지만 wall time을 직렬 합계로 만들지 않았다. 각 문단에 전체 prompt가 반복되므로 prompt token 비용은 문단 수에 비례한다. 패키지 prompt 파일 본문은 프로세스에서 단계별 1회 읽고 캐시하지만, vLLM 요청의 전체 instruction 반복은 그대로다.
- 다음 승인 전에는 표본을 확대하고 실제 TTS 음성 청취 평가와 반복 안정성 평가를 추가해야 한다.

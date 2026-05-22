# Diff 표시 방식 설계 문서

## 1. Diff Item Type 정의

| Type | 설명 |
|------|------|
| unchanged | 변경 없음 → 일반 텍스트 출력 |
| deleted | 삭제됨 |
| inserted | 추가됨 |
| inserted_comma | `,` 또는 `，`만 단독 삽입된 경우 |
| paragraph_tag | 입력에 없던 줄바꿈 묶음의 첫 `\n`에만 붙는 자동 문단 구분 태그 |
| inserted_newline | 출력에는 반영되지만 태그는 붙지 않는 삽입 개행 |
| whitespace_changed | 삭제된 공백 인접에 공백이 삽입된 경우만 해당 |

---

## 2. 스타일 규칙

| Type | CSS 클래스 | 스타일 |
|------|------------|--------|
| deleted | `.diff-del` | #ffe0e0 배경 · #cc0000 텍스트 · 취소선 · bold 없음 |
| inserted | `.diff-add` | #e6ffed 배경 · #1a7f37 텍스트 · bold |
| inserted_comma | `.diff-add-comma` | #e6ffed 배경 · #1a7f37 텍스트 · bold · 점선 테두리 |
| paragraph_tag | `.diff-paragraph` | #f0f0f0 배경 · #666 텍스트 · border-radius:999px 캡슐 |
| inserted_newline | (없음) | 실제 줄바꿈만 출력 |
| whitespace_changed | `.diff-add` 재사용 | 공백을 `␣` 심볼로 치환해 표시 |
| unchanged | (없음) | 일반 텍스트 그대로 |

---

## 3. 공백 시각화 방식

- `deleted` 스팬 내부 공백만 `␣` 심볼로 치환 (`.diff-space-sym`)
- `whitespace_changed`: 인접 삭제 공백이 있을 때만 발동 → `␣` 시각화 적용
- `unchanged` 및 `inserted` 내 일반 공백: 그대로 출력 (불필요한 강조 없음)

---

## 4. Diff 처리 로직

1. `tokenize()` — 정규식 기반으로 입력 문자열을 토큰 배열로 분리  
   - 토큰 종류: 줄바꿈, 공백(연속 공백), 숫자 블록, 영문 블록, 한글 블록, 단위/통화 기호, 기타 단일 문자
   - 숫자·한글·영문·기호가 섞인 토큰은 경계별로 분해
   - 예: `12권과 → ["12", "권과"]`, `2025년 → ["2025", "년"]`, `WHO와 → ["WHO", "와"]`
2. `buildTokenLCS()` — 토큰 배열에 대해 LCS DP 테이블 구축 (`Uint32Array` 기반)
3. `traceTokenOps()` — LCS backtrack → 토큰별 `eq / ins / del` op 배열 생성
4. `classifyTokenOp()` — op → DiffType 분류 (`unchanged / deleted / inserted / inserted_comma / _ins_newline / _ins_space`)
5. `refineWhitespace()` — `_ins_space` 중 인접 삭제 공백이 있는 경우만 `whitespace_changed` 로 승격; 나머지는 `unchanged` 처리
6. `refineNewlines()` — 연속 `_ins_newline` 묶음을 검사해, 입력 줄바꿈에 인접한 묶음은 모두 `inserted_newline`, 입력에 없던 새 묶음은 첫 개행만 `paragraph_tag` 로 변환

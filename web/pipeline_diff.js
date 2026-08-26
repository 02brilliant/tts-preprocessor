(function exposePipelineDiff(globalScope) {
  "use strict";

  const MAX_LCS_CELLS = 4_000_000;
  const MAX_MYERS_EDIT_DISTANCE = 4_000;
  const MAX_MYERS_TRACE_CELLS = 12_000_000;
  const SPACE_SYMBOL = "\u2423";
  const SPEECH_STRUCTURE_CHARACTER_RE =
    /^[\s,，.。!?！？:：;；()（）[\]{}"'“”‘’…—–]$/u;
  const UNPROCESSED_ALPHANUMERIC_RE = /^[0-9A-Za-z]$/;

  function escapeHtml(text) {
    return text
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function sequenceOps(source, target) {
    const a = Array.from(source);
    const b = Array.from(target);
    const m = a.length;
    const n = b.length;

    if ((m + 1) * (n + 1) > MAX_LCS_CELLS) {
      return largeSequenceOps(a, b);
    }

    const dp = new Uint32Array((m + 1) * (n + 1));
    for (let i = 1; i <= m; i += 1) {
      for (let j = 1; j <= n; j += 1) {
        const cell = i * (n + 1) + j;
        if (a[i - 1] === b[j - 1]) {
          dp[cell] = dp[(i - 1) * (n + 1) + (j - 1)] + 1;
        } else {
          dp[cell] = Math.max(
            dp[(i - 1) * (n + 1) + j],
            dp[i * (n + 1) + (j - 1)],
          );
        }
      }
    }

    const ops = [];
    let i = m;
    let j = n;
    while (i > 0 || j > 0) {
      if (i > 0 && j > 0 && a[i - 1] === b[j - 1]) {
        ops.push({
          op: "eq",
          value: a[i - 1],
          sourceIndex: i - 1,
          targetIndex: j - 1,
        });
        i -= 1;
        j -= 1;
      } else if (
        j > 0
        && (
          i === 0
          || dp[i * (n + 1) + j] === dp[i * (n + 1) + (j - 1)]
        )
      ) {
        ops.push({
          op: "ins",
          value: b[j - 1],
          targetIndex: j - 1,
        });
        j -= 1;
      } else {
        ops.push({
          op: "del",
          value: a[i - 1],
          sourceIndex: i - 1,
        });
        i -= 1;
      }
    }
    return ops.reverse();
  }

  function largeSequenceOps(a, b) {
    let prefix = 0;
    while (prefix < a.length && prefix < b.length && a[prefix] === b[prefix]) {
      prefix += 1;
    }

    let suffix = 0;
    while (
      suffix < a.length - prefix
      && suffix < b.length - prefix
      && a[a.length - 1 - suffix] === b[b.length - 1 - suffix]
    ) {
      suffix += 1;
    }

    const middleOps = myersOps(
      a.slice(prefix, a.length - suffix),
      b.slice(prefix, b.length - suffix),
    );
    if (middleOps === null) {
      return boundedFallbackOps(a, b);
    }

    const ops = [];
    for (let index = 0; index < prefix; index += 1) {
      ops.push({
        op: "eq",
        value: a[index],
        sourceIndex: index,
        targetIndex: index,
      });
    }
    for (const op of middleOps) {
      ops.push({
        ...op,
        ...(op.sourceIndex === undefined
          ? {}
          : { sourceIndex: op.sourceIndex + prefix }),
        ...(op.targetIndex === undefined
          ? {}
          : { targetIndex: op.targetIndex + prefix }),
      });
    }
    for (let offset = suffix; offset > 0; offset -= 1) {
      const sourceIndex = a.length - offset;
      const targetIndex = b.length - offset;
      ops.push({
        op: "eq",
        value: a[sourceIndex],
        sourceIndex,
        targetIndex,
      });
    }
    return ops;
  }

  // Myers' O((N + M)D) algorithm keeps long documents with a few localized
  // changes precise without allocating the quadratic LCS table.
  function myersOps(a, b) {
    const maxDistance = Math.min(
      a.length + b.length,
      MAX_MYERS_EDIT_DISTANCE,
    );
    const trace = [];
    let previous = null;

    function valueAt(row, distance, diagonal) {
      const index = diagonal + distance;
      return index < 0 || index >= row.length ? -1 : row[index];
    }

    for (let distance = 0; distance <= maxDistance; distance += 1) {
      if ((distance + 1) * (distance + 1) > MAX_MYERS_TRACE_CELLS) {
        return null;
      }
      const row = new Int32Array((2 * distance) + 1);
      row.fill(-1);

      for (let diagonal = -distance; diagonal <= distance; diagonal += 2) {
        const movedDown = distance === 0
          || diagonal === -distance
          || (
            diagonal !== distance
            && valueAt(previous, distance - 1, diagonal - 1)
              < valueAt(previous, distance - 1, diagonal + 1)
          );
        const previousDiagonal = movedDown ? diagonal + 1 : diagonal - 1;
        let x = distance === 0
          ? 0
          : valueAt(previous, distance - 1, previousDiagonal) + (movedDown ? 0 : 1);
        let y = x - diagonal;
        while (x < a.length && y < b.length && a[x] === b[y]) {
          x += 1;
          y += 1;
        }
        row[diagonal + distance] = x;

        if (x === a.length && y === b.length) {
          trace.push(row);
          return backtrackMyersOps(a, b, trace);
        }
      }
      trace.push(row);
      previous = row;
    }
    return null;
  }

  function backtrackMyersOps(a, b, trace) {
    const ops = [];
    let x = a.length;
    let y = b.length;

    function valueAt(row, distance, diagonal) {
      const index = diagonal + distance;
      return index < 0 || index >= row.length ? -1 : row[index];
    }

    for (let distance = trace.length - 1; distance > 0; distance -= 1) {
      const previous = trace[distance - 1];
      const diagonal = x - y;
      const movedDown = diagonal === -distance
        || (
          diagonal !== distance
          && valueAt(previous, distance - 1, diagonal - 1)
            < valueAt(previous, distance - 1, diagonal + 1)
        );
      const previousDiagonal = movedDown ? diagonal + 1 : diagonal - 1;
      const previousX = valueAt(previous, distance - 1, previousDiagonal);
      const previousY = previousX - previousDiagonal;

      while (x > previousX && y > previousY) {
        ops.push({
          op: "eq",
          value: a[x - 1],
          sourceIndex: x - 1,
          targetIndex: y - 1,
        });
        x -= 1;
        y -= 1;
      }
      if (movedDown) {
        ops.push({ op: "ins", value: b[previousY], targetIndex: previousY });
        y = previousY;
      } else {
        ops.push({ op: "del", value: a[previousX], sourceIndex: previousX });
        x = previousX;
      }
    }

    while (x > 0 && y > 0) {
      ops.push({
        op: "eq",
        value: a[x - 1],
        sourceIndex: x - 1,
        targetIndex: y - 1,
      });
      x -= 1;
      y -= 1;
    }
    while (x > 0) {
      ops.push({ op: "del", value: a[x - 1], sourceIndex: x - 1 });
      x -= 1;
    }
    while (y > 0) {
      ops.push({ op: "ins", value: b[y - 1], targetIndex: y - 1 });
      y -= 1;
    }
    return ops.reverse();
  }

  function boundedFallbackOps(a, b) {
    let prefix = 0;
    while (
      prefix < a.length
      && prefix < b.length
      && a[prefix] === b[prefix]
    ) {
      prefix += 1;
    }

    let suffix = 0;
    while (
      suffix < a.length - prefix
      && suffix < b.length - prefix
      && a[a.length - 1 - suffix] === b[b.length - 1 - suffix]
    ) {
      suffix += 1;
    }

    const ops = [];
    for (let index = 0; index < prefix; index += 1) {
      ops.push({
        op: "eq",
        value: a[index],
        sourceIndex: index,
        targetIndex: index,
      });
    }
    for (let index = prefix; index < a.length - suffix; index += 1) {
      ops.push({ op: "del", value: a[index], sourceIndex: index });
    }
    for (let index = prefix; index < b.length - suffix; index += 1) {
      ops.push({ op: "ins", value: b[index], targetIndex: index });
    }
    for (let offset = suffix; offset > 0; offset -= 1) {
      const sourceIndex = a.length - offset;
      const targetIndex = b.length - offset;
      ops.push({
        op: "eq",
        value: a[sourceIndex],
        sourceIndex,
        targetIndex,
      });
    }
    return ops;
  }

  function initialLedger(originalText) {
    return Array.from(originalText, (value, sourceIndex) => ({
      value,
      stage: 0,
      sourceIndex,
    }));
  }

  function transitionLedger(previousLedger, targetText, stage) {
    const previousText = previousLedger.map((entry) => entry.value).join("");
    const ops = sequenceOps(previousText, targetText);
    const nextLedger = [];

    for (const op of ops) {
      if (op.op === "eq") {
        nextLedger.push(previousLedger[op.sourceIndex]);
      } else if (op.op === "ins") {
        nextLedger.push({
          value: op.value,
          stage,
          sourceIndex: null,
        });
      }
    }
    return nextLedger;
  }

  function buildPipelineLedgers(originalText, normalizedText, speechText) {
    const original = initialLedger(originalText);
    const stage1 = transitionLedger(original, normalizedText, 1);
    const stage2 = transitionLedger(stage1, speechText, 2);
    return { original, stage1, stage2 };
  }

  function appendPart(parts, part) {
    const previous = parts[parts.length - 1];
    const mergeable = !["inserted_comma", "paragraph_tag", "inserted_newline"]
      .includes(part.type);
    if (
      previous
      && mergeable
      && previous.type === part.type
      && previous.stage === part.stage
    ) {
      previous.value += part.value;
      return;
    }
    parts.push(part);
  }

  function insertedPart(value, stage) {
    if (value === "\n") {
      return {
        value,
        type: stage === 1 ? "paragraph_tag" : "inserted_newline",
        stage,
      };
    }
    if (value === "," || value === "，") {
      return { value, type: "inserted_comma", stage };
    }
    if (/^[^\S\n]$/u.test(value)) {
      return { value, type: "whitespace_changed", stage };
    }
    return { value, type: "inserted", stage };
  }

  function adjacentParts(sourceText, targetText, stage) {
    const parts = [];
    for (const op of sequenceOps(sourceText, targetText)) {
      if (op.op === "eq") {
        appendPart(parts, { value: op.value, type: "unchanged", stage: 0 });
      } else if (op.op === "del") {
        appendPart(parts, { value: op.value, type: "deleted", stage: 0 });
      } else {
        appendPart(parts, insertedPart(op.value, stage));
      }
    }
    return parts;
  }

  function stage1InputParts(originalText, normalizedText) {
    const parts = [];
    for (const op of sequenceOps(originalText, normalizedText)) {
      if (op.op === "eq") {
        appendPart(parts, {
          value: op.value,
          type: UNPROCESSED_ALPHANUMERIC_RE.test(op.value)
            ? "unprocessed_alphanumeric"
            : "unchanged",
          stage: 0,
        });
      } else if (op.op === "del") {
        appendPart(parts, {
          value: op.value,
          type: "stage1_modified",
          stage: 1,
        });
      }
    }
    return parts;
  }

  function speechContractParts(sourceText, targetText, includeDeletions) {
    const parts = [];
    for (const op of sequenceOps(sourceText, targetText)) {
      if (op.op === "eq") {
        appendPart(parts, { value: op.value, type: "unchanged", stage: 0 });
      } else if (op.op === "del") {
        if (includeDeletions) {
          appendPart(parts, {
            value: op.value,
            type: "contract_violation_deleted",
            stage: 0,
          });
        }
      } else {
        appendPart(parts, {
          value: op.value,
          type: "contract_violation",
          stage: 2,
        });
      }
    }
    return parts;
  }

  function cumulativeParts(originalText, finalLedger) {
    const sourceCharacters = Array.from(originalText);
    const parts = [];
    let sourceIndex = 0;

    for (const entry of finalLedger) {
      if (entry.sourceIndex === null) {
        appendPart(parts, insertedPart(entry.value, entry.stage));
        continue;
      }

      while (sourceIndex < entry.sourceIndex) {
        appendPart(parts, {
          value: sourceCharacters[sourceIndex],
          type: "deleted",
          stage: 0,
        });
        sourceIndex += 1;
      }

      if (sourceIndex === entry.sourceIndex) {
        appendPart(parts, {
          value: entry.value,
          type: "unchanged",
          stage: 0,
        });
        sourceIndex += 1;
      }
    }

    while (sourceIndex < sourceCharacters.length) {
      appendPart(parts, {
        value: sourceCharacters[sourceIndex],
        type: "deleted",
        stage: 0,
      });
      sourceIndex += 1;
    }
    return parts;
  }

  function visualizeSpaces(text) {
    return text.replaceAll(
      " ",
      `<span class="diff-space-symbol">${SPACE_SYMBOL}</span>`,
    );
  }

  function visualizeViolationWhitespace(text) {
    return visualizeSpaces(text)
      .replaceAll("\t", "⇥")
      .replaceAll("\r", "␍")
      .replaceAll("\n", "↵\n");
  }

  function renderParts(parts) {
    return parts.map((part) => {
      const safeValue = escapeHtml(part.value);
      if (part.type === "unchanged") {
        return safeValue;
      }
      if (part.type === "deleted") {
        return `<span class="diff-del">${visualizeSpaces(safeValue)}</span>`;
      }
      if (part.type === "contract_violation_deleted") {
        return (
          '<span class="diff-del diff-contract-violation-deleted" '
          + 'title="LLM 계약을 위반해 삭제된 입력 구조">'
          + `${visualizeViolationWhitespace(safeValue)}</span>`
        );
      }
      if (part.type === "contract_violation") {
        return (
          '<span class="diff-contract-violation" '
          + 'title="LLM 단계 계약 위반 변경">'
          + `${visualizeViolationWhitespace(safeValue)}</span>`
        );
      }
      if (part.type === "stage1_modified") {
        return (
          '<span class="diff-stage-1-input-modified" '
          + 'title="1단계 규칙 기반 발음교정 처리">'
          + `${visualizeSpaces(safeValue)}</span>`
        );
      }
      if (part.type === "unprocessed_alphanumeric") {
        return (
          '<span class="diff-contract-violation" '
          + 'title="1단계에서 처리되지 않은 숫자·알파벳">'
          + `${visualizeSpaces(safeValue)}</span>`
        );
      }
      if (part.type === "paragraph_tag") {
        return (
          `<span class="diff-paragraph diff-stage-${part.stage}">`
          + "&lt;문단 자동 구분&gt;</span>\n"
        );
      }
      if (part.type === "inserted_newline") {
        return "\n";
      }

      const stageClass = `diff-stage-${part.stage}`;
      if (part.type === "whitespace_changed") {
        return `<span class="${stageClass}">${visualizeSpaces(safeValue)}</span>`;
      }
      if (part.type === "inserted_comma") {
        return `<span class="${stageClass} diff-comma">${safeValue}</span>`;
      }
      return `<span class="${stageClass}">${safeValue}</span>`;
    }).join("");
  }

  function renderAdjacentDiff(sourceText, targetText, stage, targetElement) {
    targetElement.innerHTML = renderParts(
      adjacentParts(sourceText, targetText, stage),
    );
  }

  function renderOutputWithStageChanges(
    sourceText,
    targetText,
    stage,
    targetElement,
  ) {
    const outputParts = adjacentParts(sourceText, targetText, stage)
      .filter((part) => part.type !== "deleted");
    targetElement.innerHTML = renderParts(outputParts);
  }

  function renderCumulativeDiff(originalText, ledger, targetElement) {
    targetElement.innerHTML = renderParts(
      cumulativeParts(originalText, ledger),
    );
  }

  function renderStage1Input(originalText, normalizedText, targetElement) {
    targetElement.innerHTML = renderParts(
      stage1InputParts(originalText, normalizedText),
    );
  }

  function renderSpeechContractViolation(
    sourceText,
    outputText,
    outputElement,
    diffElement,
  ) {
    outputElement.innerHTML = renderParts(
      speechContractParts(sourceText, outputText, false),
    );
    diffElement.innerHTML = renderParts(
      speechContractParts(sourceText, outputText, true),
    );
  }

  const api = {
    adjacentParts,
    buildPipelineLedgers,
    cumulativeParts,
    escapeHtml,
    renderAdjacentDiff,
    renderCumulativeDiff,
    renderOutputWithStageChanges,
    renderParts,
    renderSpeechContractViolation,
    renderStage1Input,
    stage1InputParts,
    sequenceOps,
    speechContractParts,
  };

  globalScope.PipelineDiff = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
}(typeof globalThis !== "undefined" ? globalThis : window));

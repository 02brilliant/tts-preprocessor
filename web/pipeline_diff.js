(function exposePipelineDiff(globalScope) {
  "use strict";

  const MAX_LCS_CELLS = 4_000_000;
  const SPACE_SYMBOL = "\u2423";

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
      return boundedFallbackOps(a, b);
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

  function buildPipelineLedgers(originalText, normalizedText, prosodyText, speechText) {
    const original = initialLedger(originalText);
    const stage1 = transitionLedger(original, normalizedText, 1);
    const stage2 = transitionLedger(stage1, prosodyText, 2);
    const stage3 = transitionLedger(stage2, speechText, 3);
    return { original, stage1, stage2, stage3 };
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

  function renderParts(parts) {
    return parts.map((part) => {
      const safeValue = escapeHtml(part.value);
      if (part.type === "unchanged") {
        return safeValue;
      }
      if (part.type === "deleted") {
        return `<span class="diff-del">${visualizeSpaces(safeValue)}</span>`;
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

  function renderCumulativeDiff(originalText, ledger, targetElement) {
    targetElement.innerHTML = renderParts(
      cumulativeParts(originalText, ledger),
    );
  }

  const api = {
    adjacentParts,
    buildPipelineLedgers,
    cumulativeParts,
    escapeHtml,
    renderAdjacentDiff,
    renderCumulativeDiff,
    renderParts,
    sequenceOps,
  };

  globalScope.PipelineDiff = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
}(typeof globalThis !== "undefined" ? globalThis : window));

"use strict";

const assert = require("node:assert/strict");
const { sequenceOps, speechContractParts } = require("./pipeline_diff.js");

function renderTarget(ops) {
  return ops
    .filter((op) => op.op !== "del")
    .map((op) => op.value)
    .join("");
}

function testLongTextWithLocalizedChangesKeepsContext() {
  const source = Array.from(
    { length: 320 },
    (_, index) => `문단 ${index + 1}: 미국 국채금리와 반도체주 흐름을 점검한다.\n`,
  ).join("");
  const target = source
    .replaceAll("국채금리", "국채 금리")
    .replaceAll("반도체주", "반도체 주");
  const ops = sequenceOps(source, target);

  assert.equal(renderTarget(ops), target);
  assert.ok(
    ops.filter((op) => op.op === "eq").length > source.length * 0.8,
    "localized edits in a long document must preserve surrounding unchanged text",
  );
}

testLongTextWithLocalizedChangesKeepsContext();

function testRejectedSpeechMarksEveryChangedOutputSpan() {
  const parts = speechContractParts("삼쩜일사", "삼점일사", true);
  assert.equal(parts.filter((part) => part.type === "contract_violation").map((part) => part.value).join(""), "점");
  assert.equal(parts.filter((part) => part.type === "contract_violation_deleted").map((part) => part.value).join(""), "쩜");
}

testRejectedSpeechMarksEveryChangedOutputSpan();

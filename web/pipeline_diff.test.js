"use strict";

const assert = require("node:assert/strict");
const { sequenceOps } = require("./pipeline_diff.js");

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

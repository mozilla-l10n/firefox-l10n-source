import assert from "node:assert";
import { readFileSync } from "node:fs";
import { parse } from "yaml";

const actionPath = ".github/workflows/update.yml";

const { jobs } = parse(readFileSync(actionPath, "utf8"));

const updateBranches = jobs.update?.strategy?.matrix?.ref;
assert(
  Array.isArray(updateBranches),
  new Error('Expected to find a matrix for the "update" job')
);

const pruneCommand = jobs.cleanup?.steps?.find(
  (step) => step.id === "prune"
)?.run;
const pruneMatch = pruneCommand?.match(/\bprune(?:\.py)?\s+(.*)/);
assert(
  pruneMatch,
  new Error(`Expected a valid "prune" command: ${pruneCommand}`)
);
const pruneBranches = pruneMatch[1].trim().split(/\s+/);

assert.deepStrictEqual(
  pruneBranches,
  updateBranches,
  Object.assign(
    new Error("Expected branch lists of update and prune jobs to match"),
    { update: updateBranches, prune: pruneBranches }
  )
);

console.log("✅");

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");
const vm = require("node:vm");

const file = path.resolve(__dirname, "../src/components/design/PowerSpectrumControls.tsx");
const source = ts.createSourceFile("PowerSpectrumControls.tsx", fs.readFileSync(file, "utf8"), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const method = source.statements.find((statement) => ts.isFunctionDeclaration(statement) && statement.name?.text === "powerAxisDomain");
assert.ok(method, "powerAxisDomain must be exported");
const javascript = ts.transpileModule(`${method.getText(source)}\nexports.axis = powerAxisDomain;`, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
}).outputText;
const context = { exports: {} };
vm.runInNewContext(javascript, context);
const domain = context.exports.axis;

for (const values of [[0.0125, 0.0219], [0.0002, 0.0088], [0.963, 0.9993], [0, 0], [0.01, 0.96]]) {
  const [lower, upper] = domain(values);
  assert.ok(lower >= 0 && upper <= 1 && lower < upper);
  assert.ok(lower <= Math.min(...values) && upper >= Math.max(...values));
}
assert.ok(domain([0.0125, 0.0219])[1] < 0.05, "AR reflectance should not use the 0–100% axis");
assert.ok(domain([0.963, 0.9993])[0] > 0.9, "small variations near 100% should remain visible");
console.log("Power chart domains passed: low R, near-one T, zero A and wide-band energy.");

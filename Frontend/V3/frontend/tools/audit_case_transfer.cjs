// Execute the actual frontend transfer functions without mounting the UI.
const fs = require('node:fs');
const ts = require('typescript');
const vm = require('node:vm');
const path = require('node:path');
const source = ts.createSourceFile('App.tsx', fs.readFileSync(path.join(__dirname, '../src/App.tsx'), 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const names = new Set(['materialOptionsForRole', 'closestMaterialForValue', 'numericParam', 'layerMaterialFromRow', 'buildDraftFromCase']);
const code = source.statements.filter(n => ts.isFunctionDeclaration(n) && names.has(n.name?.text)).map(n => n.getText(source)).join('\n');
const context = {};
vm.createContext(context);
vm.runInContext(ts.transpileModule(code, {compilerOptions: {target: ts.ScriptTarget.ES2022}}).outputText, context);
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const selections = Object.fromEntries(Object.entries(input.case.default_params).filter(([k]) => k.startsWith('n_')).map(([k,v]) => [k, context.closestMaterialForValue(k,v,input.materials)]));
const series = [{x: input.result.series.wavelength_nm}];
process.stdout.write(JSON.stringify(context.buildDraftFromCase(input.case, input.materials, input.result.layers, selections, series)));

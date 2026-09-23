import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const WEB3D_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const APPS_ROOT = resolve(WEB3D_ROOT, "apps");

function entryRecords() {
  return readdirSync(APPS_ROOT)
    .map((slug) => ({ slug, htmlPath: resolve(APPS_ROOT, slug, "index.html") }))
    .filter(({ htmlPath }) => statSync(htmlPath).isFile())
    .map(({ slug, htmlPath }) => {
      const html = readFileSync(htmlPath, "utf8");
      const source = html.match(/<script[^>]+type="module"[^>]+src="([^"]+)"/)?.[1];
      return { slug, html, source, resolvedSource: source ? resolve(dirname(htmlPath), source) : null };
    });
}

describe("case-specific Three.js entrypoints", () => {
  it("gives every physical case its own module entry", () => {
    const records = entryRecords();
    expect(records).toHaveLength(40);
    expect(records.every(({ source }) => Boolean(source))).toBe(true);
    expect(new Set(records.map(({ resolvedSource }) => resolvedSource)).size).toBe(40);
  });

  it("does not route cases through generic or evidence selectors", () => {
    for (const record of entryRecords()) {
      expect(record.source).not.toMatch(/apps\/(generic|evidence)\/main\.js/);
      expect(record.html).not.toMatch(/data-case-id=/);
      const sourceCode = readFileSync(record.resolvedSource, "utf8");
      expect(sourceCode).not.toMatch(/dataset\.caseId/);
    }
  });
});


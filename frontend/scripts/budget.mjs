// Performance budgets (docs/frontend.md → Performance budgets). Run after `npm run build`.
// Fails (exit 1) if the 3D bundle grows past its budget — CI job 3. (The hero controller
// is built in code, so there is no model file to budget.)
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { join, resolve } from "node:path";

const root = resolve(import.meta.dirname, "../..");
const KB = 1024;
const budgets = [
  { name: "3D bundle JS (gzip)", limit: 250 * KB, measure: () => jsGzip(join(root, "static/dist/assets")) },
];

function jsGzip(dir) {
  if (!existsSync(dir)) throw new Error(`${dir} missing — run npm run build first`);
  return readdirSync(dir)
    .filter((f) => f.endsWith(".js"))
    .reduce((sum, f) => sum + gzipSync(readFileSync(join(dir, f))).length, 0);
}

let failed = false;
for (const b of budgets) {
  const size = b.measure();
  const ok = size <= b.limit;
  failed ||= !ok;
  console.log(`${ok ? "OK  " : "FAIL"} ${b.name}: ${(size / KB).toFixed(1)} KB / ${(b.limit / KB).toFixed(0)} KB`);
}
process.exit(failed ? 1 : 0);

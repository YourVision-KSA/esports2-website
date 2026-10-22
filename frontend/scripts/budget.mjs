// Performance budgets (docs/frontend.md → Performance budgets). Run after `npm run build`.
// Fails (exit 1) if the 3D bundle or hero model grows past its budget — CI job 3.
import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { join, resolve } from "node:path";

const root = resolve(import.meta.dirname, "../..");
const KB = 1024;
const budgets = [
  { name: "3D bundle JS (gzip)", limit: 250 * KB, measure: () => jsGzip(join(root, "static/dist/assets")) },
  { name: "hero model (glb)", limit: 1.5 * 1024 * KB, measure: () => fileSize(join(root, "static/models/controller.glb")) },
];

function jsGzip(dir) {
  if (!existsSync(dir)) throw new Error(`${dir} missing — run npm run build first`);
  return readdirSync(dir)
    .filter((f) => f.endsWith(".js"))
    .reduce((sum, f) => sum + gzipSync(readFileSync(join(dir, f))).length, 0);
}
function fileSize(path) {
  return existsSync(path) ? statSync(path).size : 0; // model optional until shipped
}

let failed = false;
for (const b of budgets) {
  const size = b.measure();
  const ok = size <= b.limit;
  failed ||= !ok;
  console.log(`${ok ? "OK  " : "FAIL"} ${b.name}: ${(size / KB).toFixed(1)} KB / ${(b.limit / KB).toFixed(0)} KB`);
}
process.exit(failed ? 1 : 0);

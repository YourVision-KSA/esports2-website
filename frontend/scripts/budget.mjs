// Performance budgets (docs/frontend.md → Performance budgets). Run after `npm run build`.
// Fails (exit 1) if a bundle or the hero model grows past its budget — CI job "frontend".
// JS is measured per Vite entry (the entry + everything it imports, statically or lazily),
// gzip-compressed; Web Worker chunks are counted with the entry that spawns them.
import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { join, resolve } from "node:path";

const root = resolve(import.meta.dirname, "../..");
const dist = join(root, "static/dist");
const KB = 1024;
const manifestPath = join(dist, ".vite/manifest.json");
if (!existsSync(manifestPath)) {
  console.error("static/dist/.vite/manifest.json missing — run npm run build first");
  process.exit(1);
}
const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
const gz = (file) => gzipSync(readFileSync(join(dist, file))).length;

function closure(key, seen = new Set()) {
  const chunk = manifest[key];
  if (!chunk || seen.has(chunk.file)) return seen;
  seen.add(chunk.file);
  for (const k of [...(chunk.imports || []), ...(chunk.dynamicImports || [])]) closure(k, seen);
  return seen;
}
const entryKey = (name) => Object.keys(manifest).find((k) => manifest[k].isEntry && manifest[k].name === name);
const workers = readdirSync(join(dist, "assets")).filter((f) => /worker/i.test(f) && f.endsWith(".js"));
const sum = (files) => [...files].reduce((n, f) => n + gz(f), 0);

const budgets = [
  { name: "hero 3D bundle JS (gzip)", limit: 250 * KB, size: sum(closure(entryKey("hero"))) },
  {
    name: "check-in scanner JS incl. worker (gzip)",
    limit: 60 * KB,
    size: sum(closure(entryKey("scanner"))) + workers.reduce((n, f) => n + gz("assets/" + f), 0),
  },
  {
    name: "hero model (glb)",
    limit: 1.5 * 1024 * KB,
    size: existsSync(join(root, "static/models/controller.glb"))
      ? statSync(join(root, "static/models/controller.glb")).size
      : 0,
  },
];

let failed = false;
for (const b of budgets) {
  const ok = b.size <= b.limit;
  failed ||= !ok;
  console.log(`${ok ? "OK  " : "FAIL"} ${b.name}: ${(b.size / KB).toFixed(1)} KB / ${(b.limit / KB).toFixed(0)} KB`);
}
process.exit(failed ? 1 : 0);

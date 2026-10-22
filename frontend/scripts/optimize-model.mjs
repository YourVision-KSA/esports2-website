// Raw model → web-ready hero model (docs/frontend.md → 3D scenes + budgets).
//   npm run model -- <input.glb|.gltf> [simplifyRatio=0.35]
// Steps (gltf-transform "optimize"): dedup + prune + weld, mesh simplification
// (meshoptimizer), textures resized to ≤1024 px and re-encoded as WebP, geometry
// compressed with EXT_meshopt_compression. Output: static/models/controller.glb.
// WebP rather than KTX2: for a single small model, the KTX2/Basis transcoder
// (~250 KB) would cost more than it saves — see docs/frontend.md.
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

const [input, ratio = "0.35"] = process.argv.slice(2);
if (!input) {
  console.error("usage: npm run model -- <input.glb|.gltf> [simplifyRatio]");
  process.exit(2);
}
const out = resolve(import.meta.dirname, "../../static/models/controller.glb");
const cli = (args) => execFileSync("npx", ["gltf-transform", ...args], { stdio: "inherit" });

cli([
  "optimize", resolve(input), out,
  "--compress", "meshopt",
  "--texture-compress", "webp",
  "--texture-size", "1024",
  "--simplify", "true",
  "--simplify-ratio", ratio,
  "--simplify-error", "0.0008",
]);
cli(["inspect", out, "--format", "pretty"]);
console.log(`\nwritten ${out} — now run: npm run budget`);

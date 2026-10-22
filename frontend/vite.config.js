// Builds the 3D bundle into Django's static tree (docs/frontend.md → Build).
// Django reads static/dist/.vite/manifest.json via the {% vite_asset %} tag.
import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  root: resolve(import.meta.dirname, "src"),
  base: "/static/dist/",
  publicDir: false,
  build: {
    outDir: resolve(import.meta.dirname, "../static/dist"),
    emptyOutDir: true,
    manifest: true,
    target: "es2020",
    // three.js is one ~650 KB (166 KB gzip) lazy chunk by design; the real limit is
    // enforced on the gzip size by scripts/budget.mjs (250 KB, docs/frontend.md).
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      // hero.js is the tiny loader; three.js only arrives via its dynamic import.
      input: {
        hero: resolve(import.meta.dirname, "src/hero.js"),
        // door-staff QR scanner (/staff/checkin/); jsQR runs in a worker, loaded only
        // on browsers without a native BarcodeDetector (e.g. iOS Safari)
        scanner: resolve(import.meta.dirname, "src/scanner.js"),
      },
    },
  },
});

import { defineConfig } from "vite";

// Builds the 3D bundle into Django's static tree (docs/frontend.md → Build).
// `npm run build` writes hashed files + .vite/manifest.json to ../static/dist/
// (gitignored; the Dockerfile has a Node stage that builds it for production).
// The {% vite_js %} tag (core/templatetags/vite.py) reads the manifest to emit
// the script tag, and renders nothing when the bundle isn't built.
export default defineConfig({
  base: "/static/dist/",
  build: {
    outDir: "../static/dist",
    emptyOutDir: true,
    manifest: true,
    rollupOptions: { input: "src/main.js" },
  },
});

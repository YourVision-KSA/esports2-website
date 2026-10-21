// Quality tiers (docs/frontend.md → Quality tiers). Decided before the scene
// loads; the scene runs a 3 s FPS probe once and may move one tier, then
// persists the result so revisits skip the probe.

const KEY = "gl-tier";

export function decideTier() {
  // Reduced motion: never start the render loop, show the poster.
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return "LOW";

  let gl = null;
  try {
    gl = document.createElement("canvas").getContext("webgl2");
  } catch {
    /* context creation threw: treat as no WebGL2 */
  }
  if (!gl) return "FALLBACK";

  if (navigator.deviceMemory && navigator.deviceMemory <= 2) return "LOW";

  let saved = null;
  try {
    saved = localStorage.getItem(KEY);
  } catch {
    /* storage blocked: fall through to the default */
  }
  if (saved === "HIGH" || saved === "MID" || saved === "LOW") return saved;

  // Start MID on mobile, HIGH on desktop; the probe settles it.
  return window.matchMedia("(pointer: coarse)").matches ? "MID" : "HIGH";
}

export function persistTier(tier) {
  try {
    localStorage.setItem(KEY, tier);
  } catch {
    /* fine — the probe just runs again next visit */
  }
}

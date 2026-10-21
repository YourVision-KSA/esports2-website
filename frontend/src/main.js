// Entry for the 3D scenes (docs/frontend.md → 3D scenes).
// The page renders fully before this loads; everything here is enhancement
// over the posters already in the HTML. LOW and FALLBACK tiers do nothing —
// the framed poster IS those tiers.
import { decideTier } from "./tiers.js";

const mount = document.querySelector("#hero-scene .scene-frame");
if (mount) {
  const tier = decideTier();
  if (tier === "HIGH" || tier === "MID") {
    import("./hero.js").then(
      (m) => m.mountHero(mount, tier),
      () => {}, // chunk failed to load: poster stays (FALLBACK behavior)
    );
  }
}

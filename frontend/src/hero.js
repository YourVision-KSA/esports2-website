/* 3D loader for the home page's two scenes — hero controller + prizes trophy
   (docs/frontend.md → 3D scenes + quality tiers).

   This file is deliberately tiny and imports nothing from three.js. It decides
   WHETHER and WHEN each 3D scene loads; scene.js (with three.js) is fetched only
   after that decision, so the page's text, buttons and countdown never wait on 3D.

   Order of gates, cheapest first:
     1. no mount point / reduced motion / saved LOW tier / low-memory device → keep poster
     2. wait for the window "load" event (all first-paint resources done)
     3. wait for an idle moment (requestIdleCallback, with a timeout)
     4. wait until the scene is near the viewport (IntersectionObserver)
   then dynamic-import scene.js. Any failure leaves the poster in place. */

const TIER_KEY = "es2.tier";

function savedTier() {
  try {
    return localStorage.getItem(TIER_KEY);
  } catch {
    return null; // private mode / blocked storage: just probe again
  }
}

function startingTier() {
  const saved = savedTier();
  if (saved === "high" || saved === "mid" || saved === "low") return saved;
  if (navigator.deviceMemory && navigator.deviceMemory <= 2) return "low";
  const mobile = window.matchMedia("(pointer: coarse)").matches;
  return mobile ? "mid" : "high";
}

function afterLoad(fn) {
  if (document.readyState === "complete") fn();
  else window.addEventListener("load", fn, { once: true });
}

function whenIdle(fn) {
  if ("requestIdleCallback" in window) window.requestIdleCallback(fn, { timeout: 2000 });
  else setTimeout(fn, 300);
}

function whenNear(el, fn) {
  if (!("IntersectionObserver" in window)) return fn();
  const io = new IntersectionObserver(
    (entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        io.disconnect();
        fn();
      }
    },
    { rootMargin: "600px 0px" },
  );
  io.observe(el);
}

// Count-only beacon (core/beacon.py): how the hero ended up on this device — at most once
// per tab session, two values from fixed lists, nothing identifying. Feeds tier_report.
const BEACON_KEY = "es2.beacon";
function report(outcome) {
  try {
    if (sessionStorage.getItem(BEACON_KEY)) return;
    sessionStorage.setItem(BEACON_KEY, outcome);
  } catch {
    /* storage blocked: still send — worst case a duplicate count */
  }
  const device = window.matchMedia("(pointer: coarse)").matches ? "mobile" : "desktop";
  const body = new Blob([`o=${outcome}&d=${device}`], { type: "application/x-www-form-urlencoded" });
  if (!(navigator.sendBeacon && navigator.sendBeacon("/beacon/3d", body))) {
    fetch("/beacon/3d", { method: "POST", body, keepalive: true }).catch(() => {});
  }
}

const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const tier = startingTier();

// Each scene gates and loads independently; the trophy sits far down the page, so its
// IntersectionObserver usually fires much later (lazy by scroll approach, rootMargin 600px).
// Only the hero reports to the beacon — its outcomes are the fixed list TierStat counts.
function arm(mountId, variant, onSettled) {
  const mount = document.getElementById(mountId);
  const modelUrl = mount && mount.dataset.model;
  if (!mount || !modelUrl || still || tier === "low") return;
  afterLoad(() =>
    whenIdle(() =>
      whenNear(mount, () => {
        import("./scene.js")
          .then((m) => m.start(mount, { tier, modelUrl, tierKey: TIER_KEY, variant, onSettled }))
          .catch(() => {
            /* FALLBACK tier: bundle, model or WebGL failed — the poster stays, page unaffected */
            onSettled("fallback");
          });
      }),
    ),
  );
}

const heroMount = document.getElementById("hero-scene");
if (heroMount && still) report("reduced");
else if (heroMount && tier === "low") report("low"); // saved from an earlier slow visit, or ≤ 2 GB RAM

arm("hero-scene", "hero", report);
arm("trophy-scene", "trophy", () => {});

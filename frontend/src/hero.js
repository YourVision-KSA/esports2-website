/* Hero 3D loader (docs/frontend.md → 3D scenes + quality tiers).

   This file is deliberately tiny and imports nothing from three.js. It decides
   WHETHER and WHEN the 3D scene loads; scene.js (with three.js) is fetched only
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

const mount = document.getElementById("hero-scene");
const modelUrl = mount && mount.dataset.model;
const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const tier = startingTier();

if (mount && still) report("reduced");
else if (mount && tier === "low") report("low"); // saved from an earlier slow visit, or ≤ 2 GB RAM

if (mount && modelUrl && !still && tier !== "low") {
  afterLoad(() =>
    whenIdle(() =>
      whenNear(mount, () => {
        import("./scene.js")
          .then((m) => m.start(mount, { tier, modelUrl, tierKey: TIER_KEY, onSettled: report }))
          .catch(() => {
            /* FALLBACK tier: bundle, model or WebGL failed — the poster stays, page unaffected */
            report("fallback");
          });
      }),
    ),
  );
}

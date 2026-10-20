# Front-end — Design Status, RTL, 3D, Performance

## Design status (updated after the prototype was demoted to content reference)

- `reference/prototype.html` is the **CONTENT reference only**: its Arabic text and event
  information (captured in docs/content-ar.md). **Do not copy its code, colors, fonts or
  layout.** Its visual design is no longer the reference.
- The visual design will come from a new **/design artifact (DEC-15, pending)**. When it
  exists, record here: the theme tokens, the font choices, the 3D scene subjects/specs, and
  the page-effect list — then remove the PENDING markers below.
- **Fixed product requirements regardless of design:** Arabic-first RTL · gaming style ·
  interactive 3D scenes · mobile-first performance (budgets below).

## Theme tokens — PENDING (DEC-15)

To be filled from the /design artifact: color palette as CSS custom properties on `:root`,
theme model (single dark / light+dark), backgrounds, accents. Until then, do not define theme
colors anywhere; base templates use structure only. Do not reuse the prototype's palette.

## Fonts — choice PENDING (DEC-15); delivery rules FIXED

The design artifact decides which fonts are used. Whatever they are:

- **Self-host trimmed `.woff2` subsets** served from `/static/` with 1-year immutable cache.
  No Google Fonts CDN or any third-party font host (performance + no visitor data leakage).
- Subset with fonttools/pyftsubset: Arabic fonts → Arabic blocks + basic Latin + digits
  (`U+0600-06FF,U+0750-077F,U+0020-007E,U+0660-0669`); Latin display/HUD fonts → only the
  glyphs actually used.
- `font-display: swap`. **Budget: all font files together ≤ 300 KB.**

## RTL rules (FIXED)

- `<html lang="ar" dir="rtl">` on every page. Use CSS logical properties
  (`margin-inline-start`, `padding-inline-end`, `inset-inline`) — never left/right directly.
- Numbers and English labels are embedded LTR runs: wrap in `<span dir="ltr">` or use
  `unicode-bidi: isolate` so strings like "1v1" and scores don't reorder.
- Arabic text comes only from docs/content-ar.md (see CLAUDE.md hard rule 1).

## Page structure (information architecture — FIXED; design may restyle/reorder within it)

One long home page: hero → stats → tournaments → zones → schedule → prizes → rules → FAQ →
sponsors → footer; nav anchors. Separate funnel routes (/vote/, /register/, /bracket/, /r/,
/invite/) reuse the theme with a compact header and **no 3D** (fast, form-first pages).

## Page effects — PENDING (DEC-15)

The effect set (glitch, scanlines, cursor light, card tilt, …) is defined by the new design.
FIXED regardless of design: all effects honor `prefers-reduced-motion: reduce` (animations
off, static states), and no effect may block interaction or run while its element is
off-screen.

## 3D scenes — subjects PENDING (DEC-15); engineering requirements FIXED

The product requires an **interactive 3D hero scene** (user-manipulable, e.g. drag-to-rotate
+ pointer parallax) and allows a second scene in a content section. Whether the subjects stay
controller/trophy or change is the design artifact's call.

Engineering requirements (apply to whatever the design specifies):

- Three.js, importing only what's used (tree-shaken); shared renderer/asset pipeline across
  scenes where possible.
- Models: **glTF (.glb) with meshopt or Draco compression**; textures **KTX2/Basis** with
  WebP/PNG fallback. Author low-poly/stylized.
- Any bloom/post-processing runs on **tier HIGH only**.
- Pause rendering when off-screen (IntersectionObserver) and on `document.visibilitychange`.
- `prefers-reduced-motion` → do not start the render loop; show the poster.
- A secondary scene is **lazy-loaded on scroll approach** (rootMargin ~600px).

## Quality tiers (FIXED; decided at runtime, re-evaluated once after 3 s)

| Tier | Trigger | Settings |
|---|---|---|
| HIGH | desktop-class GPU, or mobile passing the FPS probe ≥ 50 | post-processing on, DPR capped 2.0, full particles/effects |
| MID | default mobile start | no post-processing, DPR capped 1.5, reduced particles |
| LOW | FPS probe < 30 after 3 s, or `navigator.deviceMemory ≤ 2` | static poster image (hero render exported as WebP), effects CSS-only |
| FALLBACK | no WebGL2 / context creation fails / bundle fails to load | same poster; page fully functional |

Start at MID on mobile, HIGH on desktop; probe average FPS over 3 s and move one tier down if
< 30, up if > 50. Persist the tier in `localStorage` (try/catch) to skip the probe on revisit.
Log the final tier + fallback events to a tiny beacon endpoint (count only, no PII) — the
"WebGL fallback rate" metric in operations.md.

## Performance budgets (FIXED — mobile mid-range, 4G; CI-checked where possible)

| Item | Budget |
|---|---|
| First paint payload (HTML + CSS + fonts, no 3D) | ≤ 500 KB |
| 3D bundle JS (three + scenes, gzipped) | ≤ 250 KB |
| Hero scene assets (glb + ktx2 total) | ≤ 1.5 MB |
| Secondary scene assets | ≤ 1.0 MB (lazy) |
| Time to interactive hero on mid-range phone | ≤ 5 s on 4G |
| Steady-state FPS | ≥ 30 MID tier |

The page must render content (hero text, CTA buttons, stats) **before** the 3D bundle loads;
the canvas fades in over the poster when ready. Forms and the bracket never depend on the 3D
bundle or any JS beyond progressive enhancement (exceptions: Turnstile and the QR scanner
require JS — documented, acceptable).

## Build (FIXED)

Vite builds `frontend/` → hashed assets into Django's static pipeline (manifest consumed by a
template tag or django-vite). One bundle entry for the 3D + effects; plain CSS for the theme.
No framework (no React/Vue) — templates are server-rendered.

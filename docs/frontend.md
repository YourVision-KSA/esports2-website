# Front-end — Design Status, RTL, 3D, Performance

## Design status

- **DESIGN REFERENCE (DEC-15, delivered 2026-10-20): the "E-SPORTS 2 Website Design" artifact**
  — https://claude.ai/artifact/SNEBV9cXyS8YCmeJJfEvqG — direction **"Tournament Broadcast"**:
  professional esports look, deep navy + white ground + volt accent, gold reserved for prizes.
  7 artboards: design tokens, home desktop + mobile, vote, registration, bracket, VIP invite.
  Implement from it; propose changes there first, then here.
- `reference/prototype.html` is the **CONTENT reference only**: its Arabic text and event
  information (captured in docs/content-ar.md). **Do not copy its code, colors, fonts or
  layout.**
- **Fixed product requirements regardless of design:** Arabic-first RTL · gaming style ·
  interactive 3D scenes · mobile-first performance (budgets below).

## Theme tokens (from the design artifact — define as CSS custom properties on `:root`)

```css
--ink: #0E1433;        /* navy: dark sections, headings, card header bands */
--panel-dark: #141B45; /* panels on navy */
--line-dark: #2A3370;  /* borders on navy (hairline #232B5C) */
--volt: #D8F24A;       /* THE accent: CTAs, highlights, section slashes */
--ground: #F5F6FA;     /* page background */
--surface: #FFFFFF;    /* cards */
--surface-2: #EEF0F7;  /* alternate light sections */
--line: #DDE1EE;       /* borders on light */
--text: #171C3F;       /* body on light */
--muted: #5A6180;      /* secondary on light */
--text-dark: #E9ECFA;  /* body on navy */
--muted-dark: #A9B1D6; /* secondary on navy */
--link: #2443D6;       /* links on light */
--gold: #D9A441;       /* prizes/VIP decorative; as TEXT on light use #8A6513, on navy #E9C15C */
--error: #B3261E;
```
Theme model: **single theme** — light ground with navy "broadcast" bands (hero, schedule,
join CTA, bracket, invite). Radius 0 everywhere. Spacing scale 4/8/12/16/24/36/48/72.
Motifs: 12° skew slashes (`transform: skewX(-12deg)`) as separators and section-tag marks;
**cut-corner CTAs** (`clip-path` 10–12px) on primary buttons only; cards = white, 1px
`--line` border, navy header band + 3–4px volt rule; EN section tags in Space Grotesk
letterspaced (`01 · TOURNAMENTS`).

## Fonts (from the design artifact); delivery rules FIXED

- **Alexandria** 700/800 — display and headings (Arabic + Latin)
- **Rubik** 400/500/600/700 — body and UI (Arabic + Latin)
- **Space Grotesk** 500/700 — numbers, scores, times, EN tags (Latin only; always inside
  `dir="ltr"` isolation)

Delivery rules for them:

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

## Page effects (from the design artifact)

Deliberately restrained — no glitch/scanline/cursor effects from the prototype. Allowed set:
subtle hover lift on cards and CTAs, the volt rule sweep on card headers (optional), smooth
scroll to anchors, bracket "LIVE" badge pulse. FIXED regardless: all effects honor
`prefers-reduced-motion: reduce` (animations off, static states), and no effect may block
interaction or run while its element is off-screen.

## 3D scenes — subjects CONFIRMED by the design; engineering requirements FIXED

The design keeps both subjects, restyled to the new palette: **hero = game controller over a
lit pedestal** (navy scene, volt ring accents, drag-to-rotate + pointer parallax, in a framed
panel with the `3D INTERACTIVE SCENE` label and the hint «اسحب يد التحكم لتدويرها»), and
**prizes = gold trophy with star topper** (navy panel, gold ring, lazy-loaded). The artboards
show each scene's framed placeholder/poster composition — the poster IS the LOW/FALLBACK tier.

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

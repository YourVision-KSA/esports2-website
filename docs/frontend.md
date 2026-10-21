# Front-end — Design Status, RTL, 3D, Performance

## Design status

- **REV 4 (2026-10-21, owner-directed): "Event Logo" palette.** The owner supplied the
  official event logo (Downloads/UI; deep navy panel, cyan + magenta neon shields, gold "2"
  badge) and directed: take the site colors from the logo, drop the neon-glow styling for a
  flat professional look, and adopt the logo itself on the site. Tokens below updated;
  extracted logo assets live in `static/img/` (`logo.png`, `logo-mark.png`, `favicon.png`).
  **No colored glow shadows anywhere** — only the neutral elevation shadow token.
  The rev 3 "Arena Night" notes below remain for layout/motion/structure, which are kept.
- **DEC-02 evidence:** the logo wordmark reads «تجمع الرياضات الإلكترونية» — supports the
  rebrand answer; owner should confirm so the site name string can be switched.

- **DESIGN REFERENCE (DEC-15, rev 3 "Arena Night", 2026-10-20): the "E-SPORTS 2 Website
  Design" artifact** — https://claude.ai/artifact/SNEBV9cXyS8YCmeJJfEvqG. The owner rejected
  the earlier light "Tournament Broadcast" look; rev 3 is a **full dark, immersive esports
  design** built from competitor research (Esports World Cup, Kingdom of Gaming, BLAST,
  Gamers8): near-black ground, volt + purple glow accents, gold for prizes, atmospheric
  arena/controller/crowd/trophy photography under gradient overlays. 7 artboards: tokens,
  home desktop + mobile, vote, registration, bracket, VIP invite. Implement from it; propose
  changes there first, then here.
- **Imagery note:** the canvas uses AI-generated placeholder photos (stored as artifact
  assets, preview resolution). Production uses full-resolution, licensed or event-owned
  photography with the same treatment: dark duotone atmosphere, gradient-to-background
  overlay, purple/green light.
- **Game-card imagery rule:** each tournament card carries imagery that EVOKES its game
  without using game IP (no official art, logos or characters): rocket-car + giant ball in a
  neon arena (Rocket League), night football stadium (EA FC), tactical soldier silhouette
  (Call of Duty). When the vote confirms different games, produce equivalents in the same
  palette.
- `reference/prototype.html` is the **CONTENT reference only**: its Arabic text and event
  information (captured in docs/content-ar.md). **Do not copy its code, colors, fonts or
  layout.**
- **Fixed product requirements regardless of design:** Arabic-first RTL · gaming style ·
  interactive 3D scenes · mobile-first performance (budgets below).

## Theme tokens (from the design artifact — define as CSS custom properties on `:root`)

```css
/* REV 4 — from the official event logo. Var names kept from rev 3 so templates
   didn't churn: --volt now holds the logo CYAN, --purple the logo MAGENTA. */
--bg: #0A1322;          /* deep navy page ground (logo panel dark) */
--bg-2: #0E1A2E;        /* alternate section band */
--surface: #13223A;     /* cards, panels */
--surface-2: #1A2C49;   /* badges, inner chips */
--line: #24395B;        /* borders */
--line-strong: #32496F; /* input borders, secondary buttons */
--volt: #3EC7D6;        /* THE accent (logo cyan): CTAs, numbers, ticker */
--purple: #C9479B;      /* secondary accent (logo magenta); text-safe #E795C8 */
--text: #F2F6FC;        /* headings/body strong */
--body: #C5D1E4;        /* body text */
--muted: #92A5C0;       /* secondary */
--link: #BFD6F2;        /* links (hover: cyan) */
--gold: #CDAE4B;        /* prizes/VIP, from the logo "2" badge (deep #B29238) */
--error: #FFB4AE;
--shadow: 0 12px 28px -14px rgba(0,0,0,0.55); /* the ONLY shadow allowed */
```
Theme model: **single dark theme**. Radius 0. Spacing 4/8/12/16/24/36/48/72.
Motifs: **flat professional surfaces — NO colored glows** (no neon box/text-shadows, no
accent radial gradients; `--shadow` is the only shadow) · photo sections with
**gradient-to-bg overlays** (`linear-gradient(to bottom|top, …, var(--bg))`) · 12° skew
slashes · **cut-corner CTAs** (`clip-path` 10–12px, primary only) · cards = `--surface`,
1px `--line`, photo header + 3–4px accent rule · EN section tags in Space Grotesk
letterspaced (`01 · TOURNAMENTS`) · countdown cells with cyan bottom rule · flat page
ground (no radials) · **the event logo**: `logo-mark.png` in headers, `favicon.png` as
the tab icon, `logo.png` full lockup where needed.

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

Rev 3.1 motion spec (BLAST-inspired; all CSS/vanilla-JS, no animation library):
- **volt marquee ticker** — CSS keyframes, duplicated sequence for a seamless loop
- **hero countdown** — 1s interval; digits "--" until the date is set in SiteConfig
- **stats count-up** — numbers animate 0→value on first scroll into view (IntersectionObserver)
- **game-card hover** — lift 4px + volt border glow + image `scale(1.05)` (overflow hidden)
- **primary CTA hover** — invert to white bg / ink text
- **LIVE bar** — red dot pulse; the bar renders only during the event phase
- **section reveals** — 24px rise + fade on first entry
- **giant outline display word** ("GAME ON", `-webkit-text-stroke` volt @ ~18% alpha) and the
  vertical "REGISTER NOW" rail are static decor; **diagonal section edges** via `clip-path`
  wedges
FIXED regardless: all effects honor
`prefers-reduced-motion: reduce` (animations off, static states), and no effect may block
interaction or run while its element is off-screen.

## 3D scenes — subjects CONFIRMED by the design; engineering requirements FIXED

The design keeps both subjects in the Arena Night palette: **hero = game controller over a
lit pedestal** (dark glass panel over the arena-photo hero, volt + purple ring accents,
drag-to-rotate + pointer parallax, `3D INTERACTIVE SCENE` label, hint «اسحب يد التحكم
لتدويرها»), and **prizes = gold trophy** (photo-poster panel with gold glow; the Three.js
scene mounts lazily over it). Each framed poster IS the LOW/FALLBACK tier.

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

# Front-end — Design Status, RTL, 3D, Performance

## Design status

- **DESIGN REFERENCE (DEC-15, rev 3 "Arena Night", 2026-10-20): the "E-SPORTS 2 Website
  Design" artifact** — https://claude.ai/artifact/SNEBV9cXyS8YCmeJJfEvqG. The owner rejected
  the earlier light "Tournament Broadcast" look; rev 3 is a **full dark, immersive esports
  design** built from competitor research (Esports World Cup, Kingdom of Gaming, BLAST,
  Gamers8): near-black ground, volt + purple glow accents (**colours superseded by rev 4 below**), gold for prizes, atmospheric
  arena/controller/crowd/trophy photography under gradient overlays. 7 artboards: tokens,
  home desktop + mobile, vote, registration, bracket, VIP invite. Implement from it; propose
  changes there first, then here.
- **Imagery note:** the canvas uses AI-generated placeholder photos (stored as artifact
  assets, preview resolution). Production uses full-resolution, licensed or event-owned
  photography with the same treatment: dark duotone atmosphere, gradient-to-background
  overlay, cyan/magenta light (rev 4).
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

## Theme tokens — rev 4 "logo palette" (owner request 2026-10-21; defined on `:root` in static/css/base.css)

Rev 4 keeps the Arena Night layout, motifs and motion **unchanged** and replaces only the
colours: the owner supplied the event logo (two silver shields — D-pad / face buttons — with
cyan and magenta outlines on deep navy) and asked that the whole site use the logo's colours,
**without the neon beam look** and without the old volt green. Sampled from the logo:
cyan #32DEE7, magenta #CB5BB3, silver #8C9299→#DCE3EA, gold badge #AF8220, navy #0F243A→#030A16.

```css
--bg: #050A14;          /* deep navy page ground (from the logo panel) */
--bg-2: #08101E;        /* alternate section band */
--surface: #0D1626;     /* cards, panels */
--surface-2: #132036;   /* badges, inner chips */
--line: #1F2D45;        /* borders */
--line-strong: #2C3D5C; /* input borders, secondary buttons */
--accent: #3CD6E0;      /* logo cyan — THE accent: CTAs, numbers, highlights, ticker */
--accent-2: #D15EB9;    /* logo magenta — secondary: slashes, glows, secondary buttons */
--accent-2-text: #EBA6DC; /* text-safe magenta */
--silver: #B4BFCC;      /* logo silver, neutral decor */
--ink: #04111A;         /* text on accent backgrounds */
--text: #EEF4FA;  --body: #C2CDDC;  --muted: #8E9CB3;  --link: #B8E8EE;
--gold: #E9C15C;        /* prizes/VIP + the logo's "2" badge (decor #D9A441, bronze #C8906B) */
--error: #FFB4AE;  --live: #FF4D5E;
```
Every translucent colour uses a channel token (`rgb(var(--accent-rgb) / 0.2)`) — **no raw
hex/rgba in templates or CSS rules**, so a future recolour is a `:root`-only change. SVG
presentation attributes (which cannot read CSS variables) are the only place hex is repeated.
Colour balance rule: cyan carries the UI; magenta appears in small doses (slashes, secondary
button, ambient radials); glows are soft (≈0.2–0.3 alpha) — no neon beams.

**Logo:** `static/img/brand/emblem.svg` — clean flat redraw of the owner's emblem (silver
shields, cyan/magenta outlines, deep-tone icons for legibility down to favicon size). Header
lockup = emblem + LOGO-TITLE + gold "2" badge + LOGO-SUB (`templates/partials/brand.html`).
Also the favicon. **Placeholder photos** were hue-regraded to cyan/magenta (gold untouched);
production photography follows the same treatment.

**Superseded:** rev 3.1 tokens (`--volt #D8F24A`, `--purple #8C5CFF`, ground `#07080F`).
The design artifact (DEC-15 link above) still shows rev 3.1 colours — layout reference only.

Theme model: **single dark theme**. Radius 0. Spacing 4/8/12/16/24/36/48/72.
Motifs: **glow** (soft accent `box-shadow`/`text-shadow` on CTAs and key numbers; magenta radial
gradients + shadows on panels) · photo sections with **gradient-to-bg overlays**
(`linear-gradient(to bottom|top, …, var(--bg))`) · 12° skew slashes · **cut-corner CTAs**
(`clip-path` 10–12px, primary only) · cards = `--surface`, 1px `--line`, photo header +
3–4px accent rule · EN section tags in Space Grotesk letterspaced (`01 · TOURNAMENTS`) ·
countdown cells with accent bottom rule · page ground carries two faint radials (magenta
top-corner, cyan low-corner).

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
- **accent (cyan) marquee ticker** — CSS keyframes, duplicated sequence for a seamless loop
- **hero countdown** — 1s interval; digits "--" until the date is set in SiteConfig
- **stats count-up** — numbers animate 0→value on first scroll into view (IntersectionObserver)
- **game-card hover** — lift 4px + accent border glow + image `scale(1.05)` (overflow hidden)
- **primary CTA hover** — invert to white bg / ink text
- **LIVE bar** — red dot pulse; the bar renders only during the event phase
- **section reveals** — 24px rise + fade on first entry
- **giant outline display word** ("GAME ON", `-webkit-text-stroke` accent @ ~18% alpha) and the
  vertical "REGISTER NOW" rail are static decor; **diagonal section edges** via `clip-path`
  wedges
FIXED regardless: all effects honor
`prefers-reduced-motion: reduce` (animations off, static states), and no effect may block
interaction or run while its element is off-screen.

## 3D scenes — subjects CONFIRMED by the design; engineering requirements FIXED

The design keeps both subjects in the Arena Night palette: **hero = game controller over a
lit pedestal** (dark glass panel over the arena-photo hero, cyan + magenta ring accents,
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

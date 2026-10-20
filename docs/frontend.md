# Front-end — Design Status, RTL, 3D, Performance

## Design status

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
- `reference/prototype.html` is the **CONTENT reference only**: its Arabic text and event
  information (captured in docs/content-ar.md). **Do not copy its code, colors, fonts or
  layout.**
- **Fixed product requirements regardless of design:** Arabic-first RTL · gaming style ·
  interactive 3D scenes · mobile-first performance (budgets below).

## Theme tokens (from the design artifact — define as CSS custom properties on `:root`)

```css
--bg: #07080F;          /* near-black page ground */
--bg-2: #0B0E1A;        /* alternate section band */
--surface: #10131F;     /* cards, panels */
--surface-2: #161A2B;   /* badges, inner chips */
--line: #242A40;        /* borders */
--line-strong: #32395A; /* input borders, secondary buttons */
--volt: #D8F24A;        /* THE accent: CTAs, numbers, highlights, ticker */
--purple: #8C5CFF;      /* glow/gradient only; text-safe variant #B9A6FF */
--text: #F2F4FF;        /* headings/body strong */
--body: #C5CBE8;        /* body text */
--muted: #9AA3C4;       /* secondary */
--link: #C9D2FF;        /* links (hover: volt) */
--gold: #E9C15C;        /* prizes/VIP (decor #D9A441, bronze #C8906B) */
--error: #FFB4AE;
```
Theme model: **single dark theme**. Radius 0. Spacing 4/8/12/16/24/36/48/72.
Motifs: **glow** (volt `box-shadow`/`text-shadow` on CTAs and key numbers; purple radial
gradients + shadows on panels) · photo sections with **gradient-to-bg overlays**
(`linear-gradient(to bottom|top, …, var(--bg))`) · 12° skew slashes · **cut-corner CTAs**
(`clip-path` 10–12px, primary only) · cards = `--surface`, 1px `--line`, photo header +
3–4px accent rule · EN section tags in Space Grotesk letterspaced (`01 · TOURNAMENTS`) ·
countdown cells with volt bottom rule · page ground carries two faint radials (purple
top-corner, volt low-corner).

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
scroll to anchors, bracket "LIVE" badge pulse, the **volt marquee ticker** (CSS keyframes,
duplicated item sequence for a seamless loop), and the **hero countdown** (1s interval JS,
digits show "--" until the event date is configured in SiteConfig). Rev 2 additions came from
competitor research (Kingdom of Gaming: countdown, audience split; Esports World Cup:
big-stats band, tiered partner rows). FIXED regardless: all effects honor
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

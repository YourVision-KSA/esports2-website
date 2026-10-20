# Routes — URL map, permissions, caching

Rule zero: **edge-cached pages contain no per-visitor state** (no CSRF token, no session
cookie set). Forms exist only on BYPASS routes. The home page links to forms; it never embeds
them.

Cache column = Cloudflare edge behavior (configured as cache rules, see docs/operations.md).
`s-maxage` set via `Cache-Control` response headers from Django.

## Public

| Route | Method | Phase gate | Cache | Notes |
|---|---|---|---|---|
| `/` | GET | all | 60 s | Single long page like the prototype: hero (3D), about, zones, schedule, prizes, rules, FAQ, sponsors, footer. Section anchors match the nav (`#tournaments` …). CTA buttons change per phase (vote / register / bracket). No forms. |
| `/vote/` | GET | vote | **BYPASS** | Ballot form + Turnstile widget + published counting rules. Outside the window: static "closed" message (safe to render, still bypass). |
| `/vote/` | POST | vote | BYPASS | Casts the ballot. Sets/reads the signed voter-token cookie. Rate-limited at edge + app. |
| `/vote/done/` | GET | vote+ | BYPASS | Confirmation ("تم تسجيل صوتك"). After close: totals page (counted + held) per docs/voting.md. |
| `/register/` | GET | registration | BYPASS | Game chooser with live seats-left (server-rendered; indicative). |
| `/register/<game-slug>/` | GET/POST | registration | BYPASS | The registration form; on success redirect to the manage page and show the manage link prominently (REG-SAVE-LINK). If an email was provided, the manage link is also queued to it via the outbox (REG-LINK-EMAILED); email remains optional. |
| `/r/<manage_token>/` | GET | registration..event | BYPASS | Player status page: game, confirmed/waitlist position, schedule of their matches. |
| `/r/<manage_token>/withdraw/` | POST | registration | BYPASS | Withdraw (confirm step). Triggers waitlist promotion. |
| `/bracket/` | GET | event..archive | 30 s | Overview of all confirmed games' brackets (server-rendered). |
| `/bracket/<game-slug>/` | GET | event..archive | 30 s | Full tree for one game. Progressive page: works without JS; with JS polls the JSON endpoint. |
| `/api/bracket/<game-slug>.json` | GET | event..archive | **10 s** | Flat match list for polling. The ONLY JSON endpoint. No PII beyond player display names/gamer tags. |
| `/invite/<token>/` | GET | all | BYPASS | Guest view: name, date, venue, QR code rendered client-side or as inline SVG. 404 for unknown/revoked tokens (uniform response, no token-validity oracle beyond this). |
| `/healthz` | GET | all | BYPASS | 200 + DB ping. Used by uptime checks. |

Phase-gated POST outside its window → 403 with the Arabic closed message. GET → closed-state
page. Both enforced in the view via `current_phase()`, regardless of what links exist.

## Static assets

| Path | Cache |
|---|---|
| `/static/**` (hashed filenames via ManifestStaticFilesStorage + Vite manifest) | 1 year, immutable |
| includes `*.js, *.css, *.woff2, *.glb, *.ktx2, *.webp, *.svg` | explicit CF cache rule — glb/ktx2 are NOT cached by default |

## Staff (all BYPASS, HTTPS, login + TOTP 2FA required)

| Route | Role | Notes |
|---|---|---|
| `/staff/` | per-model perms | Django admin: Games, SiteConfig (admin only), Ballots (hold/invalidate actions), Players/Registrations (remove, promote shown), Invitations (create, mark sent, revoke, CSV export), OutboxEmail, AuditLog (read-only). CSV exports admin-only + audit-logged. |
| `/staff/results/` | referee, admin | Mobile-friendly result entry: list of `pending` matches for today → tap → enter winner + score. Thin wrapper over the result-entry transaction. (Cut-list item: fall back to Django admin.) |
| `/staff/checkin/` | door, admin | Camera QR scanner (getUserMedia + a small JS decoder) → shows guest name/org → confirm button → atomic check-in. Manual token entry fallback + searchable guest list. (Cut-list item: list page only.) |

Admin path note: serve Django admin at `/staff/` (not `/admin/`) and rate-limit login at the
edge. Door/referee users get is_staff with narrow model permissions via groups.

## Error pages

Custom 403/404/500 in the site theme, Arabic, static-cacheable, no dynamic data. Cloudflare
"always online" may serve stale content pages if origin is down — acceptable by design.

# CLAUDE.md — E-SPORTS 2 Website

Single-event website for "تجمع الرياضات الإلكترونية – Arab Open University" (E-SPORTS 2), Riyadh,
organized by Your Vision KSA. One edition, planned end of life. Arabic-first, RTL, gaming
style with interactive 3D scenes (Three.js). Visual design: **pending the new /design artifact
(DEC-15)** — `reference/prototype.html` is a **CONTENT reference only** (Arabic text + event
info); never copy its code, colors, fonts or layout.

## Read first

All design decisions live in `docs/`. Do not re-derive them; follow them. If a task conflicts
with a doc, say so and stop — do not silently diverge.

| Doc | Contents |
|---|---|
| `docs/product.md` | Scope, actors, phases, product rules |
| `docs/architecture.md` | Stack, boundaries, hosting, consistency rules |
| `docs/data-model.md` | Entities, constraints, transactional rules |
| `docs/routes.md` | URL map, permissions, cache policy per route |
| `docs/voting.md` | Anti-abuse spec (security-critical) |
| `docs/frontend.md` | Design status (pending DEC-15), RTL, 3D requirements, performance budgets |
| `docs/testing.md` | Required tests for the critical rules |
| `docs/operations.md` | Deploy, runbooks, end of life |
| `docs/plan.md` | Timeline, gates, cut list, open decisions (DEC-xx) |
| `docs/content-ar.md` | ALL Arabic user-facing text |

## Stack (fixed — see docs/architecture.md before proposing anything else)

- Python 3.12+, **Django 5.2 LTS**, server-rendered templates. No DRF, no SPA, no React.
- **PostgreSQL** (local per developer; Cloud SQL in production). No other datastore, no Redis.
- Front-end: Django templates + one **Vite**-built bundle for the Three.js 3D scenes.
- Hosting: Cloud Run + Cloud SQL, region **me-central2** (Dammam). Cloudflare in front.
- No message broker, no WebSockets, no Kubernetes, no object storage, no CMS.

## Hard rules

1. **Arabic text**: every user-facing string comes from `docs/content-ar.md`, copied **exactly**.
   Never invent, "fix", or machine-translate Arabic. New strings needed → add a row to
   `docs/content-ar.md` marked `DRAFT — needs owner review` and flag it in your summary.
2. **Phases are enforced server-side** on every request (vote open/close, registration
   open/close). A scheduler is a convenience, never the enforcement mechanism.
3. **Critical rules require the tests in `docs/testing.md`** before the feature is considered
   done: one vote per token, seat race, one tournament per player, waitlist FIFO, single-use
   QR check-in, result entry + audit.
4. **No player accounts.** Players use secret manage links; voters use signed tokens. Only
   staff log in (Django auth + TOTP 2FA).
5. **Prefer Django built-ins** (admin, auth, forms, validators, messages) over custom code or
   new dependencies. Any new dependency needs a one-line justification in the PR/commit.
6. **Times**: store UTC, display Asia/Riyadh (UTC+3, no DST). `TIME_ZONE = "Asia/Riyadh"`,
   `USE_TZ = True`. Never hardcode naive datetimes.
7. **PII**: raw IPs and user agents are never stored — only HMAC hashes (see docs/voting.md).
   Exports of personal data are admin-only and audit-logged.
8. **Public GET pages that are edge-cached must not contain per-visitor state** (no CSRF
   tokens, no session cookies on them). Forms live only on cache-bypassed routes
   (see docs/routes.md).
9. Do not build items on the "deliberately not built" list in docs/architecture.md, and check
   `docs/plan.md` for whether a feature is currently cut before building it.
10. **`reference/prototype.html` is a content reference only.** Take Arabic text and event
    information from it (via docs/content-ar.md) — never its markup, CSS, colors, fonts,
    layout or JS. The design reference is the /design artifact (DEC-15); until it exists,
    theme tokens / fonts / 3D scene subjects in docs/frontend.md are PENDING — don't invent them.

## Conventions

- Single Django project `esports/` with apps: `core` (pages, phases, audit, outbox),
  `voting`, `registration`, `bracket`, `invitations`.
- Settings: `esports/settings/base.py`, `local.py`, `production.py`; secrets from env vars only.
- Templates in `templates/`, base template owns RTL (`<html lang="ar" dir="rtl">`), fonts,
  and theme tokens from docs/frontend.md.
- Migrations are committed; never edit an applied migration.
- Tests: pytest + pytest-django. Run: `pytest`. Concurrency tests are marked
  `@pytest.mark.concurrency` and need real Postgres (not SQLite).
- Lint/format: ruff (`ruff check . && ruff format .`).
- Local run: `python manage.py runserver` + `npm run dev` (Vite) for 3D work.
- Team knows Python basics but is **new to Django** — favor explicit, boring, well-commented
  code over clever abstractions; code is reviewed by the team.

## Git

- Default branch `main`. Small, single-purpose commits with imperative messages.

# E-SPORTS 2 — Event Website (يوم الرياضات الإلكترونية)

Website for the one-off esports event **"تجمع الرياضات الإلكترونية – Arab Open University"
(E-SPORTS 2)** in Riyadh, organized by **Your Vision KSA**. Three games (chosen by public
vote), 1v1, 16 players each, over three days, with the finals at the Arab Open University.

Arabic-first, right-to-left, gaming style with interactive WebGL scenes. Visual design is
pending the new /design artifact (DEC-15); `reference/prototype.html` is the **content
reference only** — its Arabic text and event info, not its code or look.

## What the site does

| Feature | Who uses it |
|---|---|
| Public vote on which games are played (advisory, anti-abuse protected) | Everyone |
| Player registration with 16-seat cap + waitlist, one tournament per player | Players |
| Live single-elimination brackets (3 × 16, 45 matches) | Everyone |
| Result entry with audit trail | Referees/admins |
| VIP invitations with QR check-in | Organizers, door staff |
| Content: schedule, zones, prizes, rules, FAQ, sponsors, stream links | Everyone |

No player accounts, no payments, no CMS. The site has a planned end of life: archive page,
data export, personal-data deletion, resource teardown.

## Stack

Django 5.2 LTS (server-rendered, Arabic RTL) · PostgreSQL · Three.js via a Vite bundle ·
Cloud Run + Cloud SQL (me-central2, Dammam) · Cloudflare (CDN, Turnstile, rate limits).
Rationale: `docs/architecture.md`.

## Status (2026-10-21)

W1 implementation done: all five apps, 55 tests green (incl. concurrency on PostgreSQL 16),
ruff clean, CI + Dockerfile. DEC-15 design delivered — "Arena Night" rev 3.1 theme
implemented (owner sign-off pending). Code lives in the GitHub org
[YourVision-KSA](https://github.com/YourVision-KSA/esports2-website) (private).
Timeline and gates: `docs/plan.md` · execution checklist per person: `docs/tasks.md`.
Target: vote opens ~Nov 2, registration ~Nov 16, event late Nov / early Dec 2026.

## Quickstart (Windows)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env               # defaults work with the local Postgres below
.\scripts\dev-db.ps1 start           # portable PostgreSQL 16 (see script header for setup)
python manage.py migrate
python manage.py setup_roles         # referee + door groups
python manage.py seed_demo           # candidate games + opens a 7-day vote window
python manage.py createsuperuser
python manage.py runserver           # http://127.0.0.1:8000  (admin at /staff/)
pytest                               # run all tests (needs the local Postgres)

# 3D hero scene (optional for backend work — the site runs without it):
cd frontend
npm install
npm run build                        # writes static/dist/ (gitignored; Docker builds it too)
```

## Documentation map

Start with `CLAUDE.md` (rules for AI-assisted building), then:

1. `docs/product.md` — scope, phases, product rules, assumptions
2. `docs/architecture.md` — the decided architecture (condensed ADR)
3. `docs/data-model.md` — entities and transactional rules
4. `docs/routes.md` — URLs, permissions, caching
5. `docs/voting.md` — anti-abuse design
6. `docs/frontend.md` — identity, fonts, 3D, performance
7. `docs/testing.md` — required critical tests
8. `docs/operations.md` — deploy, runbooks, end of life
9. `docs/plan.md` — week-by-week plan, cut list, open decisions
10. `docs/content-ar.md` — all Arabic user-facing text (single source of truth)

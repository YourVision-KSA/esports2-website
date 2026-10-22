# Tasks — who does what (Hussein / Yousef)

Working checklist derived from `docs/plan.md` (the plan stays the source of truth for
sequence and gates — this file only tracks execution). Mark a task `[x]` when it is done.

**People**: Hussein (husseinalshawa — dev machine, builds with Claude) ·
Yousef (24446357ksa@aou.edu.sa — org owner on GitHub, owner-facing follow-ups).

## ✅ Done

- [x] Django skeleton: project + 5 apps (core, voting, registration, bracket, invitations), settings, CI, Dockerfile
- [x] Data model + migrations, server-side phase gating
- [x] Voting module + anti-abuse (tokens, held bucket) + tests
- [x] Registration + 16-seat cap + waitlist FIFO + manage links + withdraw
- [x] Bracket + random draw + result entry + audit log
- [x] VIP invitations + QR check-in + email outbox
- [x] Staff admin (Django admin at `/staff/`) with groups
- [x] 55/55 tests green (incl. concurrency on real PostgreSQL 16), ruff clean
- [x] Local dev environment: portable PostgreSQL 16 (`scripts/dev-db.ps1`)
- [x] DEC-15 design delivered → "Arena Night" rev 3.1 theme implemented on the site
- [x] GitHub organization **YourVision-KSA** created, `esports2-website` pushed (private)
- [x] Org profile branded from `YOUR VISION Guide Line.pdf` (README, colors, logo assets)
- [x] Owner invitation sent to Yousef (24446357ksa@aou.edu.sa)
- [x] Local smoke test 2026-10-21: `/`, `/vote/`, `/register/`, `/bracket/`, `/healthz` all OK
- [x] Yousef accepted the GitHub owner invitation (active org admin, 2026-10-21)
- [x] Yousef's Mac dev environment set up (README → Quickstart macOS); 59/59 tests green
- [x] **Rebrand to the event logo — frontend rev 4 "logo palette"** (Yousef, 2026-10-21,
      branch `dev-yousef`): colours from the owner's logo (cyan / magenta / silver on deep
      navy, soft glows, volt green removed), clean SVG emblem + header lockup + favicon,
      placeholder photos regraded. Details: `docs/frontend.md` → Theme tokens rev 4.
      Logo export files for the owner were delivered outside the repo.

## ⬜ Remaining — Yousef

- [ ] Chase Your Vision for the open decisions in `docs/plan.md` — most urgent:
  - [ ] DEC-01 final event dates + venue
  - [ ] DEC-03 vote definition (game list, choices per ballot, window, counting-rules text)
  - [ ] DEC-04 final domain + who owns the Cloudflare account
  - [ ] DEC-05 GCP billing account owner
  - [ ] DEC-02, DEC-06..09, DEC-11..14 (see the decision log table)
- [ ] Get owner sign-off on the design **with the new logo colours** (rev 4, branch `dev-yousef`)
- [ ] **DEC-02**: the logo says «تجمع الرياضات الإلكترونية» but SITE-NAME / hero title say
      «يوم الرياضات الإلكترونية» — ask which name the site uses (one-line change after)
- [ ] Owner review of the new DRAFT strings LOGO-TITLE / LOGO-SUB (`docs/content-ar.md`)
- [ ] Collect content: prize values (DEC-13), staff roster (DEC-11), VIP sender mailbox (DEC-12)

## ⬜ Remaining — Yousef (code, with Claude) — next session starts here

Checkpoint 2026-10-21: rebrand done and committed on `dev-yousef` (PR open to `main`).
Order agreed — code work that does NOT wait on owner decisions:

- [ ] Merge the rebrand PR after review (Hussein to glance at it)
- [ ] Staff pages polish for phones: `/staff/results/` (wrong button label — uses REG_SUBMIT)
      and `/staff/checkin/` layout
- [ ] Privacy notice page + consent checkbox wiring (Arabic as DRAFT until DEC-08)
- [ ] Live bracket polling JS on `/bracket/<slug>/` (endpoint already exists)
- [ ] Camera QR scanner on `/staff/checkin/` (manual entry stays as fallback)
- [x] CI job 3: `npm run build` + size budgets (`frontend` job, 2026-10-22)
- [ ] Deploy workflow (GitHub Actions → Cloud Run), written now, enabled after DEC-04/05
- [x] **Hero 3D scene** — Yousef, 2026-10-22, branch `feat/hero-3d` (PR stacked on the
      rebrand PR). CC-BY "Dualsense" model cleaned (no PS logo/symbols), recoloured,
      21 MB → 362 KB; lazy loader, tiers, worker decode, chunked start-up (longest task
      ≈ 145 ms on a 4×-slowed phone), poster WebP 13 KB, credit line, budgets in CI.
      ⚠️ Tell Hussein the hero scene is done (it was on his list).
- [ ] Tier beacon endpoint (count-only, no PII) for the WebGL fallback-rate metric
- [ ] Trophy 3D scene (cut-list item 2 — static image acceptable)

## ⬜ Remaining — Hussein (with Claude)

- [ ] Upload the org avatar: Desktop `yourvision-avatar-dark.png` → GitHub org settings → profile picture
- [x] Verify staff 2FA enrollment flow end-to-end (left over from W1) — gap found and
      fixed 2026-10-21: new `enroll_totp` management command + 4 tests (59 total green)
- [ ] GCP + Cloudflare setup per `docs/operations.md` (~Oct 29; needs DEC-04/05 from Yousef first)
- [ ] Vote-page counting-rules content (needs DEC-03)
- [x] Hero 3D scene → done by Yousef 2026-10-22 (see Yousef's list)
- [ ] Trophy 3D scene (W5; cut-list fallback: static image)
- [ ] Monitoring + uptime alert before G1 (vote opens ~Nov 2)
- [ ] Staging cache + abuse rehearsal (W2)

## ⬜ Later — together

- [ ] Company website project (new repo in the org; use the brand guidelines)
- [ ] W4–W6 event items per `docs/plan.md` timeline (rehearsal, draw, event days, wrap-up)

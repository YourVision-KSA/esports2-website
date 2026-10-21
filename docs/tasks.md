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

## ⬜ Remaining — Yousef

- [ ] Accept the GitHub owner invitation (email from GitHub, or https://github.com/orgs/YourVision-KSA/invitation)
- [ ] Chase Your Vision for the open decisions in `docs/plan.md` — most urgent:
  - [ ] DEC-01 final event dates + venue
  - [ ] DEC-03 vote definition (game list, choices per ballot, window, counting-rules text)
  - [ ] DEC-04 final domain + who owns the Cloudflare account
  - [ ] DEC-05 GCP billing account owner
  - [ ] DEC-02, DEC-06..09, DEC-11..14 (see the decision log table)
- [ ] Get owner sign-off on the DEC-15 design (Arena Night rev 3.1, live on the site)
- [ ] Collect content: prize values (DEC-13), staff roster (DEC-11), VIP sender mailbox (DEC-12)

## ⬜ Remaining — Hussein (with Claude)

- [ ] Upload the org avatar: Desktop `yourvision-avatar-dark.png` → GitHub org settings → profile picture
- [ ] Verify staff 2FA enrollment flow end-to-end (left over from W1)
- [ ] GCP + Cloudflare setup per `docs/operations.md` (~Oct 29; needs DEC-04/05 from Yousef first)
- [ ] Vote-page counting-rules content (needs DEC-03)
- [ ] Hero 3D scene: Vite + Three.js bundle (W3 — not started, no `package.json` yet)
- [ ] Trophy 3D scene (W5; cut-list fallback: static image)
- [ ] Monitoring + uptime alert before G1 (vote opens ~Nov 2)
- [ ] Staging cache + abuse rehearsal (W2)

## ⬜ Later — together

- [ ] Company website project (new repo in the org; use the brand guidelines)
- [ ] W4–W6 event items per `docs/plan.md` timeline (rehearsal, draw, event days, wrap-up)

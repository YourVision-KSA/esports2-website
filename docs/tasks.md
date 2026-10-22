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

Checkpoint 2026-10-21: rebrand done and committed on `dev-yousef` (PR #2 → `main`).
Checkpoint 2026-10-22 (morning): hero 3D done on `feat/hero-3d` — superseded by the entry
below; the old restore point `checkpoint/2026-10-22` + tag `checkpoint-2026-10-22` remain.
**Checkpoint 2026-10-22-merged (current):** ALL of the work below is merged to `main`
(PRs #2–#11, incl. the security-hardening PR #11); 114/114 tests green; no open PRs.
Restore point: branch `checkpoint/2026-10-22-merged` + tag `checkpoint-2026-10-22-merged`.
Details + the stacked-PR merge lesson: `docs/plan.md` status log (2026-10-22 entries).
Order agreed — code work that does NOT wait on owner decisions:

- [x] Merge the rebrand PR after review (merged 2026-10-22 with the whole stack, PRs #2–#10)
- [x] **Staff pages for phones** (2026-10-22, branch `feat/staff-pages`): shared staff layout
      (who's signed in + logout, no public footer); results = Arabic round names, big
      winner cards (✓ + dim the other), score field, PRG + confirmation, game filter,
      Arabic errors; check-in = **look up → check ID → confirm** (nothing written on
      lookup), distinct ok/already/invalid cards, Arabic status chips, card list search.
      15 new tests. 20 new strings in content-ar.md are DRAFT (owner review).
- [x] **Privacy notice page** `/privacy/` (2026-10-22, branch `feat/staff-pages`): 10 sections,
      facts matched to the implementation (14-day voter cookie, HMAC-only IP/UA, gamer tags
      only in public, no national ID/payments); linked from the consent checkbox (new tab),
      the vote page and the footer; 4 tests. **All text DRAFT.**
- [ ] → Yousef: fill the [placeholders] in the privacy notice before registration opens
      (G2): data controller (Your Vision vs. university), contact email, hosting
      confirmation, retention days (DEC-08), under-18 policy (DEC-09), publish date.
      Ideally a quick legal read.
- [x] **Live bracket** (2026-10-22, branch `feat/bracket-live`): `static/js/bracket-live.js`
      polls the 10 s edge-cached JSON every 15 s (paused on hidden tab, back-off 30→120 s on
      errors, 60 s after the final), patches cells in place with a short highlight, reveals
      the champion; matches now ordered round→slot (were unordered). Verified end-to-end:
      a result entered elsewhere appeared after ~14 s with no reload. 4 tests.
- [x] **Bracket redesign — mirrored tree** (2026-10-22, from Yousef's bracket mock-up): R16 →
      QF → SF → **final in the centre** ← SF ← QF ← R16; match numbers م1–م15; «فائز م{n}»
      in undecided slots; trophy + CHAMPION; pure-CSS connectors that **light up along the
      winners' paths** (live); per-game theme colour from the approved palette. Phones: same
      DOM restacked by round, two cards per row. Layout logic in `bracket/tree.py`. Round→day
      labels are DRAFT pending DEC-01. 7 tests.
- [x] **Camera QR scanner** on `/staff/checkin/` (2026-10-22, branch `feat/qr-scanner`):
      native BarcodeDetector where available, else jsQR in a Web Worker (iOS Safari; loaded
      only then). Scan → lookup (nothing written) → ID check → confirm; camera off while a
      guest awaits confirmation, auto-restarts for the next guest, ignores the code just
      handled for 6 s, released on hidden tab. Verified with a fake camera on both paths
      (native 2.9 s, worker 0.8 s). Scanner JS 1.3 KB + worker 46 KB gzip (budget 60 KB).
- [x] **Bug fixed: VIP invitation page returned 500 for every valid invitation** (QR PNG needed
      Pillow, not installed) → inline SVG QR; PR #6 straight to `main`, regression test.
- [x] CI job 3: `npm run build` + size budgets (`frontend` job, 2026-10-22)
- [x] **Deploy workflow** (2026-10-22, branch `ci/deploy-cloud-run`): `.github/workflows/deploy.yml`
      — after CI on `main`: build → Artifact Registry → migrate job → new revision → smoke test →
      rollback hint; keyless WIF, actions pinned to SHAs, `production` approval gate, staging via
      manual run. **Dormant until `GCP_PROJECT_ID` is set.** One-time setup commands:
      docs/operations.md → *Deploy setup*. Production `collectstatic` verified with the Vite
      bundles; Vite assets now cached 1 year by WhiteNoise.
- [ ] → after DEC-05: run the *Deploy setup* checklist (≈30 min), then rehearse a rollback on staging
- [x] **Hero 3D scene** — Yousef, 2026-10-22, branch `feat/hero-3d` (PR stacked on the
      rebrand PR). CC-BY "Dualsense" model cleaned (no PS logo/symbols), recoloured,
      21 MB → 362 KB; lazy loader, tiers, worker decode, chunked start-up (longest task
      ≈ 145 ms on a 4×-slowed phone), poster WebP 13 KB, budgets in CI. Licence credit
      moved from under the scene to a faint footer line (owner request 2026-10-22) —
      it must not be removed entirely (CC BY 4.0 condition).
      ⚠️ Tell Hussein the hero scene is done (it was on his list).
- [x] **Tier beacon** (2026-10-22, branch `feat/tier-beacon`): `POST /beacon/3d` count-only
      (no PII, no cookie, ≤ 1 per tab session via sendBeacon) → `TierStat` daily counters,
      race-safe; `manage.py tier_report` shows the fallback share per device; admin
      read-only list. Ops: add `/beacon/*` to the Cloudflare BYPASS + rate-limit rules. 11 tests.
- [ ] Trophy 3D scene (cut-list item 2 — static image acceptable)

## ⬜ Remaining — Hussein (with Claude)

- [x] Upload the org avatar (verified 2026-10-22: Your Vision logo is live on the org)
- [x] **Full review + merge of Yousef's branches** (2026-10-22): file-by-file security review
      of PRs #2–#9 (no critical findings), merged to `main` (stack consolidated via PR #10),
      verified 105/105 → 114/114 tests on real local PostgreSQL 17 (installed as a service).
- [x] **Security hardening PR #11** (2026-10-22): M1 origin shield (`CF_ORIGIN_TOKEN`,
      core/middleware.py — direct Cloud Run hits get 403, CF-Connecting-IP only trusted
      behind the shield), M2 WIF main-only + required reviewers, constant-time internal
      token compare, 12 h staff sessions, pinned CI actions, outbox ERROR logging without
      recipient PII, Error Reporting + CSP documented in operations.md. 9 new tests.
- [x] Owner status update (Arabic) written: `company-update-2026-10-22.md` (untracked)
- [x] Verify staff 2FA enrollment flow end-to-end (left over from W1) — gap found and
      fixed 2026-10-21: new `enroll_totp` management command + 4 tests (59 total green)
- [ ] GCP + Cloudflare setup per `docs/operations.md` (~Oct 29; needs DEC-04/05 from Yousef first)
      — deploy workflow + step-by-step *Deploy setup* commands are ready (PR #9)
- [~] Vote-page counting-rules content — VOTE-RULES draft is already shown on `/vote/`;
      only owner approval of the text is left (DEC-03)
- [x] Hero 3D scene → done by Yousef 2026-10-22 (see Yousef's list)
- [ ] Trophy 3D scene (W5; cut-list fallback: static image)
- [ ] Monitoring + uptime alert before G1 (vote opens ~Nov 2)
- [ ] Staging cache + abuse rehearsal (W2)

## ⬜ Later — together

- [ ] Company website project (new repo in the org; use the brand guidelines)
- [ ] W4–W6 event items per `docs/plan.md` timeline (rehearsal, draw, event days, wrap-up)

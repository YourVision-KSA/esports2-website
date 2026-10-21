# Plan — Timeline, Gates, Cut List, Open Decisions

Planned 2026-10-20 against the **earliest** plausible event (Nov 26–28). If the event lands in
early December, weeks 5–6 gain slack (spend it on polish and rehearsal, do not move gates
earlier than needed). Dates shift with DEC-01; the **sequence and gates are fixed**.

## Status log

- **2026-10-20** — W1 build largely done, ahead of schedule: Django skeleton, all five
  apps with models + migrations, phase gating, voting + anti-abuse, registration +
  waitlist, bracket + draw + results, invitations + check-in, outbox, staff admin,
  structure-only templates (theme pending DEC-15), **55/55 tests green** (incl. all
  concurrency tests on real PostgreSQL 16), ruff clean, CI workflow, Dockerfile.
  Local portable PostgreSQL 16 set up (`scripts/dev-db.ps1`). Remaining for W1/W2:
  DEC answers (esp. DEC-03 vote definition, DEC-15 design), 2FA enrollment flow check,
  GCP/Cloudflare setup per docs/operations.md.

- **2026-10-21** — Code pushed to GitHub org **YourVision-KSA** (private repo
  `esports2-website`); owner invite sent to Yousef (24446357ksa@aou.edu.sa, pending
  acceptance); org profile branded from the official guideline PDF. Arena Night rev 3.1
  theme is implemented on the site (commit 761e9b5). Local smoke test green: `/`,
  `/vote/`, `/register/`, `/bracket/`, `/healthz`. Execution checklist with per-person
  assignments added: `docs/tasks.md`.

- **2026-10-21 — CHECKPOINT `checkpoint-2026-10-21`** (git tag; restore with
  `git checkout checkpoint-2026-10-21`). Frozen state: W1 build complete on the Arena
  Night rev 3.1 theme, **59/59 tests green**, ruff clean. Infrastructure this day:
  GitHub org **YourVision-KSA** (public repo, `main` protected via ruleset: PR + CI
  required), work branch `dev-hussein`, owner invite to Yousef pending, branded org
  profile. New since W1 log: `enroll_totp` command (staff 2FA first-device enrollment,
  4 tests). A full logo-driven redesign (rev 4: event-logo palette, hero 3D controller
  scene, static logo panel) was built, then **reverted at the owner's direction** —
  it lives in history between `2f9746e` and `fc19a91` on `dev-hussein` and can be
  cherry-picked back selectively. Event logo source: `Downloads/UI` on the dev machine.
  Next up: DEC answers (Yousef), GCP/Cloudflare (~Oct 29), design direction decision.

## Timeline

| Week | Dates | Build focus | Milestone |
|---|---|---|---|
| W1 | Oct 20–26 | Django skeleton (apps, settings, CI, pytest+Postgres) · data model + migrations · phase gating · **voting module + its tests** · RTL base template (structure only; theme tokens + fonts land once DEC-15 delivers the design) | All DEC-01..11 answered; **DEC-15 design delivered**; voting logic green |
| W2 | Oct 27–Nov 2 | Anti-abuse complete (Turnstile, voter tokens, held bucket, burst report) · Django admin + 2FA + groups · **GCP + Cloudflare setup ~Oct 29** (operations.md checklists) · cache + abuse rehearsal on staging · vote-page content + counting rules | **GATE G1 — vote opens Mon Nov 2** |
| W3 | Nov 3–9 | Monitor vote (held share, bursts, daily `vote_report`) · **registration + waitlist + manage links + seat-race tests** · hero 3D scene integration starts | Vote closes Sun Nov 8 → publish counted+held totals |
| W4 | Nov 10–16 | Permits window (owner, off-site) · confirm games in DB · **bracket + results entry + audit** · **invitations + QR check-in** · email outbox · privacy notice + consent flow · content updated to confirmed games | **GATE G2 — registration opens Mon Nov 16** |
| W5 | Nov 17–23 | Monitor registration · send VIP invitations · trophy 3D scene · performance tiers + poster fallback + budgets · staff training · printed-fallback kit · **full event rehearsal** (fake result → bracket updates; QR scan; exports) | Rehearsal passed |
| W6 | Nov 24–28 | Close registration Nov 24 · random draw + seed brackets · dry run Nov 25 · **event Nov 26–28**: results + check-in live, stream links on | **GATE G3 — event day 1** |
| Wrap | Dec | Archive page · exports · PII purge at retention deadline · teardown (operations.md → End of life) | Project closed |

## Gates — what MUST be finished before each opens

**G1 (vote opens):** ballot flow + one-ballot constraint + held bucket + Turnstile verified
server-side · edge cache/rate rules verified with curl · counting rules published on /vote/ ·
staff admin with 2FA · monitoring + uptime alert on · voting tests green on the deployed
revision · final domain live. **NOT required for G1:** 3D scenes (static hero poster is
acceptable at vote time), registration, bracket, invitations.

**G2 (registration opens):** seat race / one-tournament / waitlist FIFO tests green · manage
link flow + withdraw · privacy notice + consent checkbox live · registration content for the
confirmed games · waitlist cap set · CSV export works · G2 rehearsal on staging done.

**G3 (event day 1):** draw done + brackets rendered · results entry works on a phone ·
check-in works on a phone (or its cut fallback) · printed bracket + player + VIP lists ·
staff trained, runbook printed · min-instances=1 for event days.

## Cut list (if behind — cut top-down, never cut below the line)

1. QR scanner page → door staff use the searchable guest-list page, or paper
2. Trophy 3D scene → static image (the hero scene is the identity; keep it)
3. Email outbox automation → manual emails + WhatsApp share links from admin (also stops the
   registration manage-link emails — the on-screen link remains the primary channel)
4. Waitlist self-service withdraw → admin does withdrawals manually
5. Live bracket polling (JSON endpoint) → server-rendered bracket, cache purge on each result
6. Custom `/staff/results/` page → referees use Django admin
7. Hero 3D interactivity reduced (no drag, parallax only) → still 3D, less input code

---
**Never cut:** seat-claim transaction correctness · one ballot per token · staff 2FA ·
server-side phase gating · backups/PITR · the printed event-day fallback.

## Decision log (owner input needed; owner = Your Vision)

| ID | Decision | Needed by | Status |
|---|---|---|---|
| DEC-01 | Final event dates + venue | ASAP (this week) | OPEN |
| DEC-02 | Public site name stays "يوم الرياضات الإلكترونية" or rebrands to "تجمع الرياضات الإلكترونية" | W1 | OPEN |
| DEC-03 | Vote definition: candidate game list, choices per ballot (provisional: pick 3), window dates, counting-rules text approved | before G1 | OPEN |
| DEC-04 | Final domain + Cloudflare account owner | before G1 | OPEN |
| DEC-05 | GCP billing/trial account owner; sccc credit terms checked (contingency) | this week | OPEN |
| DEC-06 | University residency/hosting answer | before G1 (default: GCP Dammam) | OPEN |
| DEC-07 | Waitlist cap per game (suggest 8) + whether positions are shown to players (suggest yes) | before G2 | OPEN |
| DEC-08 | Registration fields final + privacy notice text + retention period (30–90 days) | before G2 | OPEN |
| DEC-09 | Under-18 policy (+ guardian consent text if allowed) | before G2 | OPEN |
| DEC-10 | Online play scope confirmed as "stream links only" | before G3 | ASSUMED YES |
| DEC-11 | Staff roster (admin/referee/door names) | W4 | OPEN |
| DEC-12 | VIP mail sender mailbox/domain; SPF/DKIM configured + test email passed | before W5 | OPEN |
| DEC-13 | Prize values / descriptions for the prizes section | before G3 | OPEN |
| DEC-14 | Confirm no payments (A5) and no national ID (A6) | this week | ASSUMED YES |
| DEC-15 | **New design from /design** — the design artifact that becomes the design reference (theme tokens, fonts, 3D scene subjects, effects → recorded in docs/frontend.md). `reference/prototype.html` is content reference only | before the base template in W1 | **DELIVERED 2026-10-20** — "Tournament Broadcast" direction, 7 artboards: https://claude.ai/artifact/SNEBV9cXyS8YCmeJJfEvqG (tokens recorded in docs/frontend.md); owner sign-off pending |

When a DEC closes, record the answer here (edit the row, add the date) — this table is the
single place future sessions check before building anything that depends on an open decision.

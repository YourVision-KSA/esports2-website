# Architecture — Decided (condensed ADR, updated 2026-10-20)

Status: **Accepted** (was Proposed; updated for deadline, Django confirmation, credits,
one-tournament rule). Full reasoning lives in the architecture review conversation; this file
is the operative summary.

## Decision

One **stateless Django monolith** (server-rendered Arabic RTL pages + one Vite-built Three.js
bundle) with one **managed PostgreSQL** database as the only source of truth, deployed as a
container on **Cloud Run + Cloud SQL in me-central2 (Dammam)**, behind **Cloudflare**
(CDN, Turnstile bot challenge, rate limiting). Bracket updates by **polling edge-cached JSON**
(~10 s TTL). VIP email via the organizer's own mail system through a DB outbox table.
Cloud Scheduler triggers outbox delivery and reminders; **phase open/close is enforced in the
app**, never by the scheduler alone.

```
 Visitors / voters / players (mobile, KSA)      Staff (admin · referee · door)
              │ HTTPS                                   │ HTTPS + 2FA
              ▼                                         ▼
 ┌────────────────────────────────────────────────────────────────────┐
 │ Cloudflare: CDN + Turnstile + rate limits (KSA PoPs)               │
 │  cache 1y immutable: /static/* (JS, glb, ktx2, woff2 — hashed)     │
 │  cache ~60s: content pages   cache ~10s: /api/bracket/*.json       │
 │  BYPASS: /vote/* /register/* /r/* /invite/* /staff/*               │
 └──────────────┬─────────────────────────────────────────────────────┘
                │ cache misses + all writes
                ▼
 ┌──── Django app (one container, stateless, autoscale 0..CAP) ───────┐
 │ core (pages, phases, audit, outbox) │ voting │ registration        │
 │ bracket │ invitations │ Django admin (staff, TOTP 2FA)             │
 └───────┬────────────────────────────────────────┬───────────────────┘
         │ transactions                           │ SMTP (async, outbox)
         ▼                                        ▼
 Cloud SQL PostgreSQL (me-central2,         Organizer's mail domain → VIPs
 backups + PITR)        ◄── Cloud Scheduler (outbox tick, reminders)
```

## Why this shape (one paragraph)

The workload is tiny and read-heavy with busy windows that are **sequential, never
simultaneous** (vote → permits → registration → event). The hard problems are **correctness**
(seat race, one vote per token, atomic result advancement) and **staff tooling**, not scale.
One framework codebase enforces every rule in one place; Django's admin supplies roughly a
third of the scope (results entry, waitlist, VIP list, exports) without custom security code —
decisive for a team new to backend work. Reads are absorbed at the edge; writes are capped by
design (48 seats; one ballot per token).

## Hosting decision rule (updated 2026-10-20)

Verified: Cloud Run is available in me-central2 (Tier 2 pricing) and Cloud SQL supports the
Dammam region. sccc by stc offers ApsaraDB RDS for PostgreSQL but only Kubernetes (ACK) for
containers — on sccc the app would run on a plain ECS VM.

| Case | Choice |
|---|---|
| Default (residency unknown or required) | **GCP me-central2 on the $300/90-day free trial** (Google's public offer). The estimated usage for ~5 cloud weeks fits well inside it, and it hedges residency. |
| University mandates a Saudi-licensed (CST) provider | **sccc by stc, on the credit available there**: ApsaraDB RDS for PostgreSQL + one small ECS VM (container via systemd + Caddy for TLS). Accept added ops. Verify credit terms + RDS-PostgreSQL in the Riyadh console first. |
| Residency confirmed NOT required and GCP trial unavailable | Small PaaS (Railway/Fly.io), paid monthly. Last resort only. |

Lifecycle: develop locally (Postgres per developer); create cloud resources **4–5 days before
the vote opens** (rehearsal needs the real edge); resources stay up continuously from first
deploy through the event; delete after archive + retention period. Backups + PITR from day one.

## Boundaries and consistency

- **Modules** (apps) share one DB but own their tables: core, voting, registration, bracket,
  invitations. No service extraction — the busy windows never overlap.
- **Strong consistency (transactions, DB constraints):** seat claim + waitlist order; one
  active registration per player; one ballot per token; result entry + winner advancement;
  single-use QR check-in.
- **Eventual (seconds–minutes) is fine:** public bracket view, seats-left counter (indicative),
  vote tally (hidden until close anyway), all content.
- **Failure isolation:** WebGL failure never blocks a task (static poster fallback; forms work
  without the 3D bundle). Mail failure never fails the triggering action (outbox + retry).
  Turnstile outage → votes go to the *held* bucket (registration instead rejects + retries —
  only 48 seats). Site down during the event → paper bracket is the master; results entered
  later.
- **Auth:** staff only (Django auth + TOTP 2FA via django-otp; roles admin/referee/door as
  groups). Players: secret manage links. Voters: signed tokens. No OAuth/SSO.
  `/staff/login/` checks password and TOTP code in one step with one generic error (a right
  password is never confirmed before the second factor) and has an app-side failure
  throttle per typed username and per client network (core/staff_login.py; security
  assessment 2026-11-19, YV-38).
- **Client identity for limits** (security assessment 2026-11-19): every app-side limit
  (vote bursts, registration, staff login, beacon) counts per client **network** —
  `core.security.network_key`: the address for IPv4 and IPv4-mapped IPv6, the **/64** for
  IPv6 (same rule as the platform), stored only as an HMAC (`ip_hash`). The raw address is
  used only for Turnstile's `remoteip`. Cloudflare's headers (`CF-Connecting-IP`,
  `X-Client-ASN`) are trusted only on requests that carry the valid origin-shield token;
  secret headers are compared as bytes (a non-ASCII value is a 403, never a 500).
- **Vote classification** runs inside the ballot's transaction after a per-network
  `pg_advisory_xact_lock`, so parallel ballots from one network cannot all pass the burst
  limit; only ballots that passed Turnstile count toward the bursts (voting/services.py,
  YV-34/YV-35).

## Scaling and limits

- Edge absorbs read spikes. The first server-side bottleneck is **DB connections**: cap Cloud
  Run `max-instances` so (instances × conns per instance) stays under the Cloud SQL tier limit.
- Keep **min-instances=1** only during the vote/registration opening windows and event days;
  0 otherwise.
- 10×: bigger DB tier for the window. 100× (vote goes viral): batch ballot intake — do NOT
  build now.

## Deliberately not built

Redis/cache server · message broker · WebSockets/real-time service · object storage · search ·
Kubernetes · microservices · CMS · DRF/API framework · SPA/React · analytics stack ·
Terraform/IaC (runbook instead) · player accounts · payments · SMS/WhatsApp APIs · Nafath ·
seeding algorithms beyond a random draw · English locale.

Adding any of these requires a stated requirement and an update to this file.

Clarification (2026-10-22): the count-only hero-3D tier beacon (`TierStat` daily counters —
no visitor identifiers, docs/frontend.md) is a frontend health metric serving the stated
"WebGL fallback rate" requirement, **not** an analytics stack; nothing third-party, nothing
per-visitor. Its per-network limit (`BEACON_PER_NETWORK_10MIN`, security assessment
2026-11-19) counts in Django's default in-process local-memory cache — not a cache server;
the limit is per Cloud Run instance, which is enough for a statistics counter.

## Standing risks (top 3)

1. Vote manipulation degrading the result's legitimacy (residual risk in docs/voting.md).
2. Residency/controller answered late → forced hosting move near a deadline (mitigated by
   container + standard Postgres portability; rehearsed dump/restore).
3. 3D performance on mid-range phones (mitigated by tiers + budgets in docs/frontend.md).

## Review triggers

Revisit this architecture if: hosting must move on-premise/CST-licensed · the vote becomes
binding (needs identity verification BEFORE it opens) · payments/ticketing/national-ID/under-18
flows are added · the site must serve future editions · instance cap saturated >10 min or DB
connections >80% during the vote · any staff-account compromise or PII exposure.

# Operations — Setup, Deploy, Runbooks, End of Life

Principle: no idle cost. Develop locally; cloud exists only from ~5 days before the vote opens
until archive + retention end. **Resources are NOT torn down between phases** — the DB holds
registrations and brackets continuously from first deploy.

## Environments

| Env | Where | Notes |
|---|---|---|
| local | each developer: Python venv + local PostgreSQL 16 + `npm run dev` | `.env` file, DEBUG=on, Turnstile test keys |
| production | Cloud Run + Cloud SQL, me-central2 | created per checklist below |
| staging | second Cloud Run service `esports-staging`, separate database **on the same Cloud SQL instance** | used for the launch rehearsals; deleted after registration opens |

## GCP setup checklist (run ~Oct 29, ≥4 days before vote opens)

1. Create the GCP account on the **$300/90-day free trial** (owner decides whose billing card —
   DEC-05). Create project `esports2-prod`, region `me-central2`.
2. Enable APIs: Run, Cloud SQL Admin, Artifact Registry, Secret Manager, Cloud Scheduler,
   Cloud Build (or deploy from GitHub Actions with a service-account key/WIF).
3. **Cloud SQL**: PostgreSQL 16, smallest shared-core tier, me-central2, private IP +
   Cloud SQL connector; **automated backups ON + point-in-time recovery ON** from creation.
   Note the tier's max_connections → set Cloud Run max-instances so
   `instances × (CONN_MAX_AGE pool per instance, ~5) ≤ 60%` of it.
4. **Secret Manager**: `SECRET_KEY`, `DATABASE_URL`, `SIGNALS_SALT`, `TURNSTILE_SECRET`,
   `SMTP_*`. Never in the image or repo.
5. **Artifact Registry** (me-central2) + first image push.
6. **Cloud Run** service `esports`: min-instances 0 (raised for windows, below), max-instances
   per the connection math (likely 3–5), concurrency 40, CPU 1 / 512 MB, startup probe on
   `/healthz`.
7. Run migrations as a Cloud Run **job** (same image, `python manage.py migrate`) — not at
   container boot.
8. `createsuperuser` via a one-off job; enroll TOTP 2FA immediately in the same job with
   `python manage.py enroll_totp <username>` (prints the otpauth:// URL to scan — required,
   because OTPAdminSite refuses login without a confirmed device); create groups
   admin/referee/door and the staff users (roster: DEC-11). Rotate a compromised device
   with `enroll_totp <username> --replace`.
9. **Cloud Scheduler**: `outbox-tick` every 5 min → authenticated POST `/internal/outbox/`
   (OIDC token, Cloud Run IAM); `vote-report` twice daily during the vote window.
10. Domain mapping or a Cloudflare-proxied CNAME to the Cloud Run URL.

## Cloudflare checklist

1. Domain on Cloudflare (final domain BEFORE the vote opens — DEC-04), DNS proxied, Full
   (strict) TLS.
2. **Cache rules** (order matters):
   - BYPASS: `/vote*`, `/register*`, `/r/*`, `/invite/*`, `/staff*`, `/healthz`, `/internal/*`, `/beacon/*`
   - Cache 1 y immutable: `/static/*` — explicitly include `.glb .ktx2 .woff2` (not cached by default)
   - Edge TTL 10 s: `/api/bracket/*`
   - Edge TTL 60 s: `/` and other content pages (respect origin Cache-Control)
3. **Rate limiting**: POST `/vote/` 10/min/IP → managed challenge; `/staff/` login 5/min/IP → block 10 min;
   POST `/beacon/*` 6/min/IP → block (keeps the anonymous 3D counters honest).
4. **Turnstile**: create widget, put the site key in templates, secret in Secret Manager.
5. Verify with `curl -I`: `cf-cache-status: HIT` on static + content pages, `BYPASS`/`DYNAMIC`
   on forms; **no `Set-Cookie` on cached responses**.
6. Residency note: Cloudflare terminates TLS and proxies form submissions → it is a data
   processor. Acceptable under the current assumption; if strict localization is confirmed,
   move the BYPASS (personal-data) routes to a direct in-region path and keep Cloudflare for
   static only.

## Deploy pipeline

GitHub Actions on push to `main`: ruff + pytest (Postgres service) → build image → push to
Artifact Registry → deploy new Cloud Run revision at 100% → smoke test `/healthz` + `/`.
**Rollback** = `gcloud run services update-traffic esports --to-revisions PREV=100` (keep the
command in this file, rehearse it once).

## Monitoring & alerts (GCP built-ins only)

- Uptime check on `/healthz` every minute → email alert to the team.
- Alerts: 5xx rate > 2% over 5 min; p95 latency > 2 s on `/vote/` or `/register/`;
  Cloud SQL connections > 80%; Cloud Run instance count at max for > 10 min.
- Dashboards open during launch hours: requests, 5xx, DB connections, held-vote share
  (`manage.py vote_report`), CF cache hit rate, CF analytics on `/static/*` (if the 3D files
  stop HITting, bandwidth becomes the top cost — fix the rule immediately).
- Client beacon: tier/fallback counts (frontend.md) — check daily with `python manage.py
  tier_report [--days 7]` (or admin → Tier stats); a rising FALLBACK rate on mobile = 3D
  regression. Counts only — no visitor data.

## Window runbooks

**Before each window (vote open, registration open, each event day):** set min-instances=1;
confirm SiteConfig datetimes (Riyadh); rehearse the user path on a real phone over mobile data;
confirm backup ran in the last 24 h. **After:** min-instances back to 0 (except during the
event span).

**Vote launch day:** the checklist in docs/voting.md.

**Registration launch day:** seat race tests green on the deployed revision (run once against
staging); waitlist cap set; privacy notice page live; a dry-run registration + withdraw +
promotion on staging; export CSV works.

**Event days:**
- Print before day 1: full bracket sheets per game, confirmed-player lists with phones
  (controlled copies, collected after), VIP guest list. **Paper is the master record**; the
  site mirrors it.
- Referees enter results on `/staff/results/` (fallback: Django admin; fallback: paper only,
  enter at night).
- Door staff: `/staff/checkin/` on their phones (fallback: searchable list; fallback: paper).
- If the site is down: the event continues; restore from the latest revision/backup; never
  debug live during a final.

## Incident basics

- Staff account suspected compromised: deactivate user in admin (another admin), rotate their
  password+TOTP, check AuditLog for their actions, rotate `SECRET_KEY` if session theft is
  suspected (logs everyone out — acceptable).
- Data restore: Cloud SQL PITR to a new instance → point staging at it → verify → swap
  `DATABASE_URL`. Rehearse once before the event.

## End of life (after the event)

1. Phase → archive: freeze results/winners/sponsors page; disable all forms.
2. Exports for organizer + Federation (audit-logged).
3. At the published retention deadline: run the PII purge command (data-model.md → Retention);
   delete `SIGNALS_SALT`.
4. Final DB dump to the organizer's encrypted storage (per retention policy), then delete:
   Cloud Run services, Cloud SQL instance **and its backups**, Artifact Registry images,
   Scheduler jobs, secrets. Downgrade/close the billing account before trial end if nothing
   remains.
5. Optional: export the archive page as static HTML and host it free (e.g. the organizer's
   site) so the URL survives; then delete the GCP project entirely.

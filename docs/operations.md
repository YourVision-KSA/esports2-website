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

1. Create the GCP account on the **$300/90-day free trial** (billing account owner —
   DEC-05). Create project `esports2-prod`, region `me-central2`.
2. Enable APIs: Run, Cloud SQL Admin, Artifact Registry, Secret Manager, Cloud Scheduler,
   Cloud Build (or deploy from GitHub Actions with a service-account key/WIF).
3. **Cloud SQL**: PostgreSQL 16, smallest shared-core tier, me-central2, private IP +
   Cloud SQL connector; **automated backups ON + point-in-time recovery ON** from creation.
   Note the tier's max_connections → set Cloud Run max-instances so
   `instances × (CONN_MAX_AGE pool per instance, ~5) ≤ 60%` of it.
4. **Secret Manager**: `SECRET_KEY`, `DATABASE_URL`, `SIGNALS_SALT`, `TURNSTILE_SECRET`,
   `INTERNAL_TOKEN`, `CF_ORIGIN_TOKEN`, `SMTP_*`. Never in the image or repo.
   Production **refuses to start** (esports/settings/production.py) unless `SECRET_KEY`,
   `SIGNALS_SALT`, `TURNSTILE_SECRET`, `TURNSTILE_SITE_KEY` (real keys, not Cloudflare test
   keys), `INTERNAL_TOKEN`, `SITE_BASE_URL` (the public `https://` origin) and
   `CF_ORIGIN_TOKEN` are set, and `TURNSTILE_ENABLED` is not False. A service that is
   knowingly not behind Cloudflare (staging) sets `ALLOW_NO_ORIGIN_SHIELD=True` instead of
   `CF_ORIGIN_TOKEN`.
5. **Artifact Registry** (me-central2) + first image push.
6. **Cloud Run** service `esports`: min-instances 0 (raised for windows, below), max-instances
   per the connection math (likely 3–5), concurrency 40, CPU 1 / 512 MB, startup probe on
   `/healthz`.
7. Run migrations as a Cloud Run **job** (same image, `python manage.py migrate`) — not at
   container boot.
8. `createsuperuser` and TOTP enrollment run **interactively from a staff laptop** against
   the production database through the Cloud SQL Auth Proxy — **not** as a Cloud Run job.
   Start the proxy (`cloud-sql-proxy <project>:me-central2:esports-db --port 5433`) and, in
   that terminal session only, point `DATABASE_URL` at it —
   `export DATABASE_URL=postgres://<user>:<password>@127.0.0.1:5433/<database>` — otherwise
   the commands run against your LOCAL database and production still has no admin (the
   `database-url` secret's value does not work from a laptop: it addresses the instance
   the way Cloud Run reaches it). Close the terminal afterwards. Why not a job:
   `enroll_totp <username>` shows the otpauth:// URL, which contains the permanent TOTP
   secret, and a job's stdout is kept in Cloud Logging. The command refuses to print the
   URL to anything but a terminal (or `--url-file PATH`, a new 0600 file — delete it after
   scanning; the command creates the file before it touches the device, so a path that
   cannot be written changes nothing). Enrollment is required because OTPAdminSite refuses login without a confirmed
   device. Then `python manage.py setup_roles` (groups referee/door with their narrow
   permissions — **re-run it after every upgrade**, it replaces the groups' permissions)
   and create the staff users (roster: DEC-11). Rotate a compromised device with
   `enroll_totp <username> --replace`. **If a secret was ever logged** (an older runbook
   ran this as a job): first rotate every device enrolled that way with `--replace` —
   rotation is what makes the leaked secret useless; then remove the entries (Cloud Logging
   cannot delete single entries: `gcloud logging logs delete <log name>` deletes a whole
   log, so export anything else you need from it first) and check who had log-viewer access.
9. **Cloud Scheduler**: `outbox-tick` every 5 min → POST `<service URL>/internal/outbox/`
   with the header **`X-Internal-Token: <internal-token secret value>`** (core/views.py
   rejects the tick with 403 without it; the endpoint is exempt from the origin shield, so
   the scheduler may call the `*.run.app` URL directly). `vote_report` has no HTTP
   endpoint: create a Cloud Run **job** (same image) running
   `python manage.py vote_report` and schedule that job twice daily during the vote window.
   Likewise a one-off job `python manage.py strip_vote_signals` 14 days after the vote
   closes (it refuses earlier) — the privacy notice promises this.
10. Domain mapping or a Cloudflare-proxied CNAME to the Cloud Run URL.

## Cloudflare checklist

1. Domain on Cloudflare (final domain BEFORE the vote opens — DEC-04), DNS proxied, Full
   (strict) TLS.
2. **Cache rules** (order matters):
   - BYPASS: `/vote*`, `/register*`, `/r/*`, `/invite/*`, `/staff*`, `/healthz`, `/internal/*`, `/beacon/*`
   - Cache 1 y immutable: `/static/*` — explicitly include `.glb .ktx2 .woff2` (not cached by default)
   - Edge TTL 10 s: `/api/bracket/*`
   - Edge TTL 60 s: `/` and other content pages (respect origin Cache-Control)
3. **Rate limiting**: POST `/vote/` 10/min/IP → managed challenge; POST `/register/*`
   5/min/IP → managed challenge; `/staff/` login 5/min/IP → block 10 min;
   POST `/beacon/*` 6/min/IP → block (keeps the anonymous 3D counters honest).
   The app has its own registration limits too (registration/abuse.py, `REG_*` settings)
   — they hold even if an edge rule is missing.
4. **Turnstile**: create one widget covering the domain; site key → env `TURNSTILE_SITE_KEY`,
   secret → Secret Manager. Both the vote and the registration form use it.
5. **Origin shield** (security review 2026-10-22, M1): generate a secret (`openssl rand -hex 32`)
   → Transform Rule (Modify Request Header) adding `X-Origin-Token: <value>` to **all** proxied
   requests → store the same value as Secret Manager secret `cf-origin-token`, set it on the
   service as `CF_ORIGIN_TOKEN`, and add it as GitHub Actions secret `CF_ORIGIN_TOKEN` (the
   deploy smoke test sends it). From then on direct hits on the `*.run.app` URL get 403
   (core/middleware.py) — except `/healthz` and `/internal/` — and CF-Connecting-IP becomes
   trustworthy for the vote's per-IP limits.
6. **Security headers** (Response Header Transform Rule) — set
   `Content-Security-Policy: default-src 'self'; script-src 'self' 'wasm-unsafe-eval' https://challenges.cloudflare.com; frame-src https://challenges.cloudflare.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' blob:; worker-src 'self' blob:; base-uri 'none'; form-action 'self'; frame-ancestors 'none'`.
   All site scripts are external files, so `script-src 'self'` holds; `'unsafe-inline'` styles
   are required by the current templates; Turnstile needs the two cloudflare.com entries.
   The 3D hero needs the rest: `'wasm-unsafe-eval'` because the meshopt decoder that unpacks
   the model is WebAssembly (it permits compiling WebAssembly only, not `eval()`),
   `worker-src blob:` for the decoder's worker, and `blob:` in `img-src` and `connect-src`
   because the model's embedded textures are handed to the browser as `blob:` URLs. Without
   them the scene fails and every visitor silently gets the poster — after changing the rule,
   open the home page with the browser console open and check there are no CSP errors.
   The app sends the same policy itself (core/middleware.py `SecurityHeadersMiddleware`,
   production only, first in the middleware list so redirects and 403s carry it too) unless
   the response already carries one, so a missing edge rule is not a gap. **Keep the two
   identical** — a test compares this line with the app's policy.
7. Verify with `curl -I`: `cf-cache-status: HIT` on static + content pages, `BYPASS`/`DYNAMIC`
   on forms; **no `Set-Cookie` on cached responses**; a request to the `*.run.app` URL
   (not via the domain) returns 403.
8. Residency note: Cloudflare terminates TLS and proxies form submissions → it is a data
   processor. Acceptable under the current assumption; if strict localization is confirmed,
   move the BYPASS (personal-data) routes to a direct in-region path and keep Cloudflare for
   static only.

## Deploy pipeline

`.github/workflows/deploy.yml` — runs when **CI succeeds on `main`** (or manually: Actions →
Deploy → *Run workflow* → staging/production):

checkout the commit CI tested → keyless auth (Workload Identity Federation) → build image →
push to Artifact Registry → `gcloud run jobs update/execute <service>-migrate` (migrations as a
job, never at boot) → `gcloud run deploy <service> --image …` (only the image changes) → smoke
test `/healthz` and `/` → on failure the job summary prints the exact rollback command:

```
gcloud run services update-traffic esports --region me-central2 --to-revisions PREV=100
```

The workflow is **dormant until `GCP_PROJECT_ID` is set** (all jobs skipped). Rehearse one
rollback on staging before the vote opens.

### Deploy setup (one time, after DEC-05 — ~30 min)

Variables used below: `P=esports2-prod`, `R=me-central2`, `ORG=YourVision-KSA`,
`REPO=esports2-website`, `N=$(gcloud projects describe $P --format='value(projectNumber)')`.

1. **Artifact Registry**: `gcloud artifacts repositories create esports --repository-format=docker --location=$R`
2. **Service accounts**
   - runtime: `gcloud iam service-accounts create esports-run` → roles `roles/cloudsql.client`,
     `roles/secretmanager.secretAccessor`
   - deployer: `gcloud iam service-accounts create esports-deploy` → roles `roles/run.admin`,
     `roles/artifactregistry.writer`, and `roles/iam.serviceAccountUser` **on esports-run only**
3. **Secrets** (Secret Manager): `secret-key`, `database-url`, `signals-salt`, `turnstile-secret`,
   `internal-token`, `cf-origin-token`, `email-host-password` — generated once, never in the
   repo or image. `cf-origin-token` is the origin-shield value (Cloudflare checklist step 5);
   step 4 below mounts it, so the first deploy fails if the secret does not exist yet.
4. **Service** (first deploy by hand, from any built image; later deploys only swap the image):
   ```
   gcloud run deploy esports --region $R --image $R-docker.pkg.dev/$P/esports/web:<sha> \
     --service-account esports-run@$P.iam.gserviceaccount.com \
     --add-cloudsql-instances $P:$R:esports-db \
     --set-secrets SECRET_KEY=secret-key:latest,DATABASE_URL=database-url:latest,SIGNALS_SALT=signals-salt:latest,TURNSTILE_SECRET=turnstile-secret:latest,INTERNAL_TOKEN=internal-token:latest,CF_ORIGIN_TOKEN=cf-origin-token:latest,EMAIL_HOST_PASSWORD=email-host-password:latest \
     --set-env-vars ALLOWED_HOSTS=<domain>,<service>.run.app,CSRF_TRUSTED_ORIGINS=https://<domain>,SITE_BASE_URL=https://<domain>,TURNSTILE_SITE_KEY=<key>,EMAIL_HOST=<smtp>,EMAIL_HOST_USER=<user>,DEFAULT_FROM_EMAIL=<from> \
     --min-instances 0 --max-instances 4 --concurrency 40 --cpu 1 --memory 512Mi --allow-unauthenticated
   ```
   `ALLOWED_HOSTS` **must include the `*.run.app` host** or the smoke test gets 400. Add the
   startup probe on `/healthz` (console → Edit → Container → Health checks).
5. **Migration job** (same image, same secrets/SQL/SA as the service):
   `gcloud run jobs create esports-migrate --region $R --image <same> --command python --args manage.py,migrate,--noinput`
   + the same `--service-account`, `--set-cloudsql-instances`, `--set-secrets`, `--set-env-vars`.
6. **Workload Identity Federation** (keyless GitHub → GCP):
   ```
   gcloud iam workload-identity-pools create github --location=global
   gcloud iam workload-identity-pools providers create-oidc github-oidc --location=global \
     --workload-identity-pool=github --issuer-uri=https://token.actions.githubusercontent.com \
     --attribute-mapping=google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref \
     --attribute-condition="assertion.repository=='$ORG/$REPO' && assertion.ref=='refs/heads/main'"
   gcloud iam service-accounts add-iam-policy-binding esports-deploy@$P.iam.gserviceaccount.com \
     --role=roles/iam.workloadIdentityUser \
     --member="principalSet://iam.googleapis.com/projects/$N/locations/global/workloadIdentityPools/github/attribute.repository/$ORG/$REPO"
   ```
7. **GitHub** (repo → Settings → Secrets and variables → Actions → *Variables*):
   `GCP_PROJECT_ID=$P` · `GCP_WIF_PROVIDER=projects/$N/locations/global/workloadIdentityPools/github/providers/github-oidc`
   · `GCP_DEPLOY_SA=esports-deploy@$P.iam.gserviceaccount.com`.
   Secrets: `CF_ORIGIN_TOKEN` (same value as the origin shield, Cloudflare checklist step 5).
   Environments → create `production` **with required reviewers** (the manual approval gate is
   NOT optional — without it a `workflow_dispatch` ships to production unreviewed; security
   review 2026-10-22, M2) and `staging`. The WIF condition above (main-only) is the second
   half of that control: tokens are only issued to workflows running on `main`.
8. **Staging**: repeat 4–5 as `esports-staging` / `esports-staging-migrate` against the staging
   database; deploy it with *Run workflow → staging*. If staging is not behind Cloudflare
   (`ALLOW_NO_ORIGIN_SHIELD=True` instead of `CF_ORIGIN_TOKEN`), also raise the `REG_*`
   limits there — see "Registration abuse" below.
9. **Verify**: push a docs-only commit to `main` → CI → Deploy → green smoke test; then rehearse
   the rollback command on staging.

## Monitoring & alerts (GCP built-ins only)

- Uptime check on `/healthz` every minute → email alert to the team.
- **Error Reporting** (enable the API — zero code, parses Python tracebacks from Cloud Run
  logs automatically) + a log-based alert on `severity>=ERROR` → email. This catches
  unhandled 500s and permanently-failed outbox emails (core/outbox.py logs those at ERROR)
  the moment they happen, before any threshold trips.
- Alerts: 5xx rate > 2% over 5 min; p95 latency > 2 s on `/vote/` or `/register/`;
  Cloud SQL connections > 80%; Cloud Run instance count at max for > 10 min.
- Daily during active phases: admin → Outbox emails filtered on `failed` (VIP invitations
  and manage-link emails that gave up after 5 attempts need manual follow-up).
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
staging); waitlist cap set; **`python manage.py check_privacy` prints "complete"** — while
the privacy notice has [placeholders] the app keeps registration closed, the home page
shows no Register links, and the SiteConfig admin refuses to set or change the
registration date (other fields can still be saved — core/privacy.py); a dry-run registration + withdraw +
promotion on staging; export CSV works; Turnstile widget visible on the form.

**Registration abuse (runbook):** the form has Turnstile plus app-side limits per client
IP, per device (IP + browser) and per phone number (registration/abuse.py, `REG_*`
settings; a refused request gets HTTP 429 and REG-RATE-LIMITED).

| Setting (env var) | Default | Counts |
|---|---|---|
| `REG_IP_ATTEMPTS_PER_10MIN` | 60 | form submissions from one network address in 10 minutes |
| `REG_IP_REGISTRATIONS_PER_DAY` | 36 | successful registrations from one network address in 24 h |
| `REG_DEVICE_REGISTRATIONS_PER_DAY` | 12 | successful registrations from one address + browser in 24 h |
| `REG_PHONE_ATTEMPTS_PER_DAY` | 5 | submissions naming one phone number in 24 h (only those that passed Turnstile, so a script cannot lock out someone else's number) |

Why these numbers: most players register from the university network, and a campus
leaves the internet through **one shared address** — to the app, the whole campus is one
"client". A "device" is only that address plus the browser's user-agent text, which is
**identical for every phone of the same model and OS version**, so it cannot tell two
students apart. Tighter limits (the first version had 20 / 10 / 3) would have refused
real students on launch day. The defaults let half of all 72 places come from one network
in a day and a dozen from one phone model, and still stop a script from taking
everything; Turnstile and the Cloudflare rate rule are the finer controls. If real
players report REG-RATE-LIMITED on launch day, raise the matching `REG_*` variable on the
service (`gcloud run services update esports --update-env-vars REG_…=…`) — no deploy needed.

**Staging without Cloudflare** (`ALLOW_NO_ORIGIN_SHIELD=True`): the app then cannot see
visitors' real addresses and may see **every visitor as the same address**, so all testers
share one allowance. Raise the limits on that service before a rehearsal (e.g.
`REG_IP_ATTEMPTS_PER_10MIN=1000`, `REG_IP_REGISTRATIONS_PER_DAY=500`,
`REG_DEVICE_REGISTRATIONS_PER_DAY=500`), or the seat-race and dry-run rehearsals stop with
429 after a few registrations. Never copy those values to production.

Phone numbers are NOT
verified (no SMS provider — management decision DEC-16), so expect two failure modes:
- *A scripted wave of fake sign-ups*: admin → Registrations → the **network** column shows
  a hash prefix of the client IP each registration came from; search for it (or filter by
  date), select the fakes → action **Remove selected registrations** → give a reason. All
  selected rows are removed first, then free seats are filled from the waitlist in order
  (fakes on the waitlist are never promoted); every removal/promotion is in the AuditLog.
  Tighten `REG_*` or the Cloudflare rule if it continues.
- *Someone registered another person's number* (the owner gets "already registered"):
  verify the caller, then admin → Players → search the number → action **Release phone
  number** → reason. The squatter's registration is removed (waitlist promotes), their
  manage link stops working, and the owner can register normally and gets their own link.
Before the draw, staff review the confirmed list for obvious fakes.

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
3. At the published retention deadline: run the PII purge command
   `python manage.py purge_pii --yes` (data-model.md → Retention; it refuses unless the
   site is archived — step 1); delete `SIGNALS_SALT`.
4. Final DB dump to the organizer's encrypted storage (per retention policy), then delete:
   Cloud Run services, Cloud SQL instance **and its backups**, Artifact Registry images,
   Scheduler jobs, secrets. Downgrade/close the billing account before trial end if nothing
   remains.
5. Optional: export the archive page as static HTML and host it free (e.g. the organizer's
   site) so the URL survives; then delete the GCP project entirely.

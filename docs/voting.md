# Voting — Anti-Abuse Specification

Security-critical. The vote is **open to everyone, unverified, and advisory**. The owner
accepted the residual risk below. Goal: make casual and scripted abuse expensive and
detectable, never claim it is a verified election.

## Ballot flow

1. GET `/vote/`: if the browser has no voter-token cookie, generate one (128-bit random),
   set as a **signed, HttpOnly, Secure, SameSite=Lax cookie** (Django signing), expiry =
   14 days — covers the ≤7-day window plus margin (`COOKIE_MAX_AGE` in voting/views.py;
   the privacy notice states the same 14 days). Render the form (candidate games, pick
   `CHOICES_PER_BALLOT`) + Turnstile.
2. POST: verify in this order, cheapest first:
   a. phase == vote (else 403);
   b. form valid (exact number of choices, all `candidate` games);
   c. voter token present and signature valid (else re-issue and ask to resubmit — one retry);
   d. **Turnstile server-side verification** (siteverify call, ~1s budget, 2s timeout);
   e. insert Ballot inside a transaction — the **unique `token_hash`** turns a duplicate into
      an IntegrityError → friendly "لقد شاركت في التصويت مسبقًا" page.
3. Classification (synchronous, cheap checks only) sets status `counted` or `held`:

| Signal | Action |
|---|---|
| Turnstile failed / timeout / unreachable | **held** (never reject — except keep the error page honest: "تم استلام صوتك وسيُراجع") |
| ASN in datacenter/hosting/VPN list (static list shipped in repo, updatable) | held |
| > N ballots from same `ip_hash` in 1 h (default N=5 — campus/carrier NAT means SOFT handling: hold, don't block) | held |
| > M ballots from same `ua_hash`+`ip_hash` in 10 min (default M=3) | held |
| Proof-of-work token missing/invalid (if enabled, see below) | held |
| Everything clean | counted |

`held` is a review bucket, not a rejection: the voter sees the same success page. Staff can
move held→counted or →invalidated in admin (bulk actions, each audit-logged).

## Rate limiting (defense in depth)

- **Edge (Cloudflare rules):** `/vote/` POST: max 10/min per IP; challenge above that.
  `/staff/` login: 5/min per IP.
- **App:** the per-ip_hash counters above (plain SQL count on an indexed column — no Redis).

## Optional proof-of-work (enable only if abuse observed)

A small JS computation (e.g. find a nonce such that SHA-256(server_challenge+nonce) has k
leading zero bits, k≈18 → ~1 s on a phone) submitted with the form, verified server-side.
Ship behind a settings flag, default OFF. It raises the cost of mass scripting; it is not a
substitute for Turnstile.

## Burst detection (during the window)

Staff/ops checks, run as admin-visible queries or a management command (`manage.py vote_report`),
at least twice daily during the vote:
- ballots per hour (total, counted, held) — the **held share** is the headline metric
  (alert if > 20%);
- top 20 `ip_hash` by ballot count; top ASNs; counted-ballot timing histogram (bot bursts are
  spiky and uniform);
- choice distribution shifts correlated with bursts.
Staff can invalidate a cluster (by ip_hash/ASN/time slice) via a bulk admin action; every
invalidation records reason + actor.

## Process rules (owner commitments)

1. **Publish the counting rules on `/vote/` BEFORE opening**: one ballot per browser; automated
   or suspicious ballots are held and may be excluded; the organizer's decision is final; the
   result is advisory input to game selection. (Arabic text: content-ar.md → VOTE-RULES, DRAFT.)
2. **Hide the live tally** during the window. Publish counted + held totals after close.
3. Keep the window short (≤ 7 days).
4. The vote's open/close datetimes are fixed in SiteConfig before opening and not extended
   mid-window except by published announcement.

## Privacy

- Store only `HMAC-SHA256(value, SIGNALS_SALT)` of IP and UA. `SIGNALS_SALT` is a secret env
  var, generated once, **deleted at end of life** (making hashes permanently unlinkable).
- No cookies on the cached public pages; the voter cookie is set only by `/vote/`.
- Strip the `signals` JSON 14 days after close (keep status, hashes, reasons for audit).
- Mention the vote data handling in the privacy notice.

## Residual risk (accepted by owner, 2026-10)

- Residential-proxy networks + paid challenge-solving can cast **thousands of
  legitimate-looking votes**; this design detects bursts and datacenter origins, not that.
- Ordinary users can vote a few times (clear cookies, second device/browser).
- **Organized real-person campaigns are indistinguishable from popularity** — arguably
  legitimate for an advisory vote.
- Therefore: the result is a **credible popularity signal, not a defensible binding election**.
  If the organizers or the Federation later declare it binding, identity verification (phone
  OTP or university email) must be added **before the vote opens** — ballots cannot be
  verified retroactively. That decision is closed once the vote opens.

## Ops checklist for the vote window

- [ ] Counting rules published on `/vote/`
- [ ] Turnstile keys set (prod site key, not test keys)
- [ ] Edge rate rules active; `/vote/` confirmed BYPASS in cache (check response headers)
- [ ] held-share alert threshold configured; `vote_report` scheduled twice daily
- [ ] SiteConfig datetimes verified in Asia/Riyadh **and** rendered correctly on the page
- [ ] min-instances=1 for the first 24 h; DB connections dashboard open at launch hour
- [ ] Rehearsed: cast ballot, duplicate ballot, held ballot (via VPN), bulk invalidate on staging data

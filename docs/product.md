# Product Brief — E-SPORTS 2 Website

Last updated: 2026-10-20. Open decisions are tracked as DEC-xx in `docs/plan.md`.

## 1. The event (FACTS)

- Name/branding: تجمع الرياضات الإلكترونية – Arab Open University ("E-SPORTS 2").
  The public site title keeps the prototype's name: **يوم الرياضات الإلكترونية** unless the
  owner renames it (DEC-02).
- Organizer: Your Vision KSA. Venue: Arab Open University, Riyadh (finals day); first two
  days possibly at an external venue or online with streams.
- Date: late November or early December 2026 — **not final** (DEC-01). Planning assumes
  Nov 26–28; later dates add slack.
- Format: **3 games**, each a **1v1 single-elimination** bracket of **16 players**
  (15 matches per game, 45 total), over **3 days**, finals at the university.
- Candidate games include Rocket League, FIFA (EA Sports FC), Call of Duty; the final list is
  decided by the **public vote** (candidate list: DEC-03). Permits for the chosen games are
  obtained after the vote closes.
- Saudi Esports Federation involvement planned; VIP invitations will be sent.
- Sponsorship tiers (offline sales, no online payment): Diamond 150,000 · Gold 100,000 ·
  Silver 50,000 · Participant 30,000 SAR.
- One edition only. No reuse for future events. Planned end of life (see docs/operations.md).

## 1b. Design and prototype status

- `reference/prototype.html` is the **content reference only**: its Arabic text and event
  information (extracted verbatim into docs/content-ar.md). **Do not copy its code, colors,
  fonts or layout** — its visual design is no longer the reference.
- The visual design comes from a new **/design artifact (DEC-15, pending)**; once produced,
  it becomes the design reference and docs/frontend.md records its tokens, fonts and 3D specs.
- Fixed product requirements regardless of design: **Arabic-first RTL · gaming style ·
  interactive 3D scenes.** (This replaces the earlier locked constraint "keep the prototype's
  visual identity".)

## 2. Actors

| Actor | Access | What they do |
|---|---|---|
| Visitor | public | Browse content, watch streams, view brackets |
| Voter | public + signed token | Cast one ballot in the game vote |
| Player | public + secret manage link | Register for exactly one tournament, view status, withdraw |
| Admin | staff login + 2FA | Everything: config, exports, invalidations, invitations |
| Referee | staff login + 2FA | Enter and correct match results |
| Door staff | staff login + 2FA | Scan VIP QR codes, check guests in |

**No player or voter accounts.** Players are identified by a secret link; voters by a signed
browser token.

## 3. Scope (owner's decisions, 2026-10)

BUILD: public voting · registration with seat cap · waitlist · live bracket · result entry ·
VIP invitations with QR check-in · VIP confirmation/reminder emails · content pages.

NOT BUILT: content admin/CMS (content edited in code) · player notifications beyond the
registration-confirmation page and manage link · payments · player accounts · English version
· native app · self-hosted streaming (links/embeds only) · remote check-in or self-reported
results (assumed; DEC-10 if online play changes this).

## 4. Site phases

The site moves through phases, switched by configured datetimes (Asia/Riyadh) and **enforced
server-side on every request** (see docs/data-model.md → Phase).

1. **pre** — teaser content; vote announced.
2. **vote** — ballot open. Live tally hidden.
3. **permits** — vote closed; counted + held totals published; "registration opens on …".
4. **registration** — per-game registration with seat cap + waitlist.
5. **event** — registration closed; brackets live; check-in active; stream links shown.
6. **archive** — frozen results, winners, sponsors; all forms disabled; PII deleted after the
   retention period.

Phases are strictly sequential; their busy windows never overlap (this is a core architecture
assumption).

## 5. Product rules

- **One tournament per player** (changed 2026-10-20 from "max 2"). Enforced by a database
  constraint: one active registration per player across all games.
- Seats: 16 per game. First come, first served; **no overbooking ever**.
- Waitlist: FIFO per game, promoted automatically on withdrawal/removal. Cap per game:
  suggested 8 (DEC-07).
- Vote: open to everyone, no identity verification, **advisory** result. Anti-abuse per
  docs/voting.md. Counting rules published before the vote opens.
- Event rules shown on site (keep Arabic text verbatim from docs/content-ar.md): arrive 15
  minutes before your match or forfeit · referee decisions final · players may bring their own
  controller/headset · sportsmanship required; abuse = disqualification · no cheating tools.
  (The old "max two tournaments" rule text must be REPLACED — see content-ar.md.)
- VIP QR: unguessable single-use token; door staff see the guest's name for an ID check.
- Spectator zones (free play, VR, retro, exhibits) are content-only — no booking system.

## 6. Personal data (PDPL)

- Collected: player full name, Saudi phone, per-game player ID(s), optional email; VIP name +
  contact; voter signal hashes (HMAC of IP/UA — never raw). **No national/iqama ID** (A6).
- Exact registration fields: DEC-08. Under-18 policy and guardian consent: DEC-09.
- Controller (Your Vision vs. university): UNKNOWN — being confirmed. Privacy notice +
  retention period (suggest 30–90 days post-event) must be live before registration opens.
- Data residency: probably not required; hosting in GCP me-central2 (Dammah/Dammam, KSA)
  hedges it either way. See docs/architecture.md → Hosting.

## 7. Standing assumptions (from the architecture review)

| ID | Assumption | Status |
|---|---|---|
| A5 | No payments | Assumed (DEC pending with owner) |
| A6 | No national/iqama ID collected | Assumed |
| A7 | Peak concurrency low thousands, mostly cached reads | Assumed |
| A9 | Streams hosted externally, linked/embedded only | Assumed |
| A10 | Arabic only at launch | Confirmed |
| — | Vote is advisory | Confirmed 2026-10 |
| — | Team: 2–4 people, Python basics, new to Django, no DevOps | Confirmed |
| — | Small budget; no idle cloud cost; credits available (GCP trial, sccc) | Confirmed |

## 8. Known conflicts to keep in mind

- The prototype page describes 4 tournaments / 1 day / 32 seats. That content is a **template**;
  the real event is 3 games / 1v1 / 16 seats / 3 days. Every prototype string that encodes the
  old format is marked REPLACE in docs/content-ar.md.
- The vote decides the games, so game names on registration/bracket pages must come from the
  database (confirmed games), never hardcoded.

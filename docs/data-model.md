# Data Model

Architectural level: entities, fields, constraints, state machines, and the transactional
rules. Field types are indicative; exact Django field choices are the implementer's call —
**the constraints are not negotiable**. App ownership in parentheses.

Conventions: every table gets `created_at`/`updated_at`; PKs are default Django bigint ids;
"active" means status in the set noted per model. All datetimes stored UTC (`USE_TZ=True`).

## Game (core)

The three (candidate, then confirmed) tournaments. Game names are DATA, not hardcoded —
the vote decides which are confirmed.

| Field | Notes |
|---|---|
| slug | unique, e.g. `rocket-league` |
| name_ar / name_en | display names (Arabic shown; English for IDs/HUD labels) |
| platform | e.g. PS5 / PC (display only) |
| status | `candidate` → `confirmed` \| `cancelled` |
| seats | default 16 |
| waitlist_cap | default 8 (DEC-07) |
| display_order | int |
| player_id_label_ar | label for the per-game player ID field (e.g. "معرّف EA") |

Registration and brackets exist only for `confirmed` games.

## Ballot + BallotChoice (voting)

One ballot per voter token. Choices per ballot = `CHOICES_PER_BALLOT` setting (DEC-03;
provisionally 3 — "pick the 3 games you want").

**Ballot**

| Field | Notes |
|---|---|
| token_hash | **unique** — HMAC-SHA256 of the voter token; the one-ballot rule |
| status | `counted` \| `held` \| `invalidated` |
| turnstile_passed | bool |
| ip_hash, ua_hash | HMAC-SHA256 with `SIGNALS_SALT`; raw values never stored |
| asn | int, nullable (from CF header/GeoIP if available) |
| signals | JSON: coarse heuristics (header anomalies, timing). No raw PII |
| held_reason / invalidated_reason | short code; set when status ≠ counted |
| invalidated_by | FK → staff user, nullable; invalidation is audit-logged |

**BallotChoice**: ballot FK, game FK, `unique(ballot, game)`. App validates count ==
CHOICES_PER_BALLOT and games are `candidate`.

State machine: `counted ↔ held` (staff review, logged) → `invalidated` (terminal, logged).
Tallies are computed queries over `status=counted` — never stored counters.

## Player + Registration (registration)

**Player**

| Field | Notes |
|---|---|
| full_name | required |
| phone | required, normalized `+9665XXXXXXXX`; **unique** (one player identity per phone) |
| email | optional; if given, the manage link is also emailed via OutboxEmail at registration |
| manage_token | **unique**, ≥128-bit urlsafe random; the secret manage link. Store a hash if feasible; minimum bar: unguessable + never logged |
| consent_at | datetime; privacy-notice consent checkbox timestamp |
| (age/guardian fields) | pending DEC-09 — leave out until decided |

**Registration**

| Field | Notes |
|---|---|
| player FK, game FK | |
| status | `confirmed` \| `waitlisted` \| `withdrawn` \| `removed` |
| waitlist_position | int, nullable; dense FIFO order among waitlisted of that game |
| game_player_id | the per-game ID (EA ID / Activision ID / Epic ID) — lives here, not on Player |
| promoted_at / withdrawn_at | datetimes, nullable |

Constraints:
- **One tournament per player**: partial unique index on `player` WHERE
  `status IN ('confirmed','waitlisted')`.
- `unique(player, game)` overall (no re-register after withdrawal without staff help; keeps
  history clean).

**Seat-claim transaction (the seat race)** — the critical path:
```
BEGIN;
  SELECT ... FROM game WHERE id=? FOR UPDATE;           -- serialize per game
  n_confirmed = COUNT(registrations WHERE game=?, status='confirmed')
  IF n_confirmed < game.seats:        status='confirmed'
  ELIF n_waitlisted < waitlist_cap:   status='waitlisted', position=n_waitlisted+1
  ELSE:                               reject ("اكتملت المقاعد")
  INSERT registration;                 -- partial unique index backstops the one-tournament rule
  IF player.email IS NOT NULL:
    INSERT outboxemail (manage-link message, EMAIL-MANAGE-* in content-ar.md)  -- same transaction
COMMIT;
```
**Waitlist promotion** (on withdraw/remove of a confirmed seat): same `FOR UPDATE` on the game
row → promote lowest `waitlist_position` to `confirmed`, decrement positions above it, audit-log.
Promotion is manual-notification only (no player emails in scope): admin sees promotions in
the admin list and contacts the player.

State machine: `confirmed → withdrawn|removed`; `waitlisted → confirmed (promotion) |
withdrawn | removed`. Registrations freeze when the phase leaves `registration`.

## Match (bracket)

Fixed single-elimination tree of 15 matches per game, created at draw time.

| Field | Notes |
|---|---|
| game FK | |
| round | 1=round-of-16 … 4=final |
| slot | position within round (1..8, 1..4, 1..2, 1) |
| player1 FK / player2 FK | nullable until fed |
| winner FK | nullable; must equal player1 or player2 (DB CHECK) |
| score_text | free text, e.g. "3–1" (referee-entered; no per-game score schema) |
| status | `pending` → `done` \| `forfeit` |
| next_match FK + next_slot (1|2) | where the winner advances; null for the final |

Constraints: `unique(game, round, slot)`.

**Result-entry transaction**: lock the match row → set winner/score/status → write winner into
`next_match.playerN` → AuditLog(before/after). Correcting a result (admin only): reverse
downstream propagation only if downstream matches are still `pending`; otherwise refuse and
require manual admin intervention (log the attempt).

**Draw**: when registration closes, a management command seeds matches from confirmed
registrations by **random draw** (seedable RNG, logged). 16 confirmed required; if fewer,
byes fill from the top (status `forfeit` with the lone player as winner).

## Invitation (invitations)

| Field | Notes |
|---|---|
| guest_name, organization | shown to door staff for ID check |
| contact_email / contact_phone | at least one |
| token | **unique**, ≥128-bit urlsafe random; QR encodes `https://<domain>/invite/<token>` |
| status | `created` → `sent` → `checked_in` \| `revoked` |
| sent_at / checked_in_at | datetimes |
| checked_in_by | FK → staff user |

**Single-use check-in** (atomic, race-safe):
`UPDATE invitation SET status='checked_in', checked_in_at=now(), checked_in_by=?
 WHERE token=? AND status='sent'` — exactly one concurrent scan wins (rowcount 1); the other
sees "already checked in at HH:MM by X".

## OutboxEmail (core)

| Field | Notes |
|---|---|
| to_email, subject, body_text | plain text; Arabic body from content-ar.md |
| status | `queued` → `sent` \| `failed` |
| attempts, next_attempt_at, last_error | retry with backoff, max 5 attempts |

Delivery: Cloud Scheduler hits an authenticated endpoint → worker selects
`FOR UPDATE SKIP LOCKED` rows due for sending → SMTP via the organizer's mail domain.
Senders never send inline — they **insert a row**: VIP invitation confirmations/reminders, and
the registration manage-link email (only when the player provided an email).

## SiteConfig (core) — the phase switch

Singleton row: `vote_opens_at, vote_closes_at, registration_opens_at,
registration_closes_at, event_start_date, event_end_date, archived (bool)`, plus
`stream_url_1..3` (nullable). `current_phase()` derives the phase from now() vs. these fields
and is checked **in every form view** (GET shows closed-state message, POST returns 403).
Editable only in Django admin; every change audit-logged.

## AuditLog (core)

`actor FK (nullable=system), action (slug), model, object_id, before JSON, after JSON,
created_at`. Written for: result entry/correction, ballot hold/invalidate, registration
remove/promote, invitation revoke/check-in reversal, SiteConfig changes, **every PII export**.
Append-only: no update/delete paths in app code; excluded from admin editing.

## Retention

- Raw ballot `signals`: strip 14 days after the vote closes (keep status + hashes for audit).
- Player, Registration (PII fields), Invitation contacts, OutboxEmail: delete at the published
  retention deadline (30–90 days post-event, DEC-08). Keep: anonymized results (gamer tags
  only, if the privacy notice says so — DEC-08), Game, Match (winner names replaced per
  notice), AuditLog with actor=staff only.

# Entry badges with QR check-in — design (2026-11-24)

**Intent.** Hussein (2026-11-24): badges for **players and VIP guests only**, each with a QR
scanned at the door for entry. Ordinary visitors get nothing (no visitor registration exists,
by design). This gives door staff one scan flow for everyone who is allowed through the gate.

**Goals.** Print-ready Arabic RTL badge pages for (a) players with a confirmed seat and
(b) VIP invitees; door check-in for players that is race-safe and single-use, exactly like
the existing VIP check-in; one scanner page handling both QR kinds.

**Non-goals / anti-goals.** No visitor badges. No player accounts (hard rule 4 stands; the
badge rides the existing manage link). No PDF generation dependency — the browser's print
dialog renders the badge (no new dependencies, hard rule 5). No change to the working VIP
check-in machinery. Check-in stays an attendance record; it does not gate bracket play.

**Approaches considered.**
1. *Extend the proven VIP pattern to players* (chosen, Hussein 2026-11-24): new
   single-purpose player check-in token, badge pages on existing routes, the existing
   `/staff/checkin/` page learns to resolve both token kinds.
2. *Unified "Pass" model for players + VIPs* — rejected: refactors the audited, tested VIP
   check-in weeks before the event for no user-visible gain.
3. *Reuse the manage token in the player QR* — rejected on security grounds: the manage link
   can withdraw the player; a badge is shown to door staff and cameras, so it must carry a
   token that can do nothing but mark attendance.

## Decisions

- **Player check-in token**: `Player.checkin_token` — 128-bit `secrets.token_urlsafe(24)`,
  stored in plain like `Invitation.token` (it is not a credential over data; single purpose).
  Plus `checked_in_at` / `checked_in_by` on `Player` (mirror of `Invitation`).
- **Player QR encodes the bare token** (no URL): scanning it with a phone yields an opaque
  string, nothing to visit; the staff scanner feeds the raw text to lookup, which already
  strips URLs (`_token_from`).
- **Check-in rule**: a player checks in once (single conditional UPDATE, exactly one
  concurrent scan wins), and only while they hold a **CONFIRMED** registration. Waitlisted,
  withdrawn, removed → INVALID at the door. Admin can reverse a mistaken check-in
  (mirror of `undo_checkin`), audited.
- **Badge pages** (both `never_cache`, BYPASS):
  - Player: `/r/<manage_token>/badge/` — same phase window as the manage page
    (registration..event), 404 unless the registration is CONFIRMED.
  - VIP: `/invite/<token>/badge/` — same validity rules as the invite page (uniform 404).
  - Shared template `templates/badges/badge.html` + print CSS (card layout): event name,
    kind label (player/guest), person name, subtitle (game name / organization), inline-SVG
    QR, door hint, print button. Player badge shows `full_name` + `game.name_ar`;
    VIP badge shows `guest_name` + `organization`. The player badge QR is the
    **check-in token, never the manage token** (pinned by test).
- **Scanner page**: `/staff/checkin/` lookup tries Invitation by `token`, then Player by
  `checkin_token` (tokens are 128-bit random — no ambiguity). Confirm carries an explicit
  `kind` field. The guest flow is untouched; the player card shows name + game + the same
  CHECKIN_OK / CHECKIN_ALREADY / CHECKIN_INVALID strings. Same door permission
  (`invitations.checkin_invitation`) gates the page for both kinds.
- **Arabic**: all new strings go to `docs/content-ar.md` as **DRAFT — needs owner review**
  rows; existing CHECKIN_* strings are reused for players.
- **Migration**: add `checkin_token` nullable → RunPython fills existing players → alter to
  unique. `default=new_checkin_token` covers new rows.
- **Tests** (docs/testing.md style): player single-use concurrent scan (`concurrency` mark),
  status gating at the door, badge-page phase/validity/no-store, manage-token-never-in-QR,
  scanner page both kinds, admin reversal re-arms the QR.

**Left to the builder:** exact badge markup/CSS within the site's existing theme tokens;
admin list/readonly details.

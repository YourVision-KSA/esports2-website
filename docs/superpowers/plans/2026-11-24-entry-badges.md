# Entry Badges + Player QR Check-in Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Print-ready entry badges (players + VIP guests) with QR codes, and race-safe single-use player check-in on the existing door-staff scanner page.

**Architecture:** Mirror the audited VIP check-in pattern onto `Player` (single-purpose plain token, conditional-UPDATE check-in, audit rows). Badges are server-rendered print pages sharing one template; the player QR carries the bare check-in token, never the manage secret. `/staff/checkin/` resolves both token kinds; the guest flow is untouched.

**Tech Stack:** Django 5.2 LTS, existing `qrcode` (SvgPathImage) dependency, pytest(-django), real Postgres for `concurrency` marks.

**Spec:** `docs/superpowers/specs/2026-11-24-entry-badges-design.md`

## Global Constraints

- Arabic user-facing strings come from `docs/content-ar.md` exactly; every NEW string is added there first as a `DRAFT — needs owner review` row, then mirrored into `core/content.py` `CONTENT` (dash key → underscore key).
- No new dependencies. No player accounts. Raw IP/UA never stored. Times: UTC store, Asia/Riyadh display.
- Manage token never appears in badge markup or QR (security: it can withdraw the player).
- Badge/manage/invite routes are BYPASS: `@never_cache` on every new view.
- Uniform 404 for unknown/invalid tokens — no token-validity oracle.
- Repo is public: no real names, prices or secrets in fixtures or docs.
- Lint: `ruff check . && ruff format .` must pass; suite: `pytest` (279 green before this work).

## Review Focus

1. Door scans a player badge whose player withdrew after printing → INVALID, never OK (test in Task 1).
2. Two door devices scan the same player QR at once → exactly one OK, other ALREADY with time+actor (test in Task 1).
3. Badge page hit during `pre`/`vote`/`permits` phases or with a wrong token → uniform 404, no distinguishable body (test in Task 2).
4. Player badge HTML containing the manage token anywhere (href, QR, hidden input) → pinned to never happen (test in Task 2).
5. Scanner lookup with a player token during a VIP-only mental model: template must render the player card with game name, not the guest card fields (test in Task 4).

---

### Task 1: Player check-in model fields + service

**Files:**
- Modify: `registration/models.py` (Player: 3 fields + `new_checkin_token`)
- Create: `registration/migrations/0004_player_checkin.py`
- Modify: `registration/services.py` (check_in, undo_checkin)
- Test: `registration/tests/test_checkin.py`

**Interfaces:**
- Produces: `Player.checkin_token: str` (unique, default `new_checkin_token`), `Player.checked_in_at`, `Player.checked_in_by`; `registration.services.check_in(token: str, actor) -> tuple[str, Player | None]` and `registration.services.undo_checkin(player, actor) -> Player | None`; results reuse `invitations.services.CheckInResult` constants (`OK`/`ALREADY`/`INVALID`).

- [ ] **Step 1: Write failing tests** in `registration/tests/test_checkin.py`:
  - `test_checkin_marks_confirmed_player` — confirmed registration; `check_in(token, staff)` → `(OK, player)`, `checked_in_at` set, `checked_in_by == staff`, one audit row `player.checkin`.
  - `test_checkin_requires_confirmed_registration` — waitlisted, withdrawn, removed, and no-registration players → `(INVALID, None)`; unknown token → `(INVALID, None)`.
  - `test_checkin_already_reports_time_and_actor` — second call → `(ALREADY, player)` with original `checked_in_at`/`checked_in_by` intact.
  - `test_checkin_single_use_concurrent` (`@pytest.mark.concurrency`) — two threads, one token → exactly one OK, one ALREADY (mirror `invitations/tests/test_invitations.py` concurrency pattern).
  - `test_undo_checkin_rearms_token` — undo → fields cleared, audit `player.checkin_reversed`, then `check_in` succeeds again.
- [ ] **Step 2: Run** `pytest registration/tests/test_checkin.py -v` — FAIL (no field/service).
- [ ] **Step 3: Implement.** `new_checkin_token()` = `secrets.token_urlsafe(24)`. Fields: `checkin_token = CharField(max_length=48, unique=True, default=new_checkin_token)`, `checked_in_at = DateTimeField(null=True, blank=True)`, `checked_in_by = FK(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=SET_NULL, related_name="+")`. Migration: AddField nullable → RunPython per-row tokens → AlterField unique+default. `check_in`: conditional UPDATE `filter(checkin_token=token, checked_in_at__isnull=True, pk__in=Registration confirmed players)`; on 1 row, audit `player.checkin`; distinguish ALREADY (player exists, checked in, confirmed) from INVALID exactly like `invitations.services.check_in`. A checked-in player whose registration later left CONFIRMED still reports ALREADY only if checked in; otherwise INVALID.
- [ ] **Step 4: Run** the file — PASS; run `pytest registration/ -q` — no regressions.
- [ ] **Step 5: Commit** `feat: player check-in token and race-safe check-in service`.

### Task 2: Badge template + player badge page

**Files:**
- Create: `templates/badges/badge.html`
- Modify: `static/css/base.css` (badge card + `@media print`)
- Modify: `registration/views.py`, `registration/manage_urls.py`, `templates/registration/manage.html`
- Modify: `docs/content-ar.md`, `core/content.py`
- Test: `registration/tests/test_badge_page.py`

**Interfaces:**
- Consumes: Task 1 fields; `invitations.views._qr_svg` — move it to `core/qr.py` as `qr_svg(data: str) -> str` and re-import in invitations (one-line shim is fine).
- Produces: URL name `registration:manage-badge` at `/r/<token>/badge/`; template `badges/badge.html` context: `kind_label`, `person_name`, `subtitle`, `qr_svg`, all strings via `content.*`.

- [ ] **Step 1: Content rows.** Add DRAFT rows to `docs/content-ar.md` and mirror to `CONTENT`: `BADGE-TITLE` «بطاقة الدخول», `BADGE-PLAYER` «لاعب», `BADGE-GUEST` «ضيف», `BADGE-PRINT` «اطبع البطاقة», `BADGE-HINT` «أبرز رمز الاستجابة عند بوابة الدخول», `MANAGE-BADGE-LINK` «بطاقة الدخول». Flag as DRAFT in the final summary.
- [ ] **Step 2: Write failing tests** in `registration/tests/test_badge_page.py`:
  - `test_badge_page_for_confirmed_player` — event/registration phase → 200; body contains `full_name`, `game.name_ar`, `<svg`, `content.BADGE_TITLE`; `Cache-Control` contains `no-store`.
  - `test_badge_qr_is_checkin_token_not_manage_token` — raw manage token NOT in body; `player.checkin_token` IS (inside the QR data assert via `qrcode` decode of… simpler: assert the view passed `qr_svg(checkin_token)` by asserting the token appears nowhere in body except we can't read SVG paths — instead monkeypatch `core.qr.qr_svg` to identity-record its argument and assert it equals `checkin_token`).
  - `test_badge_404_cases` — wrong token, waitlisted player, withdrawn player, and `pre`/`vote`/`permits` phases → 404 with identical bodies to each other.
- [ ] **Step 3: Run** — FAIL.
- [ ] **Step 4: Implement.** `core/qr.py` with `qr_svg`; `views.badge(request, token)` mirrors `manage`'s phase gate + `_get_registration_or_404`, 404 unless `registration.status == CONFIRMED`; render `badges/badge.html`. Badge template: standalone print page (extends base or standalone `<html lang="ar" dir="rtl">` — standalone is simpler for print; builder's call), card ~A6, site theme tokens, print button `window.print()`, `@media print` hides the button. Manage page: show `MANAGE_BADGE_LINK` link only when status is CONFIRMED.
- [ ] **Step 5: Run** file + `pytest registration/ invitations/ -q` — PASS.
- [ ] **Step 6: Commit** `feat: print-ready player entry badge page`.

### Task 3: VIP badge page

**Files:**
- Modify: `invitations/views.py`, `invitations/urls.py`, `templates/invitations/invite.html`
- Test: `invitations/tests/test_badge_page.py`

**Interfaces:**
- Consumes: `core.qr.qr_svg`, `badges/badge.html` (kind label `content.BADGE_GUEST`, subtitle = `organization`).
- Produces: URL `/invite/<token>/badge/` (name `invite-badge`), QR data = `invitation.invite_url()` (unchanged encoding — door scanner already strips URLs).

- [ ] **Step 1: Write failing tests**: `test_vip_badge_renders` (valid token → 200, guest_name + organization + `<svg` + no-store), `test_vip_badge_404_for_unknown_and_revoked` (uniform 404), `test_invite_page_links_to_badge`.
- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement** `invite_badge(request, token)` with the same status filter as `invite`; add badge link/button on `invite.html` using `content.BADGE_PRINT`.
- [ ] **Step 4: Run** `pytest invitations/ -q` — PASS.
- [ ] **Step 5: Commit** `feat: print-ready VIP guest badge page`.

### Task 4: Door scanner handles player QRs

**Files:**
- Modify: `invitations/views.py` (`staff_checkin`), `templates/staff/checkin.html`
- Modify: `docs/content-ar.md`, `core/content.py` (row `STAFF-PLAYER-CARD` «لاعب — {game}» or equivalent label key)
- Test: `invitations/tests/test_staff_checkin_page.py` (extend)

**Interfaces:**
- Consumes: Task 1 `registration.services.check_in`; `Player.objects.filter(checkin_token=...)`.
- Produces: POST `kind=player` confirm path; context keys `player_result`, `player` alongside untouched `result`/`guest`.

- [ ] **Step 1: Write failing tests** (same style as existing ones in the file):
  - `test_lookup_player_token_shows_player_card` — lookup with a confirmed player's `checkin_token` → card with `full_name`, `game.name_ar`, confirm button with `kind=player`.
  - `test_confirm_player_checks_in` — confirm → CHECKIN_OK string, player checked in.
  - `test_lookup_waitlisted_player_is_invalid` — CHECKIN_INVALID, no card.
  - `test_guest_flow_unchanged` — existing guest lookup/confirm asserts still pass (run the file).
- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement.** In `staff_checkin`: when the token matches no Invitation, try `Player` by `checkin_token` (card requires a CONFIRMED registration for `lookup`, else INVALID; CHECKED-in → ALREADY with time/actor). Confirm with `kind=player` calls `registration.services.check_in`. Template: player card section parallel to the guest card, reusing `CHECKIN_*` strings, game name beside the player's name.
- [ ] **Step 4: Run** `pytest invitations/ -q` — PASS.
- [ ] **Step 5: Commit** `feat: door scanner checks players in by badge QR`.

### Task 5: Admin + roles guard

**Files:**
- Modify: `registration/admin.py`
- Test: extend `registration/tests/test_checkin.py` + run `invitations/tests/test_roles.py`

**Interfaces:**
- Consumes: Task 1 `undo_checkin`.

- [ ] **Step 1: Write failing tests**: `test_admin_undo_checkin_action` (admin action on a checked-in player clears fields, audits); `test_checkin_token_readonly_in_admin` (token + check-in fields in `readonly_fields`).
- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement**: PlayerAdmin: show `checked_in_at` in list, `checkin_token`/`checked_in_at`/`checked_in_by` readonly, action `undo_checkin_action` calling the service per selected row.
- [ ] **Step 4: Run** `pytest registration/ invitations/tests/test_roles.py -q` — PASS (door role gains nothing new: page permission unchanged).
- [ ] **Step 5: Commit** `feat: admin reversal for mistaken player check-ins`.

### Task 6: Docs sync + full verification + PR

**Files:**
- Modify: `docs/routes.md` (rows for `/r/<token>/badge/`, `/invite/<token>/badge/`; `/staff/checkin/` note "players + guests"), `docs/data-model.md` (Player check-in fields), `docs/testing.md` (player check-in + badge rows), `docs/tasks.md` (new ✅ entry dated 2026-11-24)

- [ ] **Step 1:** Update the four docs; keep each to the file's existing table style.
- [ ] **Step 2:** `ruff check . && ruff format .` — clean.
- [ ] **Step 3:** Full `pytest` on Postgres 5433 — expect 279 + new tests, 0 failures.
- [ ] **Step 4:** Commit docs; push branch; open PR titled "Entry badges (players + VIP) with QR door check-in" with the DRAFT-strings flag in the body; usual PR footer.
- [ ] **Step 5:** High-effort code review of the branch; fix findings; green CI; merge per the approved flow.

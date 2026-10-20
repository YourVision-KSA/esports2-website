# Testing — Required Critical Tests

The rules below are the reason this project has a backend at all. **A feature touching them is
not done until its tests pass.** Framework: pytest + pytest-django against **real PostgreSQL**
(not SQLite — the partial unique indexes and `FOR UPDATE` semantics must be the real thing).

Concurrency tests use `@pytest.mark.concurrency`, `transaction=True`, and two threads with
separate DB connections, synchronized with a barrier so both hit the critical section together.
Pattern: thread A and B both call the service function; join; assert invariants on the final DB
state. Flaky-proof by asserting invariants, not orderings.

## Voting

| Test | Assert |
|---|---|
| `test_one_ballot_per_token` | second ballot with same token → IntegrityError handled → "already voted" page; ballot count for token == 1 |
| `test_ballot_choice_count_enforced` | fewer/more than CHOICES_PER_BALLOT choices → form error, no ballot row |
| `test_choice_must_be_candidate_game` | confirmed/cancelled game id in choices → rejected |
| `test_turnstile_fail_goes_to_held` | mocked siteverify failure/timeout → ballot saved, `status=held`, voter sees success page |
| `test_datacenter_asn_held` | ASN in the list → held |
| `test_ip_burst_held` | 6th ballot within 1 h same ip_hash → held; first 5 counted |
| `test_vote_phase_gate` | POST before open / after close → 403, no row — **even with valid token + Turnstile** |
| `test_no_raw_ip_stored` | after a ballot, no column anywhere contains the request IP string |
| `test_bulk_invalidate_audited` | admin bulk action → statuses changed + one AuditLog row per ballot with actor + reason |

## Registration (the seat race)

| Test | Assert |
|---|---|
| `test_seat_race_last_seat` (concurrency) | 15 confirmed exist; 2 players claim simultaneously → exactly 1 confirmed, 1 waitlisted at position 1; never 17 confirmed |
| `test_seat_cap_never_exceeded` (concurrency) | 10 threads claim 3 remaining seats → exactly 3 confirmed, rest waitlisted in FIFO order |
| `test_one_tournament_per_player` | player with active registration registers for another game → rejected with the Arabic message; concurrency variant: 2 simultaneous registrations for different games → exactly 1 active |
| `test_same_phone_is_same_player` | second registration with same normalized phone reuses the Player row (and then hits the one-tournament rule) |
| `test_waitlist_fifo_promotion` | 3 waitlisted (pos 1,2,3); confirmed player withdraws → pos 1 becomes confirmed, others shift to 1,2; AuditLog row written |
| `test_withdraw_idempotent` | double-POST withdraw → one state change, one promotion |
| `test_waitlist_cap` | waitlist full → rejection message, no row |
| `test_registration_phase_gate` | POST outside the registration window → 403, no row |
| `test_manage_token_unguessable` | token length/entropy ≥ 128 bits; wrong token → 404 (not 403; no oracle) |
| `test_registration_email_queues_manage_link` | registration with email → exactly one OutboxEmail row containing the manage URL; without email → no row; an SMTP failure later never affects the registration itself |

## Bracket

| Test | Assert |
|---|---|
| `test_result_advances_winner` | enter result in R16 slot 1 → winner appears as player1 of the correct QF match; match `done`; AuditLog with before/after |
| `test_winner_must_be_participant` | winner id not in {player1, player2} → ValidationError/CHECK violation |
| `test_result_correction_pending_downstream` | admin corrects a result while downstream match pending → downstream slot updated, audited |
| `test_result_correction_blocked_downstream_done` | downstream already `done` → correction refused, attempt logged |
| `test_referee_cannot_edit_siteconfig` | role/permission boundaries: referee can enter results, cannot touch SiteConfig/exports |
| `test_draw_seeds_16` | draw command on 16 confirmed → 8 R16 matches, every player exactly once, deterministic under a fixed seed |
| `test_draw_with_byes` | 14 confirmed → 2 byes as forfeit wins, bracket still resolves |

## Invitations / check-in

| Test | Assert |
|---|---|
| `test_checkin_single_use_concurrent` (concurrency) | 2 simultaneous scans of one token → exactly one succeeds; other gets "already checked in" with time + actor |
| `test_checkin_requires_sent_status` | `created`/`revoked`/`checked_in` tokens cannot check in |
| `test_invite_page_uniform_404` | unknown and revoked tokens → identical 404 |
| `test_invitation_creates_outbox_row` | creating + marking sent queues the email; SMTP failure leaves status `queued`/`failed` with retry scheduled; invitation unaffected |
| `test_outbox_skip_locked` | two workers tick simultaneously → each email sent once |

## Phases & misc

| Test | Assert |
|---|---|
| `test_phase_derivation` | `current_phase()` for datetimes around each boundary (incl. exactly-at-boundary) in Asia/Riyadh |
| `test_scheduler_not_authoritative` | with scheduler never fired, forms still close at the configured time |
| `test_cached_pages_set_no_cookies` | GET `/`, `/bracket/...` responses: correct Cache-Control, **no Set-Cookie, no CSRF token in body** |
| `test_bypass_pages_no_store` | `/vote/`, `/register/...`, `/r/...`: `Cache-Control: no-store` |
| `test_export_audit_logged` | admin CSV export writes an AuditLog row |
| `test_pii_purge_command` | end-of-life command removes PII per the retention spec in data-model.md, keeps results/audit |

## CI (GitHub Actions)

- Job 1: ruff check + format check.
- Job 2: pytest with a `postgres:16` service container; run full suite including concurrency
  marks. Fail the build on any failure.
- Job 3 (later): `npm run build` + budget check (bundle gzip size ≤ 250 KB, fail if over).
- Runs on every push/PR to `main`. Deploy workflow (operations.md) requires green CI.

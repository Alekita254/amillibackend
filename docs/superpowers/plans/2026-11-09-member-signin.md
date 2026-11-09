# Member Sign-in Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Passwordless email sign-in for applicants (mentors and mentees) and a "My cohort" page showing their own status, mentor or mentees, and editable profile.

**Architecture:** A hashed, single-use `LoginLink` is emailed; redeeming it finds or creates a non-staff `User` and returns the same JWT payload the admin login does (30-day refresh). `members/me/` computes everything from `CohortMembership` rows matched by the user's email. The React app gets three pages, navbar changes and an admin guard.

**Tech Stack:** Django 6.1 / DRF 3.18 / SimpleJWT (backend, `backend/backend/cohorts`), React 19 + TypeScript + Vite + shadcn/Tailwind (frontend, `fronted/src`). No frontend test runner: frontend tasks are verified with `tsc`, ESLint, a production build, and a headless-Chrome run against a mocked API (scripts are throwaway, kept outside the repo).

**Spec:** `backend/docs/superpowers/specs/2026-11-09-member-signin-design.md` (repo `backend`). Builds on `2026-11-08-cohort-workflow-design.md`.

## Global Constraints

- Backend tests: `cd backend/backend && DJANGO_SECRET_KEY=t <venv2>/bin/python manage.py test` where `<venv2>` is `/tmp/claude-1001/-home-devmurimi-SIL-sil-util-01/ee367b31-0f00-4a2d-a397-79ad7522fcaa/scratchpad/venv2`. Currently 50 tests pass; keep them passing.
- All responses use `api.utils.custom_response(success, message, data, status_code)`; errors use `api.utils.error_response(exc)` (shape `{success:false, message, data}`).
- Token: `secrets.token_urlsafe(32)`; only its SHA-256 hex is stored. Link TTL 15 minutes, cooldown 60 seconds per email, refresh lifetime 30 days.
- The request endpoint's 200 body is identical for every email: message `"If you've applied to a cohort, we've emailed you a sign-in link."`. Invalid/expired/used verify message: `"This sign-in link has expired or was already used. Request a new one."`.
- A link never signs in a user who is `is_staff`, `is_superuser` or `is_active=False`; if any user with that email (case-insensitive) is blocked, no link is issued.
- Other people's phone, admin note, linkedin, and any people outside the caller's own approved pair are never returned by `members/me/`.
- Throttles: request uses scope `email` (existing 20/hour); verify uses new scope `signin_verify` = `60/hour` in `DEFAULT_THROTTLE_RATES`. Tests that post many requests call `django.core.cache.cache.clear()` in `setUp`.
- Frontend session keys (same as admin login): `accessToken`, `refreshToken`, `user` in `localStorage`. API calls use `@/backend/functions` helpers.
- Commit trailer on every commit: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Do not push; the owner approves pushes. Do not use `rm -rf` in commands.
- Frontend task-done commands must print a result line (e.g. `&& echo 'tsc + eslint clean'`) or the ledger script exits silently.

## Review Focus

Inputs the spec implies but its own tasks don't obviously cover; each has a test or browser check in the owning task.

1. Two users share one email and one is staff: no link is issued, and verify refuses a link issued earlier (Task 1, 3).
2. The verify page fires exactly one POST even under React StrictMode, and removes the token from the address bar (Task 5).
3. `"  Ann@X.com "` and `"ann@x.com"` resolve to the same link target and the same user (Task 1, 3).
4. One person is a mentee in one cohort and a mentor in another: both cards appear and each applies its own rules (Task 4, 6).
5. A mentee assigned to a mentor later becomes rejected or unassigned: they vanish from that mentor's list on the next load (Task 4).

---

## File Structure

Backend (`backend/backend/cohorts/`):
- `models.py` (modify): add `LoginLink`.
- `migrations/0003_*.py` (create via `makemigrations`).
- `signin.py` (create): link lifecycle and user/token helpers.
- `emails.py` (modify): add `send_signin_link`.
- `member_serializers.py` (create): `ProfileSerializer`, `membership_payload`.
- `member_views.py` (create): `SigninRequestView`, `SigninVerifyView`, `MeView`, `MyMembershipView`.
- `urls.py` (modify): four routes.
- `test_signin.py` (create): all tests for this feature (imports `make_cohort`, `add`, `staff_client`, constants from `cohorts.tests`).
- `../backend/settings.py` (modify): throttle rate.

Frontend (`fronted/src/`):
- `lib/session.ts` (create): `saveSession`, `getStoredUser`, `signOut`.
- `pages/SignInPage.tsx`, `pages/SignInVerifyPage.tsx`, `pages/MyCohortPage.tsx` (create).
- `components/MemberProfileDialog.tsx` (create).
- `routes/PublicRoutes.tsx` (modify): three routes.
- `components/Navbar.tsx` (modify): Sign in / My cohort / Dashboard.
- `components/CohortRegistration.tsx` (modify): thank-you line.
- `admin/layouts/DashboardLayout.tsx` (modify): guard.

---

### Task 1: LoginLink model and helpers

**Files:** Modify `cohorts/models.py`, `backend/settings.py`; Create `cohorts/migrations/0003_*.py`, `cohorts/signin.py`, `cohorts/test_signin.py`.

**Interfaces:**
- Produces `LoginLink` (fields `email` EmailField db_index, `token_hash` CharField(64, unique), `created_at` auto_now_add, `expires_at` DateTimeField, `used_at` DateTimeField null).
- Produces in `signin.py`: constants `LINK_TTL = timedelta(minutes=15)`, `COOLDOWN = timedelta(seconds=60)`, `SESSION_REFRESH_LIFETIME = timedelta(days=30)`; `hash_token(raw: str) -> str`; `normalise(email: str) -> str` (strip + lower); `can_sign_in(email: str) -> bool`; `issue_link(email: str) -> str | None`; `redeem(raw: str) -> LoginLink | None`; `user_for(email: str) -> User | None`; `tokens_for(user) -> dict[str, str]` with keys `access`, `refresh`.

- [ ] **Step 1: Failing tests** in `test_signin.py` (`class SigninHelperTests(TestCase)`):
  - `test_can_sign_in_needs_a_membership_and_no_blocked_user`: no membership -> False; any-status membership -> True; case/space variants of the email -> True; a staff user with that email -> False; a superuser -> False; an inactive user -> False; two users share the email, one staff -> False.
  - `test_issue_link_stores_only_a_hash_and_respects_cooldown`: returns a raw token whose `hash_token` matches the row; raw token not stored in any field; a second call within 60s returns `None`; with `created_at` moved back 61s a new link is issued and old expired/used links for that email are deleted; an ineligible email returns `None` and creates nothing.
  - `test_redeem_is_single_use_and_expiry_aware`: first `redeem` returns the link and sets `used_at`; second returns `None`; unknown token `None`; expired (`expires_at` in the past) `None`.
  - `test_user_for_creates_then_reuses_a_non_staff_verified_user`: first call creates user (`username == email`, `email_verified`, `not has_usable_password()`, `is_staff False`, names split from the earliest membership's full name); second call returns the same user; email case variants return the same user; a staff match returns `None`.
  - `test_tokens_for_gives_a_thirty_day_refresh_token`: decoding `RefreshToken(tokens["refresh"])` has `exp - iat` of 30 days (±5s) and `tokens["access"]` is a non-empty string.
- [ ] **Step 2: Run** `python manage.py test cohorts.test_signin` — expect FAIL (names missing).
- [ ] **Step 3: Implement** model, migration (`makemigrations cohorts`), settings throttle rate `"signin_verify": "60/hour"` in `DEFAULT_THROTTLE_RATES`, and `signin.py`. Use `api.models.User` via `get_user_model()`. `redeem` marks used with `LoginLink.objects.filter(pk=..., used_at__isnull=True, expires_at__gt=now).update(used_at=now)` and succeeds only when the row count is 1. `user_for` blocks when any user with that email is staff/superuser/inactive.
- [ ] **Step 4: Run** the cohorts tests and `makemigrations --check --dry-run` — expect PASS / "No changes detected".
- [ ] **Step 5: Commit** `"Add login link model and sign-in helpers"`.

### Task 2: Sign-in request endpoint and email

**Files:** Modify `cohorts/emails.py`, `cohorts/urls.py`; Create `cohorts/member_views.py`; Test `cohorts/test_signin.py`.

**Interfaces:**
- Consumes: `signin.issue_link`, `signin.normalise`.
- Produces `emails.send_signin_link(email: str, raw_token: str) -> None` (subject `"Your sign-in link for A Million Techies"`; body contains `{FRONTEND_URL}/signin/verify?token={raw_token}`, "works once", "15 minutes", and "If you didn't ask for this, you can ignore this email."; failures logged and swallowed).
- Produces `SigninRequestView(APIView)` at `POST /api/members/signin/request/`, `AllowAny`, `ScopedRateThrottle` with scope `email`.

- [ ] **Step 1: Failing tests** (`class SigninRequestTests`, locmem email, `cache.clear()` in setUp): known email -> 200, one email to that address containing `/signin/verify?token=` and exactly one `LoginLink`; unknown, staff, superuser and inactive-user emails -> same 200 body, no email, no link; the response JSON is byte-identical for known and unknown; second request within 60s sends nothing; `"  ANN@x.com "` for a stored `ann@x.com` works; missing or `"not-an-email"` -> 400; mail failure (`mock.patch("cohorts.emails.send_mail", side_effect=OSError)` inside `assertLogs`) still 200; `SigninRequestView.throttle_scope == "email"`.
- [ ] **Step 2: Run** — expect FAIL.
- [ ] **Step 3: Implement** `send_signin_link`, the view (validate email with Django's `validate_email`; call `issue_link`; send only if a token came back) and the route `members/signin/request/` in `urls.py`.
- [ ] **Step 4: Run** the cohorts tests — expect PASS.
- [ ] **Step 5: Commit** `"Add sign-in link request endpoint"`.

### Task 3: Sign-in verify endpoint

**Files:** Modify `cohorts/member_views.py`, `cohorts/urls.py`; Test `cohorts/test_signin.py`.

**Interfaces:**
- Consumes: `signin.redeem`, `signin.user_for`, `signin.tokens_for`, `api.serializers.UserProfileSerializer`.
- Produces `SigninVerifyView(APIView)` at `POST /api/members/signin/verify/`, `AllowAny`, `ScopedRateThrottle` scope `signin_verify`. Success: 200 `custom_response(True, "Signed in", {"user": UserProfileSerializer(user).data, "tokens": {"access", "refresh"}})`. Any failure: 400 with the exact invalid-link message from Global Constraints.

- [ ] **Step 1: Failing tests** (`class SigninVerifyTests`): a link issued with `issue_link` redeems to 200 with `data.tokens.access`/`refresh` and `data.user.email`, `is_staff == False`; `RefreshToken(data.tokens.refresh)` is valid and belongs to that user; same token a second time -> 400 with the exact message; expired -> 400; garbage/empty token -> 400; a staff user created with that email after the link was issued -> 400 (and no tokens); two users share the email, one staff -> 400; the second sign-in for the same email reuses the same user (`User.objects.count()` unchanged); `SigninVerifyView.throttle_scope == "signin_verify"`.
- [ ] **Step 2: Run** — expect FAIL.
- [ ] **Step 3: Implement** the view and route `members/signin/verify/`.
- [ ] **Step 4: Run** the cohorts tests — expect PASS.
- [ ] **Step 5: Commit** `"Add sign-in verify endpoint"`.

### Task 4: My membership data (GET/PATCH)

**Files:** Create `cohorts/member_serializers.py`; Modify `cohorts/member_views.py`, `cohorts/urls.py`; Test `cohorts/test_signin.py`.

**Interfaces:**
- Produces `ProfileSerializer(ModelSerializer)` on `CohortMembership` with fields `full_name, phone, location, headline, about, expertise, linkedin, show_publicly` (all other model fields are not accepted).
- Produces `membership_payload(m: CohortMembership) -> dict` in the shape from the spec (`id, role, status, created_at, decided_at, cohort{title,slug,status,start_date,end_date,duration}, profile{...}, mentor{full_name,headline,about,email}|None, mentees[{full_name,headline,about,email}]`). `mentor` only when `m` is an approved mentee and `m.mentor` is an approved mentor; `mentees` only when `m` is an approved mentor and lists approved mentees whose `mentor == m`.
- Produces `MeView` at `GET /api/members/me/` -> `data = {"email", "name", "memberships": [...]}` (newest first; `name` from the user's `first_name last_name` or username), `IsAuthenticated`.
- Produces `MyMembershipView` at `PATCH /api/members/me/<int:pk>/`, `IsAuthenticated`; memberships limited to `email__iexact=request.user.email`, others 404; returns `membership_payload`; validation errors via `error_response`.

- [ ] **Step 1: Failing tests** (`class MeTests`, helper `sign_in(email)` that issues+redeems a link and returns an `APIClient` with the bearer token): unauthenticated GET -> 401; a user with no memberships -> `memberships == []`; a mentee with an approved mentor sees the mentor's name, headline, about and email; a mentee whose mentor is unassigned, pending, or rejected sees `mentor is None`; a pending mentee sees `mentor is None` even if assigned; a mentor sees only approved mentees assigned to them (not unassigned, pending, rejected, or other cohorts'), each with email; a mentee who later becomes rejected or unassigned disappears from the mentor's list on the next call; one person who is a mentee in cohort A and a mentor in cohort B gets two memberships with each side's rules; the serialized payload never contains the substrings of a seeded `phone`, `admin_note`, or another person's `linkedin`; PATCH changes `headline`, `about`, `show_publicly`; PATCH with `status: "APPROVED"`, `role: "MENTOR"`, `mentor: <id>`, `admin_note: "x"`, `email: "other@x.com"` leaves those unchanged (still 200); PATCH of another person's membership id -> 404; blank `about` -> 400 with `message`.
- [ ] **Step 2: Run** — expect FAIL.
- [ ] **Step 3: Implement** the serializer, `membership_payload`, both views and routes `members/me/` and `members/me/<int:pk>/`. Query with `select_related("cohort", "mentor")` and `prefetch_related` for mentees to avoid per-row queries.
- [ ] **Step 4: Run** the full backend suite `python manage.py test` and `makemigrations --check --dry-run` — expect PASS / no changes.
- [ ] **Step 5: Commit** `"Add member self-service endpoints"`.

### Task 5: Sign-in pages and session handling

**Files (frontend repo):** Create `src/lib/session.ts`, `src/pages/SignInPage.tsx`, `src/pages/SignInVerifyPage.tsx`; Modify `src/routes/PublicRoutes.tsx`.

**Interfaces:**
- Produces `session.ts`: `saveSession(data: { user: unknown; tokens: { access: string; refresh: string } }): void` (stores `accessToken`, `refreshToken`, `user`), `getStoredUser(): { id?: number; email?: string; first_name?: string; last_name?: string; username?: string; is_staff?: boolean } | null`, `signOut(): void` (removes the three keys).
- `/signin` (`SignInPage`): email field + "Send me a sign-in link" -> `apiPostRequest("members/signin/request/", { email })`; then a "Check your inbox" panel with the generic message and a "Use a different email" button; errors shown inline.
- `/signin/verify` (`SignInVerifyPage`): reads `token` from the query string, removes it from the address bar with `window.history.replaceState`, posts it **once** (a `useRef` guard so React StrictMode does not double-post), on success `saveSession(res.data)` then `navigate("/my-cohort", { replace: true })`; on failure shows the server message and a "Send me a new link" link to `/signin`. A missing token shows the same failure UI without posting.
- Routes `/signin`, `/signin/verify` added to `PublicRoutes.tsx` inside the public `Layout`.

- [ ] **Step 1: Implement** the files above.
- [ ] **Step 2: Verify** `cd fronted && npx tsc --noEmit && npx eslint src --max-warnings 0 && echo 'tsc + eslint clean'` — expect the echo.
- [ ] **Step 3: Browser check** (mock API): request shows the generic panel and posts the typed email; a 429/400 shows inline text; verify with a good token posts exactly once, stores the three keys, lands on `/my-cohort`, and the URL no longer contains the token; verify with a failing token shows the server message and the "Send me a new link" link; no token -> failure UI, no POST.
- [ ] **Step 4: Commit** `"Add member sign-in pages"` (frontend repo).

### Task 6: My cohort page

**Files (frontend repo):** Create `src/pages/MyCohortPage.tsx`, `src/components/MemberProfileDialog.tsx`; Modify `src/routes/PublicRoutes.tsx`.

**Interfaces:**
- Consumes: `GET members/me/` and `PATCH members/me/<id>/` (Task 4 shapes), `session.getStoredUser`, `session.signOut`.
- Produces `MyCohortPage` at `/my-cohort`: if no `accessToken` redirect to `/signin`; loading, error + retry, and empty state ("We couldn't find an application for this email."); header with the person's name and a **Sign out** button (`signOut()` then navigate to `/`); one card per membership: cohort title (link to `/cohorts/<slug>`), role, status pill; Pending text "Your application is under review. We'll email you when it's decided."; Rejected text "Your application wasn't successful this time."; approved mentee: mentor panel (name, headline, bio, `mailto:` email) or "A mentor hasn't been assigned yet."; approved mentor: mentee list (name, headline, bio, `mailto:` email) or "No mentees assigned yet."; "Edit my profile" button per card.
- Produces `MemberProfileDialog({ membership, onClose, onSaved })`: fields `full_name, phone, location, headline, about, expertise, linkedin, show_publicly`; saves with `apiPatchRequest`, shows the server message on failure, toast on success; sends only those fields.

- [ ] **Step 1: Implement** both files and the `/my-cohort` route.
- [ ] **Step 2: Verify** `tsc` + `eslint src` as in Task 5.
- [ ] **Step 3: Browser check** (mock API): approved mentee with mentor, approved mentor with mentees, pending, rejected, and one person with a mentee card plus a mentor card render the right panels and texts; edit profile sends exactly the eight editable keys and updates the card; Sign out clears storage and goes home; no token redirects to `/signin`; empty memberships show the empty state; phone width fits.
- [ ] **Step 4: Commit** `"Add My cohort page"`.

### Task 7: Navbar, thank-you line, admin guard

**Files (frontend repo):** Modify `src/components/Navbar.tsx`, `src/components/CohortRegistration.tsx`, `src/admin/layouts/DashboardLayout.tsx`.

**Interfaces:**
- Navbar: signed out shows a "Sign in" link to `/signin`; signed in shows "My cohort" (`/my-cohort`) or, when the stored user has `is_staff === true`, "Dashboard" (`/admin`). Read the session with `getStoredUser()` / presence of `accessToken`.
- `CohortRegistration` thank-you panel gains: "You can sign in with this email at any time to check on your application." with a link to `/signin`.
- `DashboardLayout` guard: no `accessToken` or no stored user -> `Navigate` to `/admin/login`; stored user with `is_staff === false` -> `Navigate` to `/my-cohort`; `is_staff` undefined or true -> render the layout.

- [ ] **Step 1: Implement** the three edits.
- [ ] **Step 2: Verify** `tsc` + `eslint src` as in Task 5.
- [ ] **Step 3: Browser check** (mock API): navbar shows each of the three states; thank-you line appears after registering; `/admin` with a `is_staff:false` user redirects to `/my-cohort`; `/admin` with no session redirects to `/admin/login`; `/admin` with a stored user that has no `is_staff` field and with `is_staff:true` renders the admin shell.
- [ ] **Step 4: Commit** `"Sign-in link in navbar and admin guard for members"`.

### Task 8: Full verification

- [ ] **Step 1:** Backend `python manage.py test` and `makemigrations --check --dry-run`; frontend `npx tsc --noEmit`, `npx eslint src --max-warnings 0`, `npx vite build --outDir <scratch>` (never the tracked `dist/`).
- [ ] **Step 2: End-to-end browser run** (stateful mock of the three backend behaviours): request link -> open verify link -> My cohort shows pending; mock admin approves and assigns a mentor -> reload My cohort shows the mentor with email; edit profile persists in the mock; sign out; `/admin` redirect for the member.
- [ ] **Step 3:** Confirm `git status` shows only the known local `db.sqlite3` change in the backend repo and nothing unexpected in the frontend repo.

---

## Self-review notes

- Spec coverage: model and helpers (T1), request endpoint and email (T2), verify endpoint with 30-day session and staff exclusion (T3), `me` GET/PATCH with privacy rules (T4), sign-in pages and single-run verify (T5), My cohort and profile editing (T6), navbar, thank-you line and admin guard (T7), end-to-end (T8). Throttle scope and migration are in T1. Staff never receive links: T1 helpers, T2 and T3 tests.
- Decisions this plan fixes where the spec is silent: helper module `signin.py`; `redeem` is atomic via a conditional UPDATE; the request endpoint validates only email syntax; `members/me/` is allowed for any authenticated user (staff simply have no memberships); tests live in `test_signin.py`.
- Consistency: names `issue_link`, `redeem`, `user_for`, `tokens_for`, `membership_payload`, `saveSession`, `getStoredUser`, `signOut` and the four endpoint paths match across tasks.

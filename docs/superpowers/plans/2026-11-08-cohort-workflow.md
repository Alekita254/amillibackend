# Cohort Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Public registration for cohorts, admin review and mentor assignment, and real approved members on the public cohort pages.

**Architecture:** One `CohortMembership` row per person per cohort (role + status). Public endpoints register and list opted-in approved people; staff-only endpoints manage members. The admin cohort page gains a Members tab; the public cohort page gains a Register dialog and the people pages read from the API.

**Tech Stack:** Django 6.1 / DRF 3.18 (backend, `backend/backend/cohorts`), React 19 + TypeScript + Vite + shadcn/Tailwind (frontend, `fronted/src`). No frontend test runner exists: frontend tasks are verified with `tsc`, ESLint, a production build, and a headless-Chrome run against a mocked API (scripts are throwaway, kept outside the repo).

**Spec:** `backend/docs/superpowers/specs/2026-11-08-cohort-workflow-design.md` (repo `backend`).

## Global Constraints

- Backend tests: `cd backend/backend && DJANGO_SECRET_KEY=t python manage.py test` (use the project venv; the key env var is required by settings).
- Responses from cohort endpoints use `api.utils.custom_response(success, message, data, status_code)`; errors are `{"success": false, "message": "<human text>", "data": {<field>: [errors]}}` so the frontend's `result.message` shows something useful.
- Staff = `user.is_staff`. Staff-only endpoints: anonymous gets 401, non-staff gets 403.
- Public endpoints never return email, phone, linkedin, admin_note, status, or mentor links.
- Registration defaults to closed. No existing data is changed or deleted. `learner_count` / `mentor_count` columns stay in the table but are served computed.
- Capacity counts **approved mentees only**; mentors are uncapped; pending applications use no seats.
- One membership per (cohort, email), email stored lowercased and stripped.
- Exact messages: closed `"Registration for this cohort is closed."`; full `"This cohort is full."`; duplicate `"You've already registered for this cohort with this email."`; staff approving into a full cohort `"Cohort is full. Raise the capacity first."`.
- Field limits: `full_name` 150, `phone` 30, `location` 100, `headline` 150, `about` 2000 (required), `expertise` 1000, `linkedin` URL max 200, `admin_note` 2000.
- Commit trailer on every commit: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Frontend: reuse `PageHeader`, `Pill`, `EmptyState`, `ConfirmDialog`, `Field`/`NativeSelect`, `DataTable`, `errorText` from `fronted/src/admin/`. API calls use `@/backend/functions` helpers (they handle auth and token refresh).
- Do not push; the owner approves pushes.

## Review Focus

Inputs the spec implies but its own tasks don't obviously cover; each has a test in the owning task.

1. Email with spaces/uppercase (`"  Ann@X.com "`) must dedupe against `ann@x.com` (Task 1, 3).
2. Two mentees pending for the last seat: approving the first works, approving the second is blocked (Task 5).
3. A staff PATCH naming a mentor from another cohort, a pending/rejected mentor, or a mentee as `mentor` is a 400 (Task 5).
4. A mentor demoted (role to mentee, status away from approved) or deleted leaves their mentees unassigned but still in the cohort (Task 5).
5. Lowering `capacity` below approved mentees is a 400, clearing it to null is fine, and a cohort with zero opted-in people returns `[]`, not an error (Task 2, 4).

---

## File Structure

Backend (`backend/backend/cohorts/`):
- `models.py` (modify): new `Cohort` fields + computed properties; new `CohortMembership`.
- `migrations/0002_*.py` (create via `makemigrations`).
- `admin.py` (modify): register `CohortMembership`.
- `serializers.py` (modify): extend `CohortSerializer`; add `RegistrationSerializer`, `PublicPersonSerializer`, `MembershipSerializer`.
- `emails.py` (create): `send_application_received(membership)`, `send_decision(membership)`; both log and swallow failures.
- `views.py` (modify): `CohortRegisterView`, `CohortPeopleView`, `CohortMemberListCreateView`, `CohortMemberDetailView`.
- `urls.py` (modify): four new routes.
- `tests.py` (create): all backend tests for this feature.

Frontend (`fronted/src/`):
- `admin/lib/cohortMembers.ts` (create): types and label maps.
- `admin/components/CohortForm.tsx` (modify): registration switch + seats; drop manual counts.
- `admin/components/CohortDetailEdit.tsx` (modify): Details / Members tabs.
- `admin/components/CohortMembers.tsx` (create): Members tab (filters, table, actions).
- `admin/components/MemberDialog.tsx` (create): view/edit details + note; add-member form.
- `admin/components/CohortTable.tsx` (modify): pending pill.
- `components/CohortRegistration.tsx` (create): public register dialog + form.
- `pages/CohortDetailPage.tsx` (modify): Register button/state; counts from API; people preview from API.
- `pages/CohortPeoplePage.tsx` (modify): read `people/` from the API.
- `assets/cohortPeople.ts` (delete when nothing imports it; `ProjectDetailPage.tsx` also imports it, check before deleting).

---

### Task 1: Models, migration, admin

**Files:**
- Modify: `backend/backend/cohorts/models.py`, `backend/backend/cohorts/admin.py`
- Create: `backend/backend/cohorts/migrations/0002_*.py` (generated), `backend/backend/cohorts/tests.py`

**Interfaces:**
- Produces on `Cohort`: fields `registration_open: bool = False`, `capacity: int | None`; properties `seats_taken -> int`, `mentor_total -> int` (approved mentors), `seats_left -> int | None`, `registration_state -> "open" | "closed" | "full"`; reverse name `memberships`.
- Produces `CohortMembership` with constants `ROLE_MENTEE="MENTEE"`, `ROLE_MENTOR="MENTOR"`, `STATUS_PENDING="PENDING"`, `STATUS_APPROVED="APPROVED"`, `STATUS_REJECTED="REJECTED"` and the fields in the spec table. `mentor = ForeignKey("self", null, blank, SET_NULL, related_name="mentees")`. `save()` sets `email = email.strip().lower()`. `Meta.constraints = [UniqueConstraint(fields=["cohort","email"], name="uniq_cohort_email")]`, `ordering = ["-created_at"]`.

- [ ] **Step 1: Write failing tests** in `tests.py` (class `ModelTests(TestCase)`):
  - `test_registration_state`: published open cohort -> `"open"`; `registration_open=False` -> `"closed"`; `published=False` -> `"closed"`; `status="COMPLETED"` -> `"closed"`; `capacity=1` with one approved mentee -> `"full"`; pending/mentor rows do not make it full.
  - `test_counts_and_seats`: 2 approved mentees, 1 approved mentor, 1 pending mentee, capacity 5 -> `seats_taken == 2`, `mentor_total == 1`, `seats_left == 3`; capacity `None` -> `seats_left is None`.
  - `test_email_normalised_and_unique`: saving `"  Ann@X.com "` stores `"ann@x.com"`; a second `"ANN@x.com"` in the same cohort raises `IntegrityError`; the same email in another cohort is fine.
  - `test_deleting_mentor_unassigns_mentees`: mentee keeps existing, `mentor is None`.
- [ ] **Step 2: Run** `python manage.py test cohorts` — expect FAIL (fields/model missing).
- [ ] **Step 3: Implement** the model changes above; `python manage.py makemigrations cohorts` (migration name auto). Register `CohortMembership` in admin with `list_display = ("full_name","email","cohort","role","status","show_publicly")`, filters on `cohort`, `role`, `status`, search on name/email.
- [ ] **Step 4: Run** the cohorts tests and `python manage.py makemigrations --check --dry-run` — expect PASS / "No changes detected".
- [ ] **Step 5: Commit** `"Add cohort membership model and registration fields"` (stage models, migration, admin, tests).

### Task 2: Cohort serializer (computed values + registration settings)

**Files:** Modify `backend/backend/cohorts/serializers.py`, `backend/backend/cohorts/views.py`; Test `cohorts/tests.py`.

**Interfaces:**
- Consumes: Task 1 `Cohort` properties.
- Produces: `CohortSerializer` output gains read-only `registration_state`, `seats_taken`, `seats_left`; `learner_count` and `mentor_count` become **read-only computed** (`seats_taken` / `mentor_total`); `registration_open` and `capacity` writable. `pending_count` (int, pending applications) is included **only when `request.user.is_staff`**. `validate_capacity(value)`: if not None and `< instance.seats_taken` raise `"Capacity can't be lower than the N mentees already approved."`.

- [ ] **Step 1: Failing tests** (`class CohortApiTests`): anonymous `GET /api/cohorts/<slug>/` has `registration_state`, `seats_taken`, `seats_left`, computed `learner_count`, and no `pending_count`; staff GET includes `pending_count`; staff `PATCH {"registration_open": true, "capacity": 10}` returns 200 and persists; `PATCH {"capacity": 1}` with 2 approved mentees is 400; `PATCH {"capacity": null}` is 200; `PATCH {"learner_count": 99}` is ignored (value stays computed).
- [ ] **Step 2: Run** — expect FAIL.
- [ ] **Step 3: Implement** in `CohortSerializer` (use `SerializerMethodField` for `pending_count`; `learner_count`/`mentor_count` declared `serializers.IntegerField(source=..., read_only=True)` via properties). Staff-only field via `to_representation` dropping `pending_count` for non-staff.
- [ ] **Step 4: Run** cohorts tests — expect PASS.
- [ ] **Step 5: Commit** `"Expose registration state and computed counts on cohorts"`.

### Task 3: Public registration endpoint and received email

**Files:** Create `cohorts/emails.py`; Modify `serializers.py`, `views.py`, `urls.py`; Test `tests.py`.

**Interfaces:**
- Produces `RegistrationSerializer` (ModelSerializer on `CohortMembership`; fields: `role, full_name, email, phone, location, headline, about, expertise, linkedin, show_publicly`; honeypot handled in the view). `validate(attrs)` receives the cohort via `self.context["cohort"]` and raises, in this order: closed (`registration_state == "closed"`), full (only when `role == MENTEE` and state is `"full"`), duplicate email.
- Produces `emails.send_application_received(m: CohortMembership) -> None` (subject `"Application received: {cohort.title}"`; body thanks them and says they will hear back by email; uses `settings.DEFAULT_FROM_EMAIL`; wraps in try/except, `logger.exception` on failure).
- Produces `POST /api/cohorts/<slug>/register/` -> `CohortRegisterView(APIView)`, `permission_classes=[AllowAny]`, `throttle_classes=[ScopedRateThrottle]`, `throttle_scope="email"`. 404 if the cohort is unpublished or missing. A non-empty `website` field returns 201 without saving. Success: 201 `custom_response(True, "Application received. We'll email you once it's reviewed.")`.

- [ ] **Step 1: Failing tests** (`class RegisterTests`, `locmem` email backend): happy path creates `PENDING`, sends exactly one email to the applicant; closed -> 400 with the exact closed message; unpublished -> 404; full mentee -> 400 full message, full mentor -> 201; `"  Ann@X.com "` after `"ann@x.com"` -> 400 duplicate message; non-empty `website` -> 201 and no row; missing `about` -> 400 with `data` containing `about`; `about` longer than 2000 -> 400; invalid `linkedin` -> 400; the view's `throttle_scope == "email"`; mail failure (patch `send_mail` to raise) still returns 201.
- [ ] **Step 2: Run** — expect FAIL.
- [ ] **Step 3: Implement** serializer, email helper, view, and the `register/` route in `urls.py`. Convert serializer errors into the `custom_response` error shape (message = first error text).
- [ ] **Step 4: Run** cohorts tests — expect PASS.
- [ ] **Step 5: Commit** `"Add public cohort registration"`.

### Task 4: Public people endpoint

**Files:** Modify `serializers.py`, `views.py`, `urls.py`; Test `tests.py`.

**Interfaces:**
- Produces `PublicPersonSerializer` fields exactly `id, role, full_name, headline, about`.
- Produces `GET /api/cohorts/<slug>/people/` -> `CohortPeopleView(generics.ListAPIView)`, `AllowAny`, no pagination, returns `custom_response(True, ..., data=[...])`; only `APPROVED` and `show_publicly=True`; ordered mentors first then by `full_name`; 404 for unpublished/missing cohort.

- [ ] **Step 1: Failing tests** (`class PeopleTests`): returns only approved + opted-in; response keys per person are exactly `{"id","role","full_name","headline","about"}`; pending, rejected and non-opted-in excluded; zero opted-in -> `data == []` and 200; unpublished cohort -> 404.
- [ ] **Step 2: Run** — expect FAIL.
- [ ] **Step 3: Implement** and add the `people/` route.
- [ ] **Step 4: Run** cohorts tests — expect PASS.
- [ ] **Step 5: Commit** `"Add public cohort people endpoint"`.

### Task 5: Staff members API, decisions and mentor rules

**Files:** Modify `serializers.py`, `views.py`, `urls.py`, `emails.py`; Test `tests.py`.

**Interfaces:**
- Consumes: Task 3 `emails.send_application_received` (unused here), Task 1 model.
- Produces `emails.send_decision(m)`: if `m.status == APPROVED` subject `"You're in: {cohort.title}"` (body names the mentor when assigned); if `REJECTED` subject `"Update on your application: {cohort.title}"`; no-op for other statuses; failures logged and swallowed.
- Produces `MembershipSerializer` (all spec fields; `mentor` = id, read-only `mentor_name`, read-only `created_at`, `decided_at`). `validate` enforces: `mentor` only on mentees; mentor must be `APPROVED` + `ROLE_MENTOR` + same cohort; resulting state that is an approved mentee when the cohort is full and the member wasn't already an approved mentee -> `"Cohort is full. Raise the capacity first."`; duplicate email (excluding self).
- Produces routes, all staff-only (`IsAdminUser`): `GET/POST cohorts/<slug>/members/` (`CohortMemberListCreateView`, filters `?role=` `?status=`; POST defaults `status=APPROVED`, ignores closed registration, sets `decided_at`, **sends no email**) and `GET/PATCH/DELETE cohorts/<slug>/members/<int:pk>/` (`CohortMemberDetailView`). On PATCH, when `status` changes to `APPROVED` or `REJECTED`: set `decided_at = now` and call `send_decision` once; an unchanged status sends nothing. After any change that stops a membership being an approved mentor (status away from approved, role to mentee) and on delete: `CohortMembership.objects.filter(mentor=m).update(mentor=None)`. A mentee changed to mentor gets `mentor=None`.

- [ ] **Step 1: Failing tests** (`class MemberApiTests`): anonymous 401 and non-staff 403 for GET, POST, PATCH, DELETE; list filters by role and status; approve sends exactly one email and sets `decided_at`, a second PATCH with the same status sends none; reject sends the rejection email; admin POST creates `APPROVED` with no email; assigning an approved same-cohort mentor works; mentor from another cohort, a `PENDING` or `REJECTED` mentor, and a mentee as `mentor` are each 400; with capacity 1 and two pending mentees, approving the first is 200 and the second is 400 with the full message; raising capacity then allows it; demoting a mentor (role to mentee, or status to `REJECTED`) and deleting one leaves their mentees with `mentor=None` and still approved; changing a mentee with a mentor to role mentor clears that mentor; the view for another cohort's member id is 404.
- [ ] **Step 2: Run** — expect FAIL.
- [ ] **Step 3: Implement** serializer, views (staff-only, scoped to the cohort slug including drafts), `send_decision`, routes.
- [ ] **Step 4: Run** the full backend suite `python manage.py test` — expect PASS; also `makemigrations --check --dry-run` clean.
- [ ] **Step 5: Commit** `"Add staff cohort member management"`.

### Task 6: Admin UI — registration settings and tabs

**Files:** Create `fronted/src/admin/lib/cohortMembers.ts`; Modify `admin/components/CohortForm.tsx`, `admin/components/CohortDetailEdit.tsx`, `admin/components/CohortTable.tsx`.

**Interfaces:**
- Produces in `cohortMembers.ts`: `type MemberRole = "MENTEE" | "MENTOR"`, `type MemberStatus = "PENDING" | "APPROVED" | "REJECTED"`, `interface Member { id; role; status; full_name; email; phone; location; headline; about; expertise; linkedin; show_publicly; mentor: number | null; mentor_name: string | null; admin_note; created_at; decided_at }`, `ROLE_LABEL`, `STATUS_LABEL`, `STATUS_TONE: Record<MemberStatus, "amber"|"green"|"gray">`.
- `CohortForm` payload no longer sends `learner_count`/`mentor_count`; adds `registration_open: boolean` (toggle "Registration open — people can apply on the website") and `capacity: number | null` (empty input -> `null`, hint "Leave empty for no limit").
- `CohortDetailEdit` renders two tabs (**Details**, **Members** with a pending count) using a simple segmented control; Members renders `<CohortMembers slug cohort />` (Task 7).
- `CohortTable` shows an amber `Pill` "`N` pending" under the title when `pending_count > 0`.

- [ ] **Step 1: Implement** the files above (Members tab renders a placeholder `EmptyState` until Task 7).
- [ ] **Step 2: Verify** `cd fronted && npx tsc --noEmit && npx eslint src/admin --max-warnings 0` — expect no output / exit 0.
- [ ] **Step 3: Browser check** (mock API, light + dark): Details tab shows the switch and seats; saving sends `registration_open`/`capacity` and omits the manual counts; list shows the pending pill.
- [ ] **Step 4: Commit** `"Admin: registration settings and cohort tabs"` (frontend repo).

### Task 7: Admin UI — Members tab

**Files:** Create `admin/components/CohortMembers.tsx`, `admin/components/MemberDialog.tsx`.

**Interfaces:**
- Consumes: `Member` types (Task 6); API `GET/POST cohorts/<slug>/members/`, `PATCH/DELETE cohorts/<slug>/members/<id>/` (Task 5), via `apiGetRequest`, `apiPostRequest`, `apiPatchRequest`, `apiDeleteRequest`.
- Produces `CohortMembers({ slug, cohort }: { slug: string; cohort: { capacity?: number | null; seats_taken?: number } })`: header summary "Mentees X / Y seats · Mentors Z"; role filter (All/Mentees/Mentors) and status filter (All/Pending/Approved/Rejected); `DataTable` rows with name+email, role, status `Pill` (`STATUS_TONE`), mentor `NativeSelect` on mentee rows ("Unassigned" first, options = approved mentors in this cohort; changing it PATCHes `{mentor}`), applied date, and actions Approve / Reject / Remove (`ConfirmDialog`). Row click opens `MemberDialog`. Server errors shown with `errorText`/toast (e.g. the "Cohort is full" message).
- Produces `MemberDialog({ member?: Member | null; slug; onClose; onSaved })`: edit mode shows all fields and `admin_note` (PATCH); create mode ("Add member") POSTs with `status: "APPROVED"`.

- [ ] **Step 1: Implement** both components and replace the Task 6 placeholder.
- [ ] **Step 2: Verify** `tsc` + ESLint as in Task 6.
- [ ] **Step 3: Browser check** (mocked API recording requests): filters narrow the list; Approve sends `PATCH {status:"APPROVED"}`; Reject sends `REJECTED`; picking a mentor sends `PATCH {mentor:<id>}`; Remove asks to confirm then `DELETE`; "Add member" POSTs approved; a mocked 400 "Cohort is full…" appears as an error and the row is unchanged; empty state when no members.
- [ ] **Step 4: Commit** `"Admin: cohort members tab"`.

### Task 8: Public registration

**Files:** Create `fronted/src/components/CohortRegistration.tsx`; Modify `pages/CohortDetailPage.tsx`.

**Interfaces:**
- Consumes: cohort fields `registration_state`, `seats_left`, `slug`, `title` from `GET cohorts/<slug>/`; `apiPostRequest("cohorts/<slug>/register/", payload)`.
- Produces `CohortRegistration({ cohort }: { cohort: { slug: string; title: string; registration_state?: "open"|"closed"|"full"; seats_left?: number | null } })`: when `open`, a **Register** button (with "N seats left" when `seats_left` is not null) opening a dialog; when `full` or `closed`, a disabled state with text "This cohort is full" / "Registration is closed". Dialog form: role toggle (Mentee/Mentor), `full_name`*, `email`*, `phone`, `location`, `headline`, `about`* (label changes by role: "Why do you want to join?" / "About you"), `expertise` (label "Your goals" / "Your expertise"), `linkedin`, checkbox "Show me on the public page", a visually hidden `website` input (`tabIndex=-1`, `autoComplete="off"`), inline required checks, and on success a thank-you panel. Server messages (full, duplicate, closed) appear in the form and the entered values stay.
- `CohortDetailPage`: replace the "Apply / Join" button (links to `/joinus`) with `<CohortRegistration cohort={cohort} />`; counts come from the API's `learner_count`/`mentor_count` only (remove the `Math.max(..., static people length)` mixing).

- [ ] **Step 1: Implement** the component and page changes.
- [ ] **Step 2: Verify** `tsc` + `npx eslint src --max-warnings 0` for the touched files.
- [ ] **Step 3: Browser check** (mock API): open shows button + seats left; submit success shows thank-you and posted body includes `role`, `show_publicly`, and an empty `website`; mocked 400 duplicate and full messages are displayed with values preserved; `closed`/`full` states show no button; required fields block submit; phone width fits.
- [ ] **Step 4: Commit** `"Public cohort registration form"`.

### Task 9: People pages from the API and final verification

**Files:** Modify `pages/CohortPeoplePage.tsx`, `pages/CohortDetailPage.tsx`; Delete `assets/cohortPeople.ts` only if no import remains (`ProjectDetailPage.tsx` also imports it; if it still needs the data, leave the file and only stop using it in the cohort pages).

**Interfaces:**
- Consumes: `GET cohorts/<slug>/people/` -> `[{id, role, full_name, headline, about}]`.
- `CohortPeoplePage({ kind })` loads people once, filters `role === "MENTEE"` or `"MENTOR"`, shows loading, error + retry, and an empty state ("No one has chosen to be shown yet."); initials avatar and the existing dialog keep working with `full_name`/`headline`/`about`.
- `CohortDetailPage` people previews use the same endpoint (a small fetch alongside the cohort fetch).

- [ ] **Step 1: Implement** the page changes; remove now-unused imports.
- [ ] **Step 2: Full verification** — backend `python manage.py test` and `makemigrations --check --dry-run`; frontend `npx tsc --noEmit`, `npx eslint src --max-warnings 0` (or on touched dirs if the rest has pre-existing warnings), `npx vite build --outDir <temp>` (never touch the tracked `dist/`).
- [ ] **Step 3: End-to-end browser run** (mock API) of the whole flow: public people page lists opted-in people and shows the empty state; register from the cohort page; admin Members tab approve + assign mentor.
- [ ] **Step 4: Commit** `"Cohort people pages use real members"`; confirm `git status` shows only the known local `db.sqlite3` change in the backend repo.

---

## Self-review notes

- Spec coverage: data model (T1), computed values and settings (T2), registration with throttle/honeypot/limits/email (T3), people endpoint and privacy (T4), staff API, rules, decision emails (T5), admin tabs/settings/pending badge (T6), Members tab (T7), public form and states (T8), people pages and removal of fake data (T9). Migration and compatibility are covered by T1 plus Global Constraints.
- Decisions the spec left open and this plan fixes: admin-added members get no email; the staff Members list is not paginated; mail send is synchronous but failure-tolerant; per-cohort count queries are acceptable (cohort lists are small).
- Consistency: `registration_state` values, `seats_taken`/`seats_left`, member field names, and endpoint paths match across T1–T9.

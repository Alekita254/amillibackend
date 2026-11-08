# Cohort workflow: members, mentor assignment, registration

Date: 2026-11-08
Status: awaiting review
Repos: `backend` (Django/DRF) and `fronted` (React/Vite)

## Goal

Let the public register for a cohort, let admins review applications and
assign each mentee a mentor, and show real cohort members on the public
pages instead of the hardcoded sample people.

## Decisions (agreed with the owner)

| Topic | Decision |
|---|---|
| Registration | Anyone applies with a short form, no account. The application is **pending** until an admin approves or rejects it. |
| Pairing | One mentor per mentee. A mentor can have many mentees. |
| Mentors | Mentors **apply through the same form** (role toggle) and go through the same approval. Admins can also add a member directly as approved. |
| Limits | Per cohort: a "registration open" switch and an optional seat cap. |
| Public visibility | A person appears publicly only if they tick **"show me on the public page"**, for mentors and mentees alike. Email and phone are never public. |
| Counts | Learner and mentor counts are computed from approved members. |
| Capacity rule | The cap counts **approved mentees only**. Mentors are uncapped. Pending applications do not use seats. |
| Duplicates | One application per email per cohort, case-insensitive, regardless of role. |

## Data model (`cohorts` app)

### `Cohort` (two new fields)

- `registration_open` boolean, default `False`.
- `capacity` positive integer, nullable (null = no cap).

`learner_count` and `mentor_count` stay in the table (no destructive
migration) but are no longer edited or served as typed values. The API serves
computed counts under the same names.

### `CohortMembership` (new)

| Field | Notes |
|---|---|
| `cohort` | FK to `Cohort`, cascade. |
| `role` | `MENTEE` or `MENTOR`. |
| `status` | `PENDING` (default), `APPROVED`, `REJECTED`. |
| `full_name` | required, max 150. |
| `email` | required. |
| `phone`, `location`, `headline` | optional short text. `headline` is the public "title", e.g. "Backend developer". |
| `about` | text: bio for mentors, motivation for mentees. Required, max 2000. |
| `expertise` | text: mentor expertise or mentee goals/experience. Optional, max 1000. |
| `linkedin` | optional URL. |
| `show_publicly` | boolean, default `False`. |
| `mentor` | nullable FK to self, `SET_NULL`. Only meaningful for mentees. |
| `admin_note` | text, staff only. |
| `created_at`, `decided_at` | timestamps. `decided_at` set on approve/reject. |

Constraints:

- Unique on (`cohort`, lowercased `email`). The serializer checks this first so
  the user gets a friendly message.
- `mentor`, when set, must be an **approved mentor in the same cohort**, and
  the member being assigned must be a mentee. Enforced in the serializer.
- Deleting a mentor clears `mentor` on their mentees (`SET_NULL`).
- Changing a mentor to a non-approved state or non-mentor role clears
  `mentor` on their mentees.

Derived values (computed, not stored):

- `learner_count` = approved mentees, `mentor_count` = approved mentors.
- `seats_taken` = approved mentees. `seats_left` = `capacity - seats_taken`
  (null when uncapped).
- `registration_state`: `open`, `closed`, or `full`.
  - `closed` if not published, or `registration_open` is false, or the
    cohort status is `COMPLETED`.
  - `full` if open but a capacity is set and `seats_left` is 0.
  - otherwise `open`.

## API

All under `/api/`. "Staff" means a user with `is_staff`, as elsewhere.

### Public

- `POST cohorts/<slug>/register/` creates a `PENDING` membership.
  - Body: `role`, `full_name`, `email`, `phone`, `location`, `headline`,
    `about`, `expertise`, `linkedin`, `show_publicly`, and a hidden `website`
    spam-trap field (any value is silently accepted and discarded).
  - Rejects with 400 and a clear message when: the cohort is unpublished or
    not found (404), `registration_state` is not `open`, the role is mentee and
    the cohort is full, or the email is already registered for this cohort.
  - Mentor applications are not blocked by capacity.
  - Throttled with the existing `email` scope (20/hour per IP).
  - Sends the "application received" email, best effort.
  - Response never exposes other members' data.
- `GET cohorts/<slug>/people/` returns approved members with
  `show_publicly=True`: `id`, `role`, `full_name`, `headline`, `about`.
  Never email, phone, linkedin, notes or mentor links. 404 for unpublished
  cohorts.
- The existing cohort list/detail serializer gains read-only
  `registration_state`, `capacity`, `seats_taken`, `seats_left`, and the
  computed counts.

### Staff only

- `GET cohorts/<slug>/members/?role=&status=` lists memberships with all fields.
- `POST cohorts/<slug>/members/` adds a member directly. Status defaults to
  `APPROVED`; same validation as registration except registration being
  closed does not block it.
- `PATCH cohorts/<slug>/members/<id>/` edits `status`, `mentor`, `admin_note`,
  `show_publicly`, contact fields, `role`.
  - Moving to `APPROVED` for a mentee when the cohort is full is rejected
    ("Cohort is full. Raise the capacity first.").
  - A status change to `APPROVED` or `REJECTED` sets `decided_at` and sends the
    matching email once, best effort. Re-saving the same status sends nothing.
- `DELETE cohorts/<slug>/members/<id>/` removes a member.
- `PATCH cohorts/<slug>/` (existing) now also accepts `registration_open` and
  `capacity`. `capacity` may not be set below `seats_taken`.

The existing staff-only write rule on cohorts is unchanged
(`IsStaffOrReadOnly`). The members endpoints are staff-only for every method.

### Emails

Three plain templates, sent with the existing SMTP setup:

1. Application received (to the applicant).
2. Approved (to the applicant; includes cohort title and, for mentees, the
   mentor's name if one is already assigned).
3. Not selected (to the applicant).

A failure to send is logged and never fails the request.

## Admin UI (`fronted/src/admin`)

- **Cohort edit page** becomes two tabs: **Details** and **Members**.
  - Details keeps the existing form and adds "Registration open" and
    "Seats" (optional number), with a hint showing current seats taken.
- **Members tab**
  - Filters: role (All/Mentees/Mentors) and status (All/Pending/Approved/
    Rejected). Pending count shown on the tab.
  - Table: name and email, role, status pill, assigned mentor, applied date,
    actions. Mentee rows have a mentor dropdown listing approved mentors of
    the cohort ("Unassigned" first). Row actions: Approve, Reject, Remove
    (with the existing confirm dialog). Clicking a row opens a dialog
    with all details and the admin note.
  - "Add member" dialog (adds as approved).
  - Header summary: "Mentees 12 / 30 seats · Mentors 4".
- **Cohort list** shows a "N pending" pill on rows with pending applications
  (from a computed `pending_count` returned to staff only).
- Reuse existing building blocks: `PageHeader`, `Pill`, `EmptyState`,
  `ConfirmDialog`, `Field`, `DataTable`.

## Public UI (`fronted/src`)

- **Cohort detail page**: shows a Register button when `registration_state`
  is `open`, with "N seats left" when capped. When `closed` or `full`, shows
  that state instead of the button.
- **Registration form** (dialog or page): role toggle (Mentee / Mentor), the
  fields above, "Show me on the public page" checkbox, a hidden `website`
  field, inline validation, and a thank-you state after success. Server
  messages (full, duplicate, closed) are shown clearly.
- **People pages** (`/cohorts/:slug/mentees`, `/mentors`) fetch
  `people/` instead of using `assets/cohortPeople`. Empty state when nobody
  has opted in. The static sample data file is removed once nothing uses it.
- The standalone `/mentors` and `/mentors/:slug` pages are not changed.

## Security and privacy

- Public endpoints never return email, phone, linkedin, notes, status or
  mentor links.
- Registration is throttled and has a honeypot; all text fields have length
  limits; `linkedin` is validated as a URL; the front end renders text (React
  escapes it).
- Member management is staff-only; the permission is tested for every method.
- Cohort drafts stay invisible to the public (existing behaviour); the
  register and people endpoints 404 for unpublished cohorts.

## Migration and compatibility

- One migration adds the two `Cohort` fields and creates `CohortMembership`.
  No existing data is changed or deleted.
- Existing cohorts show 0 learners and mentors until members exist (the
  typed numbers are no longer served). Registration defaults to closed, so
  nothing becomes publicly registerable until an admin opts in.
- `JoinUsSubmission` and the Join Us page are untouched.

## Testing

Backend (Django test runner), at least:

- Register: open happy path; closed; unpublished; full (mentee blocked,
  mentor allowed); duplicate email in different case; honeypot ignored; bad
  input; throttle scope present.
- People endpoint: only approved and opted-in; no private fields in output.
- Staff members API: permissions (anonymous 401, non-staff 403) for every
  method; approve/reject sets `decided_at` and sends exactly one email;
  re-saving does not resend; approving a mentee into a full cohort is
  blocked; mentor must be approved, same cohort, and a mentor; deleting or
  demoting a mentor clears assignments; capacity cannot drop below seats
  taken.
- Computed counts and `registration_state`.

Frontend: `tsc`, ESLint (no warnings), production build, and a headless
browser run against a mocked API covering: register (success, full,
duplicate), the members tab (filter, approve, reject, assign mentor, add,
remove), and the people pages.

## Delivery order

One spec, built in three stages, each committed separately and checked
before the next:

1. Backend: models, migration, serializers, endpoints, emails, tests.
2. Admin UI: registration settings, Members tab, pending badge.
3. Public UI: register button and form, people pages from the API.

## Out of scope

Member logins and dashboards, mentor-facing views, messaging, waitlists,
payments, CSV export, changes to the `/mentors` pages, and dropping the unused
`learner_count` / `mentor_count` columns (can be a later cleanup).

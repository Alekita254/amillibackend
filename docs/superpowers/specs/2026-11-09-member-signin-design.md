# Member sign-in and "My cohort"

Date: 2026-11-09
Status: awaiting review
Repos: `backend` (Django/DRF) and `fronted` (React/Vite)
Builds on: `2026-11-08-cohort-workflow-design.md` (memberships, mentor assignment)

## Goal

Let mentors and mentees (anyone who applied to a cohort) sign in without a
password, using a one-time link sent to their email, and see their own cohort
space: application status, their mentor or mentees, and their own profile.

## Decisions (agreed with the owner)

| Topic | Decision |
|---|---|
| Purpose | A "My cohort" page: status, mentor/mentees, edit own profile. No admin tools. |
| Method | Email a one-time sign-in link. No passwords for members. |
| Who | Anyone with an application, any status (pending, approved, rejected). |
| Contact sharing | A mentor and their assigned mentees see each other's **email**, only for assigned approved pairs. Phone numbers are never shared. |
| Staff | A sign-in link never signs into a staff account. Staff keep their password login. |
| Link rules | 15 minutes, single use, at most one link per email per minute. |
| Session | Members stay signed in up to 30 days (refresh token). |
| Rejected applicants | Can sign in; see only their status. |
| Accounts | Created automatically, with no password, on the first successful link. |

## Backend (`cohorts` app)

### `LoginLink` (new model)

| Field | Notes |
|---|---|
| `email` | lowercased applicant email, indexed. |
| `token_hash` | SHA-256 hex of the raw token; unique. The raw token is never stored. |
| `created_at` | auto. |
| `expires_at` | `created_at + 15 minutes`. |
| `used_at` | null until used. |

Raw token: `secrets.token_urlsafe(32)`. Link: `{settings.FRONTEND_URL}/signin/verify?token=<raw>`.
When a new link is created for an email, that email's expired and used links are deleted.

### Endpoints (all under `/api/`)

**`POST members/signin/request/`** (public, throttled with the existing `email` scope)

- Body: `{ "email": "<address>" }`. A missing or malformed email is a 400.
- The response is **always** `200` with
  `custom_response(True, "If you've applied to a cohort, we've emailed you a sign-in link.")`
  whether or not the email is known, so it cannot be used to find out who applied.
- A link is created and emailed only when **all** hold:
  - at least one `CohortMembership` exists with that email (case-insensitive, any status);
  - no `User` with that email (case-insensitive) has `is_staff` or `is_superuser`, or is inactive;
  - no link was created for that email in the last 60 seconds.
- Email subject `"Your sign-in link for A Million Techies"`. Body: the link, "It works once and expires in 15 minutes", and "If you didn't ask for this, you can ignore this email."
- A mail failure is logged and does not change the response.

**`POST members/signin/verify/`** (public, throttled with a new `signin_verify` scope, `60/hour`)

- Body: `{ "token": "<raw>" }`.
- Unknown, expired or already used token: `400`, message
  `"This sign-in link has expired or was already used. Request a new one."`.
- Marking the link used is atomic (an `UPDATE ... WHERE used_at IS NULL` whose row count must be 1), so two simultaneous requests cannot both succeed.
- On success: find or create the `User`:
  - match by email (case-insensitive); if that user is staff, superuser or inactive, respond with the same 400 as an invalid token;
  - otherwise reuse it, or create one with `username` = lowercased email, `email`, an unusable password, `email_verified=True`, and `first_name`/`last_name` split from the full name on their earliest membership.
- Response `200`, `custom_response(True, "Signed in", data={"user": <UserProfileSerializer>, "tokens": {"access": ..., "refresh": ...}})`. This is the same shape the admin login returns, so the frontend stores it the same way.
- The refresh token's lifetime is set to **30 days** (`refresh.set_exp(lifetime=timedelta(days=30))`); the access token keeps the project default (15 minutes) and is renewed through the existing `/api/token/refresh/`.

**`GET members/me/`** (any authenticated user)

Memberships are those whose email equals the signed-in user's email (case-insensitive). Response `data`:

```
{
  "email": str, "name": str,
  "memberships": [{
    "id": int, "role": "MENTEE"|"MENTOR", "status": "PENDING"|"APPROVED"|"REJECTED",
    "created_at": ts, "decided_at": ts|null,
    "cohort": {"title", "slug", "status", "start_date", "end_date", "duration"},
    "profile": {"full_name","phone","location","headline","about","expertise","linkedin","show_publicly"},
    "mentor": {"full_name","headline","about","email"} | null,
    "mentees": [{"full_name","headline","about","email"}]
  }]
}
```

- `mentor` is filled only for an **approved mentee** whose assigned mentor is an **approved mentor**; otherwise `null`.
- `mentees` lists only for an **approved mentor**: approved mentees assigned to them; otherwise `[]`.
- Never included: anyone's phone, admin note, linkedin of other people, other cohorts' people, mentor links of other pairs.
- Sorted newest membership first. A user with no matching membership gets `memberships: []`.

**`PATCH members/me/<id>/`** (authenticated)

- `<id>` must be one of the user's own memberships, otherwise `404`.
- Editable fields only: `full_name` (required, max 150), `phone` (max 30), `location` (max 100), `headline` (max 150), `about` (required, max 2000), `expertise` (max 1000), `linkedin` (URL), `show_publicly`.
- Any other field in the body (`role`, `status`, `mentor`, `admin_note`, `email`, `cohort`) is ignored.
- Response: the updated membership in the `memberships[]` shape. Validation errors use the project's `{success, message, data}` error shape.

### Settings

`DEFAULT_THROTTLE_RATES` gains `"signin_verify": "60/hour"`. No other settings change.

### Migration

One migration creating `LoginLink`. No existing data is touched.

## Frontend (`fronted/src`)

- **`/signin`** (public): an email field and a "Send me a sign-in link" button; after submit, a "Check your inbox" panel that repeats the generic message and offers "Use a different email". Rate-limit or network errors are shown inline.
- **`/signin/verify?token=`** (public): posts the token to `members/signin/verify/`, stores `accessToken`, `refreshToken` and `user` in `localStorage` exactly as the admin login does, then goes to `/my-cohort`. On failure it shows the server message and a "Send me a new link" button to `/signin`. The token is removed from the address bar after use, and the request runs once (guard against React StrictMode double effects).
- **`/my-cohort`** (requires sign-in; otherwise redirect to `/signin`): loads `members/me/` and shows one card per membership:
  - cohort title, role and a status pill; for Pending "Your application is under review. We'll email you when it's decided."; for Rejected "Your application wasn't successful this time."
  - Approved mentee: a mentor panel (name, headline, bio, email as a `mailto:` link) or "A mentor hasn't been assigned yet."
  - Approved mentor: a list of assigned mentees (name, headline, bio, email), or "No mentees assigned yet."
  - "Edit my profile" opens a dialog with the editable fields; saving shows a toast.
  - A header with the person's name and a **Sign out** button (clears the stored session). Empty state when there are no memberships.
- **Navbar**: "Sign in" when signed out; when signed in, "My cohort" (or "Dashboard" linking to `/admin` for staff).
- **Registration thank-you screen**: adds a line that they can sign in with this email to check their application.
- **Admin guard**: `/admin/*` redirects to `/admin/login` when there is no session, and to `/my-cohort` when the stored user has `is_staff === false`. A stored user with no `is_staff` field (a session from before that field existed) is **not** redirected; the backend still enforces staff-only access.

## Security and privacy

- The request endpoint never reveals whether an email has applied; its response is identical. (The existing "already registered" message on the registration form already reveals applied emails, so this adds no new exposure. Mail latency can differ between known and unknown emails; accepted at this scale.)
- Tokens are 256-bit random, stored hashed, single use, short lived.
- Links never authenticate staff, superusers or inactive users.
- Members cannot reach any staff endpoint (already staff-only) and the admin UI redirects them away.
- Contact details are shared only inside an approved mentor-mentee pair, and only the email.
- All writes to `members/me/<id>/` are limited to the caller's own membership and the listed fields.

## Testing

Backend (Django test runner), at least:

- Request: known email sends one email and creates one link; unknown email, staff email, superuser email and inactive-user email send nothing; all return the same 200 body; a second request within 60 seconds sends nothing; a malformed email is 400; mail failure still returns 200; case/space variants of an email match.
- Verify: valid token returns tokens and user, and the access token works on `members/me/`; the same token twice fails the second time; an expired token fails; an unknown token fails; a staff user created after the link was issued cannot be signed in; first use creates a non-staff `email_verified` user with an unusable password and names split from the membership; a second sign-in reuses the same user; refresh token lifetime is 30 days.
- Me: a mentee sees their approved mentor with email, not before approval or assignment; a mentor sees only their approved assigned mentees; people from other cohorts and unassigned people never appear; no phone or admin note anywhere in the payload; pending and rejected applicants see status and `mentor: null`; unauthenticated is 401; user with no memberships gets `[]`.
- Patch: own profile fields change; `status`, `role`, `mentor`, `admin_note`, `email` in the body are ignored; someone else's membership id is 404; blank `about` is 400.

Frontend: `tsc`, ESLint (no warnings), production build, and a headless-browser run against a mocked API: request link (generic panel), verify success and failure, My cohort for a mentee and a mentor and a pending and a rejected applicant, edit profile, sign out, navbar states, and the admin guard (member redirected; admin without `is_staff` in storage not redirected).

## Delivery order

1. Backend: model, migration, endpoints, email, throttle, tests.
2. Frontend: sign-in pages, My cohort, navbar, admin guard, thank-you line.

Each stage is committed separately and checked before the next, followed by one independent review of the whole change.

## Out of scope

Passwords or Google sign-in for members, messaging between mentor and mentee, notifications beyond the sign-in link, changing the admin password login (the missing password-reset page is a separate item), multiple emails per person, and signing out other devices.

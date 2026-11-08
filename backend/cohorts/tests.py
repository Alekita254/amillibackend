from django.db import IntegrityError, transaction
from django.test import TestCase

from cohorts.models import Cohort, CohortMembership

MENTEE, MENTOR = CohortMembership.ROLE_MENTEE, CohortMembership.ROLE_MENTOR
PENDING, APPROVED = CohortMembership.STATUS_PENDING, CohortMembership.STATUS_APPROVED


def make_cohort(title="Alpha", **kwargs):
    defaults = dict(published=True, registration_open=True)
    defaults.update(kwargs)
    return Cohort.objects.create(title=title, **defaults)


def add(cohort, email, role=MENTEE, status=APPROVED, **kwargs):
    return CohortMembership.objects.create(
        cohort=cohort, email=email, role=role, status=status,
        full_name=kwargs.pop("full_name", email.split("@")[0]), about="about", **kwargs,
    )


class ModelTests(TestCase):
    def test_registration_state(self):
        c = make_cohort()
        self.assertEqual(c.registration_state, "open")

        c.registration_open = False
        self.assertEqual(c.registration_state, "closed")

        c.registration_open, c.published = True, False
        self.assertEqual(c.registration_state, "closed")

        c.published, c.status = True, Cohort.STATUS_COMPLETED
        self.assertEqual(c.registration_state, "closed")

        c.status, c.capacity = Cohort.STATUS_UPCOMING, 1
        add(c, "pending@x.com", status=PENDING)
        add(c, "mentor@x.com", role=MENTOR)
        self.assertEqual(c.registration_state, "open")  # pending + mentors use no seats

        add(c, "mentee@x.com")
        self.assertEqual(c.registration_state, "full")

    def test_counts_and_seats(self):
        c = make_cohort(capacity=5)
        add(c, "a@x.com")
        add(c, "b@x.com")
        add(c, "m@x.com", role=MENTOR)
        add(c, "p@x.com", status=PENDING)
        self.assertEqual(c.seats_taken, 2)
        self.assertEqual(c.mentor_total, 1)
        self.assertEqual(c.seats_left, 3)

        c.capacity = None
        self.assertIsNone(c.seats_left)

    def test_email_normalised_and_unique(self):
        c, other = make_cohort("A"), make_cohort("B")
        m = add(c, "  Ann@X.com ")
        self.assertEqual(m.email, "ann@x.com")

        with self.assertRaises(IntegrityError), transaction.atomic():
            add(c, "ANN@x.com")

        add(other, "ann@x.com")  # same email, different cohort is fine

    def test_deleting_mentor_unassigns_mentees(self):
        c = make_cohort()
        mentor = add(c, "mentor@x.com", role=MENTOR)
        mentee = add(c, "mentee@x.com", mentor=mentor)
        mentor.delete()
        mentee.refresh_from_db()
        self.assertIsNone(mentee.mentor)


from api.models import User
from rest_framework.test import APIClient


def staff_client():
    user = User.objects.create_user("staff", "staff@x.com", "pass12345", is_staff=True)
    client = APIClient()
    client.force_authenticate(user)
    return client


class CohortApiTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort(capacity=10)
        self.url = f"/api/cohorts/{self.cohort.slug}/"
        self.anon, self.staff = APIClient(), staff_client()

    def test_public_detail_has_registration_fields_and_computed_counts(self):
        add(self.cohort, "a@x.com")
        add(self.cohort, "b@x.com")
        add(self.cohort, "m@x.com", role=MENTOR)
        add(self.cohort, "p@x.com", status=PENDING)
        data = self.anon.get(self.url).json()["data"]
        self.assertEqual(data["registration_state"], "open")
        self.assertEqual((data["seats_taken"], data["seats_left"]), (2, 8))
        self.assertEqual((data["learner_count"], data["mentor_count"]), (2, 1))
        self.assertNotIn("pending_count", data)

    def test_staff_detail_includes_pending_count(self):
        add(self.cohort, "p@x.com", status=PENDING)
        self.assertEqual(self.staff.get(self.url).json()["data"]["pending_count"], 1)

    def test_staff_can_set_registration_open_and_capacity(self):
        r = self.staff.patch(self.url, {"registration_open": False, "capacity": 25}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.cohort.refresh_from_db()
        self.assertEqual((self.cohort.registration_open, self.cohort.capacity), (False, 25))

    def test_capacity_cannot_drop_below_approved_mentees_but_can_be_cleared(self):
        add(self.cohort, "a@x.com")
        add(self.cohort, "b@x.com")
        low = self.staff.patch(self.url, {"capacity": 1}, format="json")
        self.assertEqual(low.status_code, 400)
        self.assertIn("2 mentees", low.json()["message"])
        self.assertEqual(self.staff.patch(self.url, {"capacity": None}, format="json").status_code, 200)

    def test_typed_counts_are_ignored(self):
        self.staff.patch(self.url, {"learner_count": 99, "mentor_count": 99}, format="json")
        data = self.anon.get(self.url).json()["data"]
        self.assertEqual((data["learner_count"], data["mentor_count"]), (0, 0))


from unittest import mock
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from cohorts.views import CohortRegisterView

CLOSED_MSG = "Registration for this cohort is closed."
FULL_MSG = "This cohort is full."
DUPLICATE_MSG = "You've already registered for this cohort with this email."


def reg_payload(**overrides):
    data = dict(role="MENTEE", full_name="Ann Wanjiku", email="ann@x.com",
                about="I want to learn backend development.")
    data.update(overrides)
    return data


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RegisterTests(TestCase):
    def setUp(self):
        cache.clear()  # the 'email' throttle scope is shared with other tests
        self.cohort = make_cohort("Alpha")
        self.url = "/api/cohorts/alpha/register/"
        self.client = APIClient()

    def post(self, **overrides):
        return self.client.post(self.url, reg_payload(**overrides), format="json")

    def test_registers_pending_and_emails_applicant_once(self):
        r = self.post(show_publicly=True)
        self.assertEqual(r.status_code, 201, r.content)
        m = CohortMembership.objects.get()
        self.assertEqual((m.status, m.role, m.show_publicly), (PENDING, MENTEE, True))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ann@x.com"])
        self.assertIn("Alpha", mail.outbox[0].subject)

    def test_closed_cohort_is_rejected_with_clear_message(self):
        self.cohort.registration_open = False
        self.cohort.save()
        r = self.post()
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["message"], CLOSED_MSG)

    def test_unpublished_cohort_is_404(self):
        self.cohort.published = False
        self.cohort.save()
        self.assertEqual(self.post().status_code, 404)

    def test_full_cohort_blocks_mentees_but_not_mentors(self):
        self.cohort.capacity = 1
        self.cohort.save()
        add(self.cohort, "taken@x.com")
        full = self.post()
        self.assertEqual((full.status_code, full.json()["message"]), (400, FULL_MSG))
        self.assertEqual(self.post(role="MENTOR").status_code, 201)

    def test_duplicate_email_ignores_case_and_spaces(self):
        self.assertEqual(self.post(email="ann@x.com").status_code, 201)
        dup = self.post(email="  ANN@x.com ")
        self.assertEqual((dup.status_code, dup.json()["message"]), (400, DUPLICATE_MSG))
        self.assertEqual(CohortMembership.objects.count(), 1)

    def test_honeypot_returns_success_without_saving(self):
        r = self.post(website="http://spam.example")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(CohortMembership.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_input_is_rejected(self):
        missing = self.client.post(self.url, {k: v for k, v in reg_payload().items() if k != "about"}, format="json")
        self.assertEqual(missing.status_code, 400)
        self.assertIn("about", missing.json()["data"])
        self.assertEqual(self.post(about="x" * 2001).status_code, 400)
        self.assertEqual(self.post(linkedin="not a url").status_code, 400)
        self.assertEqual(self.post(role="ADMIN").status_code, 400)
        self.assertEqual(CohortMembership.objects.count(), 0)

    def test_registration_uses_the_email_throttle_scope(self):
        self.assertEqual(CohortRegisterView.throttle_scope, "email")

    def test_mail_failure_does_not_fail_registration(self):
        with mock.patch("cohorts.emails.send_mail", side_effect=OSError("smtp down")), \
                self.assertLogs("cohorts.emails", "ERROR"):
            r = self.post()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(CohortMembership.objects.count(), 1)

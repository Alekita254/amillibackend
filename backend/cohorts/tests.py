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

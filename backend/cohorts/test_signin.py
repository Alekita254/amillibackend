from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from cohorts import signin
from cohorts.models import LoginLink
from cohorts.tests import APPROVED, MENTEE, MENTOR, PENDING, REJECTED, add, make_cohort

User = get_user_model()


class SigninHelperTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort("Alpha")

    def test_can_sign_in_needs_a_membership_and_no_blocked_user(self):
        self.assertFalse(signin.can_sign_in("ann@x.com"))  # never applied

        add(self.cohort, "ann@x.com", status=REJECTED)  # any status counts
        self.assertTrue(signin.can_sign_in("ann@x.com"))
        self.assertTrue(signin.can_sign_in("  ANN@x.com "))  # case and spaces

        add(self.cohort, "staff@x.com")
        User.objects.create_user("staff", "staff@x.com", "pw12345678", is_staff=True)
        self.assertFalse(signin.can_sign_in("staff@x.com"))

        add(self.cohort, "root@x.com")
        User.objects.create_superuser("root", "root@x.com", "pw12345678")
        self.assertFalse(signin.can_sign_in("root@x.com"))

        add(self.cohort, "off@x.com")
        User.objects.create_user("off", "off@x.com", "pw12345678", is_active=False)
        self.assertFalse(signin.can_sign_in("off@x.com"))

        # email is not unique on User: one blocked account blocks the address
        add(self.cohort, "dup@x.com")
        User.objects.create_user("dup1", "dup@x.com", "pw12345678")
        User.objects.create_user("dup2", "dup@x.com", "pw12345678", is_staff=True)
        self.assertFalse(signin.can_sign_in("dup@x.com"))

    def test_issue_link_stores_only_a_hash_and_respects_cooldown(self):
        add(self.cohort, "ann@x.com")
        raw = signin.issue_link("  Ann@X.com ")
        link = LoginLink.objects.get()
        self.assertEqual(link.email, "ann@x.com")
        self.assertEqual(link.token_hash, signin.hash_token(raw))
        self.assertNotIn(raw, (link.email, link.token_hash))
        self.assertAlmostEqual((link.expires_at - link.created_at).total_seconds(), 15 * 60, delta=2)

        self.assertIsNone(signin.issue_link("ann@x.com"))  # inside the 60s cooldown
        self.assertEqual(LoginLink.objects.count(), 1)

        now = timezone.now()
        LoginLink.objects.create(email="ann@x.com", token_hash="expired", expires_at=now - timedelta(minutes=1))
        LoginLink.objects.create(email="ann@x.com", token_hash="used", expires_at=now + timedelta(minutes=5), used_at=now)
        LoginLink.objects.create(email="other@x.com", token_hash="other", expires_at=now - timedelta(minutes=1))
        LoginLink.objects.update(created_at=now - timedelta(seconds=61))  # all past the cooldown
        again = signin.issue_link("ann@x.com")
        self.assertTrue(again)
        hashes = set(LoginLink.objects.values_list("token_hash", flat=True))
        self.assertNotIn("expired", hashes)
        self.assertNotIn("used", hashes)
        self.assertIn("other", hashes)  # another email's links are left alone

        before = LoginLink.objects.count()
        self.assertIsNone(signin.issue_link("nobody@x.com"))  # never applied
        self.assertEqual(LoginLink.objects.count(), before)

    def test_redeem_is_single_use_and_expiry_aware(self):
        add(self.cohort, "ann@x.com")
        raw = signin.issue_link("ann@x.com")
        link = signin.redeem(raw)
        self.assertEqual(link.email, "ann@x.com")
        self.assertIsNotNone(LoginLink.objects.get().used_at)
        self.assertIsNone(signin.redeem(raw))  # second use
        self.assertIsNone(signin.redeem("not-a-token"))

        LoginLink.objects.all().delete()
        raw = signin.issue_link("ann@x.com")
        LoginLink.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertIsNone(signin.redeem(raw))

    def test_user_for_creates_then_reuses_a_non_staff_verified_user(self):
        add(self.cohort, "ann@x.com", full_name="Ann Wanjiku")
        user = signin.user_for("ann@x.com")
        self.assertEqual((user.username, user.email), ("ann@x.com", "ann@x.com"))
        self.assertTrue(user.email_verified)
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.is_staff)
        self.assertEqual((user.first_name, user.last_name), ("Ann", "Wanjiku"))

        self.assertEqual(signin.user_for("  ANN@x.com ").pk, user.pk)
        self.assertEqual(User.objects.filter(email="ann@x.com").count(), 1)

        add(self.cohort, "boss@x.com")
        User.objects.create_user("boss", "boss@x.com", "pw12345678", is_staff=True)
        self.assertIsNone(signin.user_for("boss@x.com"))

    def test_tokens_for_gives_a_thirty_day_refresh_token(self):
        add(self.cohort, "ann@x.com")
        user = signin.user_for("ann@x.com")
        tokens = signin.tokens_for(user)
        refresh = RefreshToken(tokens["refresh"])
        self.assertAlmostEqual(refresh["exp"] - refresh["iat"], 30 * 24 * 3600, delta=5)
        self.assertTrue(tokens["access"])


from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from cohorts.member_views import SigninRequestView

GENERIC = "If you've applied to a cohort, we've emailed you a sign-in link."
REQUEST_URL = "/api/members/signin/request/"


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SigninRequestTests(TestCase):
    def setUp(self):
        cache.clear()  # the 'email' throttle scope is shared with other tests
        self.cohort = make_cohort("Alpha")
        self.client = APIClient()

    def ask(self, email):
        return self.client.post(REQUEST_URL, {"email": email}, format="json")

    def test_known_email_gets_one_link_by_email(self):
        add(self.cohort, "ann@x.com")
        r = self.ask("ann@x.com")
        self.assertEqual((r.status_code, r.json()["message"]), (200, GENERIC))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ann@x.com"])
        body = mail.outbox[0].body
        self.assertIn("/signin/verify?token=", body)
        self.assertIn("15 minutes", body)
        self.assertIn("works once", body)
        self.assertEqual(LoginLink.objects.count(), 1)

    def test_unknown_staff_superuser_and_inactive_emails_get_the_same_answer_and_no_mail(self):
        add(self.cohort, "known@x.com")
        known = self.ask("known@x.com")
        cache.clear()
        for email, make in (
            ("nobody@x.com", None),
            ("staff@x.com", lambda: User.objects.create_user("s", "staff@x.com", "pw12345678", is_staff=True)),
            ("root@x.com", lambda: User.objects.create_superuser("r", "root@x.com", "pw12345678")),
            ("off@x.com", lambda: User.objects.create_user("o", "off@x.com", "pw12345678", is_active=False)),
        ):
            add(self.cohort, email) if make else None
            make and make()
            mail.outbox.clear()
            before = LoginLink.objects.count()
            r = self.ask(email)
            self.assertEqual(r.content, known.content, email)  # identical body: nothing to learn from it
            self.assertEqual(len(mail.outbox), 0, email)
            self.assertEqual(LoginLink.objects.count(), before, email)

    def test_second_request_within_a_minute_sends_nothing(self):
        add(self.cohort, "ann@x.com")
        self.ask("ann@x.com")
        r = self.ask("ann@x.com")
        self.assertEqual(r.status_code, 200)
        self.assertEqual((len(mail.outbox), LoginLink.objects.count()), (1, 1))

    def test_case_and_spaces_are_ignored(self):
        add(self.cohort, "ann@x.com")
        self.assertEqual(self.ask("  ANN@x.com ").status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ann@x.com"])

    def test_missing_or_malformed_email_is_rejected(self):
        self.assertEqual(self.client.post(REQUEST_URL, {}, format="json").status_code, 400)
        self.assertEqual(self.ask("not-an-email").status_code, 400)
        self.assertEqual(self.client.post(REQUEST_URL, ["a@x.com"], format="json").status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_mail_failure_still_looks_like_success(self):
        add(self.cohort, "ann@x.com")
        with mock.patch("cohorts.emails.send_mail", side_effect=OSError("smtp down")), \
                self.assertLogs("cohorts.emails", "ERROR"):
            r = self.ask("ann@x.com")
        self.assertEqual((r.status_code, r.json()["message"]), (200, GENERIC))

    def test_uses_the_email_throttle_scope(self):
        self.assertEqual(SigninRequestView.throttle_scope, "email")

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _send(subject, body, to):
    """Best effort: a mail failure is logged and never fails the request."""
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to])
    except Exception:
        logger.exception("Cohort email to %s failed", to)


def send_application_received(m):
    _send(
        f"Application received: {m.cohort.title}",
        f"Hi {m.full_name},\n\n"
        f"Thanks for applying to {m.cohort.title} as a {m.get_role_display().lower()}. "
        "We've received your application and will email you once it has been reviewed.\n\n"
        "— The A Million Techies team",
        m.email,
    )


def send_decision(m):
    """Email the applicant when an admin approves or rejects them. Other statuses send nothing."""
    if m.status == m.STATUS_APPROVED:
        mentor = f" Your mentor is {m.mentor.full_name}." if m.mentor_id else ""
        _send(
            f"You're in: {m.cohort.title}",
            f"Hi {m.full_name},\n\n"
            f"Good news: your application to {m.cohort.title} as a {m.get_role_display().lower()} "
            f"has been approved.{mentor} We'll be in touch with next steps.\n\n"
            "— The A Million Techies team",
            m.email,
        )
    elif m.status == m.STATUS_REJECTED:
        _send(
            f"Update on your application: {m.cohort.title}",
            f"Hi {m.full_name},\n\n"
            f"Thank you for applying to {m.cohort.title}. Unfortunately we can't offer you a place "
            "this time. We appreciate your interest and hope you'll apply again.\n\n"
            "— The A Million Techies team",
            m.email,
        )


def send_signin_link(email, raw_token):
    link = f"{settings.FRONTEND_URL}/signin/verify?token={raw_token}"
    _send(
        "Your sign-in link for A Million Techies",
        "Hi,\n\n"
        f"Use this link to sign in:\n{link}\n\n"
        "It works once and expires in 15 minutes.\n\n"
        "If you didn't ask for this, you can ignore this email.\n\n"
        "— The A Million Techies team",
        email,
    )

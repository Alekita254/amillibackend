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

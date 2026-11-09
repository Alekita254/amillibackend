"""Passwordless sign-in for people who applied to a cohort."""
import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CohortMembership, LoginLink

LINK_TTL = timedelta(minutes=15)
COOLDOWN = timedelta(seconds=60)
DAILY_WINDOW = timedelta(hours=24)
DAILY_LIMIT = 10  # links per email per 24 hours, so nobody can be flooded with mail
SESSION_REFRESH_LIFETIME = timedelta(days=30)

User = get_user_model()


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def normalise(email: str) -> str:
    return (email or "").strip().lower()


def _blocked(email: str) -> bool:
    """email is not unique on User, so one staff/inactive account blocks the address."""
    return User.objects.filter(email__iexact=email).filter(
        Q(is_staff=True) | Q(is_superuser=True) | Q(is_active=False)
    ).exists()


def can_sign_in(email: str) -> bool:
    email = normalise(email)
    if not email or not CohortMembership.objects.filter(email__iexact=email).exists():
        return False
    return not _blocked(email)


def issue_link(email: str):
    """Create a link and return the raw token, or None when not allowed or inside the cooldown."""
    email = normalise(email)
    if not can_sign_in(email):
        return None
    now = timezone.now()
    if LoginLink.objects.filter(email=email, created_at__gt=now - COOLDOWN).exists():
        return None
    # Used and expired links stay for a day because they count toward the daily limit.
    LoginLink.objects.filter(email=email, created_at__lt=now - DAILY_WINDOW).delete()
    if LoginLink.objects.filter(email=email, created_at__gt=now - DAILY_WINDOW).count() >= DAILY_LIMIT:
        return None
    raw = secrets.token_urlsafe(32)
    LoginLink.objects.create(email=email, token_hash=hash_token(raw), expires_at=now + LINK_TTL)
    return raw


def redeem(raw: str):
    """Mark a link used and return it. The conditional UPDATE makes this single-use even under races."""
    if not raw:
        return None
    now = timezone.now()
    digest = hash_token(raw)
    claimed = LoginLink.objects.filter(
        token_hash=digest, used_at__isnull=True, expires_at__gt=now
    ).update(used_at=now)
    return LoginLink.objects.get(token_hash=digest) if claimed == 1 else None


def _find_user(email: str):
    """The verified account for this email. An unverified one proves nothing about who owns the mailbox:
    /api/register/ creates unverified accounts for any address, so adopting one would hand it to a stranger."""
    return User.objects.filter(email__iexact=email, email_verified=True).order_by("pk").first()


def user_for(email: str):
    """The non-staff account for this email, created on first use. None if the address is blocked."""
    email = normalise(email)
    if _blocked(email):
        return None
    existing = _find_user(email)
    if existing:
        return existing

    first = CohortMembership.objects.filter(email__iexact=email).order_by("created_at").first()
    parts = (first.full_name if first else "").split(None, 1)
    username, n = email[:150], 1
    while User.objects.filter(username__iexact=username).exists():
        n += 1
        username = f"{email[:140]}#{n}"
    user = User(
        username=username,
        email=email,
        email_verified=True,
        first_name=parts[0][:150] if parts else "",
        last_name=parts[1][:150] if len(parts) > 1 else "",
    )
    user.set_unusable_password()
    user.save()

    # Two first sign-ins racing both create an account; the oldest one wins and the other is dropped.
    winner = _find_user(email)
    if winner and winner.pk != user.pk:
        user.delete()
        return winner
    return user


def tokens_for(user) -> dict:
    refresh = RefreshToken.for_user(user)
    refresh.set_exp(lifetime=SESSION_REFRESH_LIFETIME)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}

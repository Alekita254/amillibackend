"""Self-service endpoints for people who applied to a cohort (no staff access)."""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from api.serializers import UserProfileSerializer
from api.utils import custom_response, error_response

from . import signin
from .emails import send_signin_link
from .member_serializers import ProfileSerializer, membership_payload
from .models import CohortMembership

# The same words for every address, so the endpoint can't be used to find out who applied.
INVALID_LINK_MESSAGE = "This sign-in link has expired or was already used. Request a new one."
GENERIC_REQUEST_MESSAGE = "If you've applied to a cohort, we've emailed you a sign-in link."


class SigninRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email"

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        email = signin.normalise(str(data.get("email", "")))
        try:
            validate_email(email)
        except DjangoValidationError:
            return custom_response(success=False, message="Enter a valid email address.", status_code=400)

        raw = signin.issue_link(email)  # None unless eligible and outside the cooldown
        if raw:
            send_signin_link(email, raw)
        return custom_response(success=True, message=GENERIC_REQUEST_MESSAGE)


class SigninVerifyView(APIView):
    """Swap a one-time link for the same login payload the admin login returns."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "signin_verify"

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        link = signin.redeem(str(data.get("token", "")))
        user = signin.user_for(link.email) if link else None  # None also covers staff/inactive
        if user is None:
            return custom_response(success=False, message=INVALID_LINK_MESSAGE, status_code=400)
        return custom_response(
            success=True,
            message="Signed in",
            data={"user": UserProfileSerializer(user).data, "tokens": signin.tokens_for(user)},
        )


def _mine(request):
    """The signed-in person's own applications, matched by email."""
    email = (request.user.email or "").strip()
    # An account whose email was never confirmed (anyone can register one with any address) must see nothing.
    if not email or not request.user.email_verified:
        return CohortMembership.objects.none()
    return CohortMembership.objects.filter(email__iexact=email).select_related("cohort", "mentor")


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        return custom_response(
            success=True,
            message="Retrieved successfully",
            data={
                "email": user.email,
                "name": user.get_full_name() or user.username,
                "memberships": [membership_payload(m) for m in _mine(request).order_by("-created_at")],
            },
        )


class MyMembershipView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        membership = get_object_or_404(_mine(request), pk=pk)  # someone else's id is a 404
        serializer = ProfileSerializer(membership, data=request.data, partial=True)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            return error_response(exc)
        serializer.save()
        membership.refresh_from_db()
        return custom_response(success=True, message="Profile updated", data=membership_payload(membership))

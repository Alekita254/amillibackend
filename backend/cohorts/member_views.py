"""Self-service endpoints for people who applied to a cohort (no staff access)."""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from rest_framework import permissions
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from api.serializers import UserProfileSerializer
from api.utils import custom_response

from . import signin
from .emails import send_signin_link

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

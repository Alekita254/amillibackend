from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class OptionalJWTAuthentication(JWTAuthentication):
    """An expired/invalid token is treated as anonymous, so public endpoints keep working."""

    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except InvalidToken:
            return None

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailBackend(ModelBackend):
    """
    Authenticate using email instead of username
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username or kwargs.get('email')
        if not email or password is None:
            return None
        # email isn't unique on AbstractUser; take the first match
        user = User.objects.filter(email__iexact=email).order_by('pk').first()
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

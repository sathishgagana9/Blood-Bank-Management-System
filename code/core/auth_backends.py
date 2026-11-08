"""Lets users log in with either their username or their e-mail address (FR-02)."""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from .us03_invalid_login_error import us03_is_locked


class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        username = username or kwargs.get(User.USERNAME_FIELD)
        if not username or password is None:
            return None
        if us03_is_locked(username):  # US-03: too many failed attempts
            return None
        user = User.objects.filter(Q(username__iexact=username) | Q(email__iexact=username)).first()
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

"""US-03 Invalid Login Error.

Tasks: a clear, single error message for wrong credentials (never says whether the username or the
password was wrong) -> shown on the US-02 login page.
"""
from datetime import timedelta

from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q
from django.utils import timezone

from .models import ActivityLog, User

MAX_FAILED_ATTEMPTS = 5   # FR-02 / test case: account is locked after the 5th failed attempt
LOCKOUT_MINUTES = 15
US03_LOCKED_MESSAGE = f"Account locked after {MAX_FAILED_ATTEMPTS} failed attempts. Please try again in {LOCKOUT_MINUTES} minutes."


def us03_is_locked(identifier):
    """True when the account behind `identifier` (username or e-mail) failed to log in 5 times in the last 15 minutes.
    Failures typed as the username and as the e-mail address are counted together."""
    if not identifier:
        return False
    since = timezone.now() - timedelta(minutes=LOCKOUT_MINUTES)
    user = User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier)).first()
    names = {identifier}
    if user:
        names |= {user.username, user.email}
        last_ok = ActivityLog.objects.filter(user=user, action="LOGIN").first()
        if last_ok and last_ok.created_at > since:  # a successful login resets the counter
            since = last_ok.created_at
    matches = Q()
    for name in filter(None, names):
        matches |= Q(details__iexact=name)
    failures = ActivityLog.objects.filter(matches, action="LOGIN_FAILED", created_at__gt=since)
    return failures.count() >= MAX_FAILED_ATTEMPTS

US03_INVALID_LOGIN_MESSAGE = "Invalid username/email or password. Please check your credentials and try again."


class US03LoginForm(AuthenticationForm):
    """Login form whose error messages are the US-03 messages."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Username or email"

    error_messages = {
        "invalid_login": US03_INVALID_LOGIN_MESSAGE,
        "inactive": "This account is inactive.",
    }


def us03_invalid_login_error(form):
    """Make sure the failed login shows the US-03 error on the page."""
    identifier = form.data.get("username", "").strip()
    form.errors.pop("__all__", None)  # replace the default error with exactly one US-03 message
    form.add_error(None, US03_LOCKED_MESSAGE if us03_is_locked(identifier) else US03_INVALID_LOGIN_MESSAGE)

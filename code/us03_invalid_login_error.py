"""US-03 Invalid Login Error helper for US-02."""
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm


class US03LoginForm(AuthenticationForm):
    """Authentication form for US-02 login with US-03 error feedback."""

    pass


def us03_invalid_login_error(form):
    """Attach clear error message when login credentials are invalid (US-03)."""
    pass

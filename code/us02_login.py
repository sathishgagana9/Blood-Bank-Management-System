"""US-02 Login (and logout).

Tasks: login form (US-03 supplies the invalid-login error) -> view (start session) -> GUI page -> URLs.
"""
from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect
from django.urls import path

from .common import FORM_FIELDS, render_page
from .us03_invalid_login_error import US03LoginForm, us03_invalid_login_error

# ---- GUI
TEMPLATE = (
    """<div class="card narrow"><h2>US-02 Login</h2>
<form method="post" novalidate>{% csrf_token %}<input type="hidden" name="next" value="{{ next }}">"""
    + FORM_FIELDS
    + """<button class="btn" type="submit">Log in</button></form>
<p>No account? <a href="{% url 'us01_register_user' %}">Register</a></p></div>"""
)


# ---- Views
def us02_login(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = US03LoginForm(request, data=request.POST or None)
    next_url = request.POST.get("next") or request.GET.get("next") or ""
    if request.method == "POST":
        if form.is_valid():
            login(request, form.get_user())
            if next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect("home")
        us03_invalid_login_error(form)  # US-03
    return render_page(request, TEMPLATE, {"form": form, "next": next_url})


def us02_logout(request):
    if request.method == "POST":
        logout(request)
        messages.info(request, "You have been logged out.")
    return redirect("us02_login")


URLS = [
    path("login/", us02_login, name="us02_login"),
    path("logout/", us02_logout, name="us02_logout"),
]

"""US-01 Register User.

Tasks: registration form (validation) -> view (create account, donor role) -> GUI page -> URL.
"""
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect
from django.urls import path

from .common import FORM_FIELDS, render_page
from .models import User


# ---- Form
class US01RegisterUserForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "address")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("first_name", "last_name", "email", "phone", "address"):
            self.fields[name].required = True
        self.fields["address"].widget.attrs["rows"] = 3

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.ROLE_DONOR  # US-04: higher roles are granted only by an administrator
        if commit:
            user.save()
        return user


# ---- GUI
TEMPLATE = (
    """<div class="card narrow"><h2>US-01 Register User</h2>
<form method="post" novalidate>{% csrf_token %}"""
    + FORM_FIELDS
    + """<button class="btn" type="submit">Create account</button></form>
<p>Already registered? <a href="{% url 'us02_login' %}">Log in</a></p></div>"""
)


# ---- View
def us01_register_user(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = US01RegisterUserForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Registration successful. Please log in.")
        return redirect("us02_login")
    return render_page(request, TEMPLATE, {"form": form})


URLS = [path("register/", us01_register_user, name="us01_register_user")]

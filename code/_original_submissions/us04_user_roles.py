"""US-04 User Roles.

Tasks: role-based access decorator used by every other story -> administrator page to assign roles
(donor / staff / administrator) -> GUI table -> URLs.
"""
from functools import wraps

from django import forms
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import path

from .common import render_page
from .models import User

STAFF_ROLES = (User.ROLE_STAFF, User.ROLE_ADMIN)
ADMIN_ROLES = (User.ROLE_ADMIN,)
ALL_ROLES = (User.ROLE_DONOR, User.ROLE_STAFF, User.ROLE_ADMIN)


def us04_role_required(*roles):
    """Anonymous users go to the login page; logged-in users with the wrong role get a 403."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role not in roles:
                raise PermissionDenied("You do not have permission to access this page.")
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


# ---- Form
class US04UserRoleForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("role",)


# ---- GUI
TEMPLATE = """<div class="card"><h2>US-04 User Roles</h2>
<p>Donors register themselves; promote users to staff or administrator here.</p>
<table><tr><th>Username</th><th>Name</th><th>Email</th><th>Role</th><th></th></tr>
{% for u, form in rows %}
<tr><td>{{ u.username }}</td><td>{{ u.get_full_name }}</td><td>{{ u.email }}</td><td>{{ form.role }}</td>
<td><form id="roleform-{{ u.pk }}" method="post" action="{% url 'us04_update_user_role' u.pk %}">{% csrf_token %}</form>
<button class="btn" type="submit" form="roleform-{{ u.pk }}"{% if u == user %} disabled{% endif %}>Save</button></td></tr>
{% endfor %}</table></div>"""


# ---- Views
@us04_role_required(*ADMIN_ROLES)
def us04_user_roles(request):
    rows = []
    for u in User.objects.order_by("username"):
        form = US04UserRoleForm(instance=u, prefix=f"u{u.pk}")
        form.fields["role"].widget.attrs["form"] = f"roleform-{u.pk}"  # tie the select to its own <form>
        rows.append((u, form))
    return render_page(request, TEMPLATE, {"rows": rows})


@us04_role_required(*ADMIN_ROLES)
def us04_update_user_role(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        form = US04UserRoleForm(request.POST, instance=target, prefix=f"u{target.pk}")
        if target == request.user:
            messages.error(request, "You cannot change your own role.")
        elif form.is_valid():
            form.save()
            messages.success(request, f"Role for {target.username} updated to {target.get_role_display()}.")
        else:
            messages.error(request, "Invalid role selected.")
    return redirect("us04_user_roles")


URLS = [
    path("roles/", us04_user_roles, name="us04_user_roles"),
    path("roles/<int:user_id>/update/", us04_update_user_role, name="us04_update_user_role"),
]

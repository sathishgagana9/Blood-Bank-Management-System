"""US-04 User Roles.

Tasks: role definitions & access control decorator -> assign role form -> views (manage roles, unauthorized) -> GUI pages -> URLs.
"""
from functools import wraps

from django import forms
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import path

from .common import render_page
from .models import User

# ---- Roles
ROLE_DONOR = "donor"
ROLE_STAFF = "staff"
ROLE_ADMIN = "admin"

ROLE_CHOICES = (
    (ROLE_DONOR, "Donor"),
    (ROLE_STAFF, "Staff"),
    (ROLE_ADMIN, "Administrator"),
)

DONOR_ROLES = (ROLE_DONOR,)
STAFF_ROLES = (ROLE_STAFF, ROLE_ADMIN)
ADMIN_ROLES = (ROLE_ADMIN,)
ALL_ROLES = (ROLE_DONOR, ROLE_STAFF, ROLE_ADMIN)


# ---- Decorator
def us04_role_required(*allowed_roles):
    """Enforce role-based access control on views.

    Acceptance criteria:
    - Donors can access donor functions.
    - Staff can access staff functions.
    - Administrators can access administrator functions.
    - Users cannot access functions outside their permissions.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                next_url = request.get_full_path()
                return redirect(f"/login/?next={next_url}")
            user_role = getattr(request.user, "role", None) or (
                ROLE_ADMIN if getattr(request.user, "is_superuser", False) else ROLE_DONOR
            )
            if user_role not in allowed_roles and not getattr(request.user, "is_superuser", False):
                return render_page(
                    request,
                    TEMPLATE_UNAUTHORIZED,
                    {"required_roles": allowed_roles, "current_role": user_role},
                    status=403,
                )
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


# ---- Form
class US04AssignRoleForm(forms.Form):
    user_id = forms.IntegerField(widget=forms.HiddenInput)
    role = forms.ChoiceField(choices=ROLE_CHOICES, label="Assign Role")


# ---- GUI
TEMPLATE_ASSIGN = """<div class="card"><h2>US-04 Manage User Roles</h2>
<p>Assign appropriate roles to users to control access to system functions.</p>
<table>
 <tr><th>Username</th><th>Name</th><th>Email</th><th>Current Role</th><th>Assign New Role</th></tr>
 {% for u in users %}
 <tr>
  <td>{{ u.username }}</td>
  <td>{{ u.get_full_name|default:u.username }}</td>
  <td>{{ u.email }}</td>
  <td><span class="badge">{{ u.role|title }}</span></td>
  <td>
   <form method="post" style="display:inline-flex;gap:0.5rem;align-items:center;">{% csrf_token %}
    <input type="hidden" name="user_id" value="{{ u.pk }}">
    <select name="role">
     {% for val, label in role_choices %}
     <option value="{{ val }}" {% if u.role == val %}selected{% endif %}>{{ label }}</option>
     {% endfor %}
    </select>
    <button class="btn" type="submit">Update Role</button>
   </form>
  </td>
 </tr>
 {% empty %}
 <tr><td colspan="5">No registered users found.</td></tr>
 {% endfor %}
</table></div>"""

TEMPLATE_UNAUTHORIZED = """<div class="card narrow"><h2>403 — Access Denied</h2>
<p>You do not have permission to access this function.</p>
<p>Your current role (<strong>{{ current_role|title }}</strong>) does not have access. Required role(s): <strong>{{ required_roles|join:", "|title }}</strong>.</p>
<p><a class="btn" href="{% url 'home' %}">Return Home</a></p></div>"""


# ---- Views
@us04_role_required(*ADMIN_ROLES)
def us04_assign_role(request):
    if request.method == "POST":
        form = US04AssignRoleForm(request.POST)
        if form.is_valid():
            uid = form.cleaned_data["user_id"]
            new_role = form.cleaned_data["role"]
            try:
                target_user = User.objects.get(pk=uid)
                target_user.role = new_role
                target_user.save()
                messages.success(request, f"Role for '{target_user.username}' successfully changed to {new_role}.")
            except User.DoesNotExist:
                messages.error(request, "Selected user does not exist.")
            return redirect("us04_assign_role")
    users = User.objects.all().order_by("username")
    return render_page(
        request,
        TEMPLATE_ASSIGN,
        {"users": users, "role_choices": ROLE_CHOICES},
    )


def us04_unauthorized(request):
    return render_page(request, TEMPLATE_UNAUTHORIZED, {}, status=403)


URLS = [
    path("admin/roles/", us04_assign_role, name="us04_assign_role"),
    path("unauthorized/", us04_unauthorized, name="us04_unauthorized"),
]

"""US-29 Assign Roles.

Tasks: role form -> view (change a user's role; cannot change your own role, a superuser's role, or demote the
last active administrator; logged) -> GUI page with role summary and role filter -> URLs.
Builds on US-04 (which defines the roles and the access-check decorator).
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import path

from .common import render_page
from .models import ActivityLog, User
from .us04_user_roles import ADMIN_ROLES, US04UserRoleForm, us04_role_required

# ---- GUI
TEMPLATE = """<div class="card"><h2>US-29 Assign Roles</h2>
<p>{% for label, count in summary %}<strong>{{ label }}:</strong> {{ count }} &nbsp; {% endfor %}</p>
<form method="get" class="filters"><div><label>Show role</label>
<select name="role"><option value="">All roles</option>{% for code, label in roles %}<option value="{{ code }}"{% if code == selected %} selected{% endif %}>{{ label }}</option>{% endfor %}</select></div>
<div><button class="btn" type="submit">Filter</button></div></form>
<table><tr><th>Username</th><th>Name</th><th>Current role</th><th>New role</th><th></th></tr>
{% for u, form in rows %}
<tr><td>{{ u.username }}</td><td>{{ u.get_full_name }}</td><td>{{ u.get_role_display }}</td><td>{{ form.role }}</td>
<td><form id="assign-{{ u.pk }}" method="post" action="{% url 'us29_update_user_role' u.pk %}">{% csrf_token %}</form>
<button class="btn" style="margin:0" type="submit" form="assign-{{ u.pk }}"{% if u == user %} disabled{% endif %}>Assign</button></td></tr>
{% empty %}<tr><td colspan="5">No users found.</td></tr>{% endfor %}
</table></div>"""


# ---- Views
@us04_role_required(*ADMIN_ROLES)
def us29_assign_roles(request):
    selected = request.GET.get("role", "")
    users = User.objects.order_by("username")
    if selected:
        users = users.filter(role=selected)
    rows = []
    for u in users:
        form = US04UserRoleForm(instance=u, prefix=f"u{u.pk}")
        form.fields["role"].widget.attrs["form"] = f"assign-{u.pk}"
        rows.append((u, form))
    summary = [(label, User.objects.filter(role=code).count()) for code, label in User.ROLE_CHOICES]
    return render_page(request, TEMPLATE, {"rows": rows, "summary": summary, "roles": User.ROLE_CHOICES, "selected": selected})


@us04_role_required(*ADMIN_ROLES)
def us29_update_user_role(request, user_pk):
    target = get_object_or_404(User, pk=user_pk)
    if request.method == "POST":
        form = US04UserRoleForm(request.POST, instance=target, prefix=f"u{target.pk}")
        if not form.is_valid():
            messages.error(request, "Invalid role selected.")
        elif target == request.user:
            messages.error(request, "You cannot change your own role.")
        elif target.is_superuser:
            messages.error(request, "Superuser accounts are always Administrators.")
        else:
            old_role = User.objects.get(pk=target.pk).role
            new_role = form.cleaned_data["role"]
            if old_role == User.ROLE_ADMIN and new_role != User.ROLE_ADMIN and User.objects.filter(role=User.ROLE_ADMIN, is_active=True).count() <= 1:
                messages.error(request, "At least one active Administrator must remain.")
            else:
                form.save()
                ActivityLog.record(request.user, "ROLE_ASSIGNED", f"{target.username}: {old_role} -> {new_role}")
                messages.success(request, f"{target.username} is now {target.get_role_display()}.")
    return redirect("us29_assign_roles")


URLS = [
    path("manage/roles/", us29_assign_roles, name="us29_assign_roles"),
    path("manage/roles/<int:user_pk>/assign/", us29_update_user_role, name="us29_update_user_role"),
]

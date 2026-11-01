"""US-28 Manage Users.

Tasks: create / edit forms -> views (search list, create account with a role, edit details, activate /
deactivate; accounts are never deleted so history stays intact) -> GUI pages -> URLs. Administrator only.
Changing someone's role afterwards is US-29.
"""
from django import forms
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import path

from .common import FORM_FIELDS, render_page
from .models import ActivityLog, User
from .us04_user_roles import ADMIN_ROLES, us04_role_required


# ---- Forms
class US28CreateUserForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "address", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["address"].widget.attrs["rows"] = 3


class US28EditUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone", "address", "is_active")
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}


# ---- GUI
LIST_TEMPLATE = """<div class="card"><h2>US-28 Manage Users</h2>
<a class="btn" href="{% url 'us28_create_user' %}">Create user</a>
<form method="get" class="filters" style="margin-top:12px"><div><label>Search</label><input name="q" value="{{ q }}" placeholder="username, name or email"></div>
<div><button class="btn" type="submit">Search</button></div></form>
<table><tr><th>Username</th><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th></th></tr>
{% for u in users %}
<tr><td>{{ u.username }}</td><td>{{ u.get_full_name }}</td><td>{{ u.email }}</td><td>{{ u.get_role_display }}</td>
<td>{% if u.is_active %}Active{% else %}Inactive{% endif %}</td>
<td><a href="{% url 'us28_edit_user' u.pk %}">Edit</a>
{% if u != user %}<form class="inline" method="post" action="{% url 'us28_toggle_user' u.pk %}">{% csrf_token %}<button type="submit" style="cursor:pointer">{% if u.is_active %}Deactivate{% else %}Activate{% endif %}</button></form>{% endif %}</td></tr>
{% empty %}<tr><td colspan="6">No users found.</td></tr>{% endfor %}
</table></div>"""

FORM_TEMPLATE = (
    """<div class="card narrow"><h2>US-28 {{ title }}</h2>
<form method="post" novalidate>{% csrf_token %}"""
    + FORM_FIELDS
    + """<button class="btn" type="submit">Save</button>
<a class="btn secondary" href="{% url 'us28_manage_users' %}">Cancel</a></form></div>"""
)


# ---- Views
@us04_role_required(*ADMIN_ROLES)
def us28_manage_users(request):
    q = request.GET.get("q", "").strip()
    users = User.objects.order_by("username")
    if q:
        users = users.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
    return render_page(request, LIST_TEMPLATE, {"users": users, "q": q})


@us04_role_required(*ADMIN_ROLES)
def us28_create_user(request):
    form = US28CreateUserForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        new_user = form.save()
        ActivityLog.record(request.user, "USER_CREATED", f"{new_user.username} ({new_user.role})")
        messages.success(request, f"User '{new_user.username}' created as {new_user.get_role_display()}.")
        return redirect("us28_manage_users")
    return render_page(request, FORM_TEMPLATE, {"form": form, "title": "Create User"})


@us04_role_required(*ADMIN_ROLES)
def us28_edit_user(request, user_pk):
    target = get_object_or_404(User, pk=user_pk)
    form = US28EditUserForm(request.POST or None, instance=target)
    if request.method == "POST" and form.is_valid():
        if target == request.user and not form.cleaned_data["is_active"]:
            form.add_error("is_active", "You cannot deactivate your own account.")
        else:
            form.save()
            ActivityLog.record(request.user, "USER_UPDATED", target.username)
            messages.success(request, f"User '{target.username}' updated.")
            return redirect("us28_manage_users")
    return render_page(request, FORM_TEMPLATE, {"form": form, "title": f"Edit {target.username}"})


@us04_role_required(*ADMIN_ROLES)
def us28_toggle_user(request, user_pk):
    target = get_object_or_404(User, pk=user_pk)
    if request.method == "POST":
        if target == request.user:
            messages.error(request, "You cannot deactivate your own account.")
        else:
            target.is_active = not target.is_active
            target.save()
            ActivityLog.record(request.user, "USER_ACTIVATED" if target.is_active else "USER_DEACTIVATED", target.username)
            messages.success(request, f"'{target.username}' is now {'active' if target.is_active else 'inactive'}.")
    return redirect("us28_manage_users")


URLS = [
    path("manage/users/", us28_manage_users, name="us28_manage_users"),
    path("manage/users/create/", us28_create_user, name="us28_create_user"),
    path("manage/users/<int:user_pk>/edit/", us28_edit_user, name="us28_edit_user"),
    path("manage/users/<int:user_pk>/toggle/", us28_toggle_user, name="us28_toggle_user"),
]

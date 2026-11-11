"""US-33 View System Activities.

Tasks: activity log (automatic entries for login / logout / failed login, registrations, donations, plus every
Sprint 2 action that calls ActivityLog.record) -> filter form -> paged GUI table -> URL. Administrator only.
The signal handlers below are connected in core/apps.py when Django starts.
"""
from django import forms
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.core.paginator import Paginator
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import path

from .common import render_page
from .models import ActivityLog, Donation, User
from .us04_user_roles import ADMIN_ROLES, us04_role_required


# ---- Automatic logging
@receiver(user_logged_in)
def _log_login(sender, request, user, **kwargs):
    ActivityLog.record(user, "LOGIN", user.username)


@receiver(user_logged_out)
def _log_logout(sender, request, user, **kwargs):
    ActivityLog.record(user, "LOGOUT", getattr(user, "username", ""))


@receiver(user_login_failed)
def _log_login_failed(sender, credentials, **kwargs):
    ActivityLog.record(None, "LOGIN_FAILED", str(credentials.get("username", ""))[:100])


@receiver(post_save, sender=User)
def _log_user_created(sender, instance, created, **kwargs):
    if created:
        ActivityLog.record(None, "USER_REGISTERED", f"{instance.username} ({instance.role})")


@receiver(post_save, sender=Donation)
def _log_donation(sender, instance, created, update_fields, **kwargs):
    """Only the creation is logged here (second save, when DON-00001 is assigned).
    Donor and status changes are logged by their views, which know the logged-in user."""
    if update_fields and "donation_id" in update_fields:
        ActivityLog.record(instance.recorded_by, "DONATION_RECORDED", f"{instance.donation_id} {instance.blood_group} x{instance.quantity} status={instance.status}")


# ---- Form
class US33ActivityFilterForm(forms.Form):
    user = forms.CharField(required=False, label="Username")
    action = forms.CharField(required=False, label="Action contains")
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="From date")
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="To date")


# ---- GUI
TEMPLATE = """<div class="card"><h2>US-33 System Activities</h2>
<form method="get" class="filters">
 <div>{{ form.user.label_tag }}{{ form.user }}</div>
 <div>{{ form.action.label_tag }}{{ form.action }}</div>
 <div>{{ form.date_from.label_tag }}{{ form.date_from }}</div>
 <div>{{ form.date_to.label_tag }}{{ form.date_to }}</div>
 <div><button class="btn" type="submit">Filter</button></div>
</form>
<table><tr><th>When</th><th>User</th><th>Action</th><th>Details</th></tr>
{% for a in page.object_list %}
<tr><td>{{ a.created_at|date:"d M Y H:i:s" }}</td><td>{{ a.user.username|default:"System / anonymous" }}</td><td>{{ a.action }}</td><td>{{ a.details }}</td></tr>
{% empty %}<tr><td colspan="4">No activity recorded.</td></tr>{% endfor %}
</table>
<p>Page {{ page.number }} of {{ page.paginator.num_pages }}
{% if page.has_previous %}<a href="?{{ query }}&amp;page={{ page.previous_page_number }}">&laquo; Newer</a>{% endif %}
{% if page.has_next %}<a href="?{{ query }}&amp;page={{ page.next_page_number }}">Older &raquo;</a>{% endif %}</p></div>"""


# ---- View
@us04_role_required(*ADMIN_ROLES)
def us33_view_system_activities(request):
    params = request.GET.copy()
    page_number = params.pop("page", ["1"])[0]
    form = US33ActivityFilterForm(params or None)
    logs = ActivityLog.objects.select_related("user")
    if form.is_valid():
        d = form.cleaned_data
        if d["user"]:
            logs = logs.filter(user__username__icontains=d["user"])
        if d["action"]:
            logs = logs.filter(action__icontains=d["action"])
        if d["date_from"]:
            logs = logs.filter(created_at__date__gte=d["date_from"])
        if d["date_to"]:
            logs = logs.filter(created_at__date__lte=d["date_to"])
    page = Paginator(logs, 50).get_page(page_number)
    return render_page(request, TEMPLATE, {"form": form, "page": page, "query": params.urlencode()})


URLS = [path("manage/activity/", us33_view_system_activities, name="us33_view_system_activities")]

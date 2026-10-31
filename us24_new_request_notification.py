"""US-24 New Request Notification.

Tasks: notify every staff member and administrator when a blood request is submitted (called from US-18)
-> notification inbox page (also used by US-23, US-25, US-26) with unread count in the menu -> URLs.
"""
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import path, reverse

from .common import render_page
from .models import Notification, User
from .us04_user_roles import ALL_ROLES, STAFF_ROLES, us04_role_required


def us24_notify_new_request(blood_request):
    staff = User.objects.filter(role__in=STAFF_ROLES, is_active=True)
    Notification.send(
        staff, "NEW_REQUEST",
        f"New {blood_request.get_urgency_display().upper()} blood request {blood_request.request_id}: {blood_request.quantity} unit(s) of {blood_request.blood_group} "
        f"{blood_request.get_component_display()} at {blood_request.blood_bank} (needed by {blood_request.required_by}).",
        link=reverse("us19_view_blood_requests"),
    )


# ---- GUI
TEMPLATE = """<div class="card"><h2>US-24 Notifications</h2>
<form method="post" action="{% url 'us24_mark_notifications_read' %}">{% csrf_token %}<button class="btn" type="submit">Mark all as read</button></form>
<table><tr><th>When</th><th>Type</th><th>Message</th></tr>
{% for n in notifications %}
<tr{% if not n.is_read %} style="font-weight:700;background:#fff7e6"{% endif %}><td>{{ n.created_at|date:"d M Y H:i" }}</td><td>{{ n.get_category_display }}</td>
<td>{% if n.link %}<a href="{{ n.link }}">{{ n.message }}</a>{% else %}{{ n.message }}{% endif %}</td></tr>
{% empty %}<tr><td colspan="3">No notifications yet.</td></tr>{% endfor %}
</table></div>"""


# ---- Views
@us04_role_required(*ALL_ROLES)
def us24_view_notifications(request):
    return render_page(request, TEMPLATE, {"notifications": request.user.notifications.all()[:100]})


@us04_role_required(*ALL_ROLES)
def us24_mark_notifications_read(request):
    if request.method == "POST":
        request.user.notifications.filter(is_read=False).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
    return redirect("us24_view_notifications")


URLS = [
    path("notifications/", us24_view_notifications, name="us24_view_notifications"),
    path("notifications/read/", us24_mark_notifications_read, name="us24_mark_notifications_read"),
]

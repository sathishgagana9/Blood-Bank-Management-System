"""US-23 Low Stock Alert.

Tasks: automatic check after every stock change (called from BloodInventory.adjust) -> notify all staff and
administrators (US-24 inbox) -> GUI page listing everything currently low -> URL.
The limit is LOW_STOCK_THRESHOLD in settings.py (default 5 units).
"""
from django.conf import settings
from django.urls import path, reverse

from .common import render_page
from .models import BloodInventory, Notification, User
from .us04_user_roles import STAFF_ROLES, us04_role_required


def us23_threshold():
    return getattr(settings, "LOW_STOCK_THRESHOLD", 5)


def us23_check_low_stock(row, old_quantity):
    """Send an alert when stock went DOWN and is now at or below the threshold."""
    if row.quantity < old_quantity and row.quantity <= us23_threshold():
        staff = User.objects.filter(role__in=STAFF_ROLES, is_active=True)
        Notification.send(
            staff, "LOW_STOCK",
            f"Low stock: {row.blood_bank} has only {row.quantity} unit(s) of {row.blood_group} {row.get_component_display()}.",
            link=reverse("us23_low_stock_alert"),
        )


# ---- GUI
TEMPLATE = """<div class="card"><h2>US-23 Low Stock Alerts</h2>
<p>Showing stock at or below <strong>{{ threshold }}</strong> unit(s).</p>
<table><tr><th>Blood bank</th><th>Blood group</th><th>Component</th><th>Units left</th><th>Last updated</th><th></th></tr>
{% for r in rows %}
<tr><td>{{ r.blood_bank }}</td><td>{{ r.blood_group }}</td><td>{{ r.get_component_display }}</td>
<td style="color:#b00020;font-weight:700">{{ r.quantity }}</td><td>{{ r.updated_at|date:"d M Y H:i" }}</td>
<td><a href="{% url 'us15_update_blood_inventory' %}">Update stock</a></td></tr>
{% empty %}<tr><td colspan="6">No low-stock items. 🎉</td></tr>{% endfor %}
</table></div>"""


# ---- View
@us04_role_required(*STAFF_ROLES)
def us23_low_stock_alert(request):
    rows = BloodInventory.objects.select_related("blood_bank").filter(
        quantity__lte=us23_threshold(), blood_bank__is_active=True
    ).order_by("quantity")
    return render_page(request, TEMPLATE, {"rows": rows, "threshold": us23_threshold()})


URLS = [path("alerts/low-stock/", us23_low_stock_alert, name="us23_low_stock_alert")]

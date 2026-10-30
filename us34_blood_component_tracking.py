"""US-34 Blood Component Separation Tracking (whole blood, plasma, platelets, RBC).

Tasks: view (totals per component, blood group x component grid, units still being processed)
-> GUI tables -> URL.
"""
from django.db.models import Sum
from django.urls import path

from .common import render_page
from .models import BLOOD_GROUPS, BloodInventory, Donation
from .us04_user_roles import STAFF_ROLES, us04_role_required

# ---- GUI
TEMPLATE = """<div class="card"><h2>US-34 Blood Component Separation Tracking</h2>
<h3>Units in inventory by component</h3>
<table><tr>{% for label, total in component_totals %}<th>{{ label }}</th>{% endfor %}</tr>
<tr>{% for label, total in component_totals %}<td>{{ total }}</td>{% endfor %}</tr></table>

<h3>Blood group &times; component</h3>
<table><tr><th>Blood group</th>{% for label in component_labels %}<th>{{ label }}</th>{% endfor %}</tr>
{% for group, cells in matrix %}<tr><td>{{ group }}</td>{% for qty in cells %}<td>{{ qty }}</td>{% endfor %}</tr>{% endfor %}
</table>

<h3>Collected but not yet stored (pending / tested)</h3>
<table><tr>{% for label, total in in_process %}<th>{{ label }}</th>{% endfor %}</tr>
<tr>{% for label, total in in_process %}<td>{{ total }}</td>{% endfor %}</tr></table></div>"""


def _sum(queryset):
    return queryset.aggregate(t=Sum("quantity"))["t"] or 0


# ---- View
@us04_role_required(*STAFF_ROLES)
def us34_blood_component_tracking(request):
    inventory = BloodInventory.objects.all()
    components = Donation.COMPONENT_CHOICES
    in_process = Donation.objects.filter(status__in=[Donation.STATUS_PENDING, Donation.STATUS_TESTED])
    context = {
        "component_labels": [label for _code, label in components],
        "component_totals": [(label, _sum(inventory.filter(component=code))) for code, label in components],
        "matrix": [
            (group, [_sum(inventory.filter(blood_group=group, component=code)) for code, _l in components])
            for group, _g in BLOOD_GROUPS
        ],
        "in_process": [(label, _sum(in_process.filter(component=code))) for code, label in components],
    }
    return render_page(request, TEMPLATE, context)


URLS = [
    path("inventory/components/", us34_blood_component_tracking, name="us34_blood_component_tracking")
]

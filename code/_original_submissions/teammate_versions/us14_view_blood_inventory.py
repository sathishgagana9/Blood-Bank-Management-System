"""US-14 View Blood Inventory.

Tasks: filter form (blood bank, group, component) -> view (list stock + total) -> GUI table -> URL.
"""
from django import forms
from django.db.models import Sum
from django.urls import path

from .common import render_page
from .models import BLOOD_GROUPS, BloodBank, BloodInventory, Donation
from .us04_user_roles import ALL_ROLES, us04_role_required


# ---- Form
class US14InventoryFilterForm(forms.Form):
    blood_bank = forms.ModelChoiceField(
        queryset=BloodBank.objects.filter(is_active=True), required=False, empty_label="All blood banks"
    )
    blood_group = forms.ChoiceField(required=False, choices=[("", "Any blood group")] + BLOOD_GROUPS)
    component = forms.ChoiceField(required=False, choices=[("", "Any component")] + Donation.COMPONENT_CHOICES)


# ---- GUI
TEMPLATE = """<div class="card"><h2>US-14 Blood Inventory</h2>
<form method="get" class="filters">
 <div>{{ form.blood_bank.label_tag }}{{ form.blood_bank }}</div>
 <div>{{ form.blood_group.label_tag }}{{ form.blood_group }}</div>
 <div>{{ form.component.label_tag }}{{ form.component }}</div>
 <div><button class="btn" type="submit">Filter</button></div>
</form>
<p><strong>Total units shown:</strong> {{ total_units }}</p>
<table><tr><th>Blood bank</th><th>Blood group</th><th>Component</th><th>Units available</th><th>Last updated</th></tr>
{% for r in rows %}
<tr><td>{{ r.blood_bank }}</td><td>{{ r.blood_group }}</td><td>{{ r.get_component_display }}</td>
<td>{{ r.quantity }}</td><td>{{ r.updated_at|date:"d M Y H:i" }}</td></tr>
{% empty %}<tr><td colspan="5">No inventory records yet. Stock grows when donations are marked "Stored".</td></tr>{% endfor %}
</table></div>"""


# ---- View
@us04_role_required(*ALL_ROLES)
def us14_view_blood_inventory(request):
    form = US14InventoryFilterForm(request.GET or None)
    rows = BloodInventory.objects.select_related("blood_bank")
    if form.is_valid():
        data = form.cleaned_data
        if data["blood_bank"]:
            rows = rows.filter(blood_bank=data["blood_bank"])
        if data["blood_group"]:
            rows = rows.filter(blood_group=data["blood_group"])
        if data["component"]:
            rows = rows.filter(component=data["component"])
    total = rows.aggregate(total=Sum("quantity"))["total"] or 0
    return render_page(request, TEMPLATE, {"form": form, "rows": rows, "total_units": total})


URLS = [path("inventory/", us14_view_blood_inventory, name="us14_view_blood_inventory")]

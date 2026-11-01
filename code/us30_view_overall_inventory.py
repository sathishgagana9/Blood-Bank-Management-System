"""US-30 View Overall Inventory.

Tasks: overall inventory dashboard (across all registered blood banks and blood groups)
-> aggregated stock matrix & breakdowns by bank and component
-> filter by blood bank / blood group -> GUI page -> URL.
"""
from django import forms
from django.db.models import Sum
from django.urls import path

from .common import render_page
from .models import BLOOD_GROUPS, BloodBank, BloodInventory, Donation
from .us04_user_roles import ADMIN_ROLES, us04_role_required


# ---- Form
class US30FilterForm(forms.Form):
    blood_bank = forms.ModelChoiceField(
        queryset=BloodBank.objects.all(),
        required=False,
        empty_label="All Blood Banks",
        label="Blood Bank",
    )
    blood_group = forms.ChoiceField(
        choices=[("", "All Blood Groups")] + BLOOD_GROUPS,
        required=False,
        label="Blood Group",
    )
    component = forms.ChoiceField(
        choices=[("", "All Components")] + Donation.COMPONENT_CHOICES,
        required=False,
        label="Component",
    )


# ---- GUI
TEMPLATE = """<div class="card">
<h2>US-30 Overall Blood Inventory Dashboard</h2>
<p>Administrator overview to monitor and verify consolidated blood stock across all registered blood banks.</p>

<form method="get" class="filters">
 <div>{{ form.blood_bank.label_tag }}{{ form.blood_bank }}</div>
 <div>{{ form.blood_group.label_tag }}{{ form.blood_group }}</div>
 <div>{{ form.component.label_tag }}{{ form.component }}</div>
 <div><button class="btn" type="submit">Filter Overview</button></div>
</form>

<div style="display:flex;gap:1.5rem;flex-wrap:wrap;margin:1.5rem 0;">
 <div class="card" style="flex:1;min-width:200px;background:#f8fafc;padding:1rem;margin:0;border-left:4px solid #9b1c1c;">
  <div style="font-size:0.85em;color:#666;font-weight:600;">TOTAL BLOOD UNITS</div>
  <div style="font-size:1.8em;font-weight:700;color:#9b1c1c;margin-top:0.25rem;">{{ total_units }} unit(s)</div>
 </div>
 <div class="card" style="flex:1;min-width:200px;background:#f8fafc;padding:1rem;margin:0;border-left:4px solid #2563eb;">
  <div style="font-size:0.85em;color:#666;font-weight:600;">ACTIVE BLOOD BANKS</div>
  <div style="font-size:1.8em;font-weight:700;color:#2563eb;margin-top:0.25rem;">{{ total_banks }} bank(s)</div>
 </div>
 <div class="card" style="flex:1;min-width:200px;background:#f8fafc;padding:1rem;margin:0;border-left:4px solid #16a34a;">
  <div style="font-size:0.85em;color:#666;font-weight:600;">INVENTORY ROWS</div>
  <div style="font-size:1.8em;font-weight:700;color:#16a34a;margin-top:0.25rem;">{{ total_rows }} recorded</div>
 </div>
</div>

<h3>System-wide Stock by Blood Group</h3>
<table>
 <tr>
  <th>Blood Group</th>
  <th>Total Units Available</th>
  <th>Status</th>
 </tr>
 {% for bg, qty in group_summary.items %}
 <tr>
  <td><span class="badge">{{ bg }}</span></td>
  <td><strong>{{ qty }}</strong> unit(s)</td>
  <td>
   {% if qty == 0 %}
    <span class="badge" style="background:#fee2e2;color:#b91c1c;">Out of Stock</span>
   {% elif qty < 5 %}
    <span class="badge" style="background:#fef3c7;color:#d97706;">Low Stock</span>
   {% else %}
    <span class="badge" style="background:#e3f6e8;color:#1e7e34;">Adequate</span>
   {% endif %}
  </td>
 </tr>
 {% endfor %}
</table>

<h3 style="margin-top:2rem;">Detailed Inventory Breakdown Across Blood Banks</h3>
<table>
 <tr>
  <th>Blood Bank</th>
  <th>Location</th>
  <th>Blood Group</th>
  <th>Component</th>
  <th>Quantity Available</th>
  <th>Last Updated</th>
 </tr>
 {% for row in inventory_rows %}
 <tr>
  <td><strong>{{ row.blood_bank.name }}</strong></td>
  <td>{{ row.blood_bank.location }}</td>
  <td><span class="badge">{{ row.blood_group }}</span></td>
  <td>{{ row.get_component_display }}</td>
  <td>{{ row.quantity }} unit(s)</td>
  <td>{{ row.updated_at|date:"Y-m-d H:i" }}</td>
 </tr>
 {% empty %}
 <tr><td colspan="6">No inventory records matching selected criteria.</td></tr>
 {% endfor %}
</table>

<div style="margin-top:1.5rem;">
 <a class="btn secondary" href="{% url 'home' %}">Return Home</a>
 <a class="btn" style="margin-left:0.5rem;" href="{% url 'us15_update_blood_inventory' %}">Update Stock (US-15)</a>
</div>
</div>"""


# ---- View
@us04_role_required(*ADMIN_ROLES)
def us30_view_overall_inventory(request):
    """Administrator view to monitor consolidated blood inventory across all banks.

    Acceptance criteria:
    - Administrator can view inventory information.
    - Inventory can be viewed across blood banks.
    - Blood-group quantities are displayed.
    - Information is kept consistent with the underlying inventory.
    """
    form = US30FilterForm(request.GET or None)
    qs = BloodInventory.objects.select_related("blood_bank").order_by("blood_bank__name", "blood_group", "component")

    if form.is_valid():
        bank = form.cleaned_data.get("blood_bank")
        bg = form.cleaned_data.get("blood_group")
        comp = form.cleaned_data.get("component")

        if bank:
            qs = qs.filter(blood_bank=bank)
        if bg:
            qs = qs.filter(blood_group=bg)
        if comp:
            qs = qs.filter(component=comp)

    # Compute aggregate stock by blood group
    group_summary = {bg[0]: 0 for bg in BLOOD_GROUPS}
    for row in qs:
        group_summary[row.blood_group] += row.quantity

    total_units = sum(group_summary.values())
    total_banks = BloodBank.objects.filter(is_active=True).count()
    total_rows = qs.count()

    return render_page(
        request,
        TEMPLATE,
        {
            "form": form,
            "inventory_rows": qs,
            "group_summary": group_summary,
            "total_units": total_units,
            "total_banks": total_banks,
            "total_rows": total_rows,
        },
    )


URLS = [
    path("inventory/overall/", us30_view_overall_inventory, name="us30_view_overall_inventory"),
]

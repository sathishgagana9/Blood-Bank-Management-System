"""US-30 View Overall Inventory.

Tasks: view (totals across ALL blood banks: by blood group, by blood bank, group x bank grid; low stock
highlighted) -> GUI tables -> URL. (US-14 is the filterable row-by-row list.)
"""
from django.db.models import Sum
from django.urls import path

from .common import render_page
from .models import BLOOD_GROUPS, BloodBank, BloodInventory
from .us04_user_roles import STAFF_ROLES, us04_role_required
from .us23_low_stock_alert import us23_threshold

# ---- GUI
TEMPLATE = """<div class="card"><h2>US-30 Overall Blood Inventory</h2>
<p><strong>Total units in all blood banks:</strong> {{ grand_total }}</p>
<h3>Blood group &times; blood bank</h3>
<table><tr><th>Blood group</th>{% for b in banks %}<th>{{ b.name }}</th>{% endfor %}<th>Total</th></tr>
{% for group, cells, total, total_low in matrix %}
<tr><td><strong>{{ group }}</strong></td>
{% for qty, low in cells %}<td{% if low %} style="color:#b00020;font-weight:700"{% endif %}>{{ qty }}</td>{% endfor %}
<td{% if total_low %} style="color:#b00020;font-weight:700"{% endif %}><strong>{{ total }}</strong></td></tr>
{% endfor %}
<tr><th>Total</th>{% for t in bank_totals %}<th>{{ t }}</th>{% endfor %}<th>{{ grand_total }}</th></tr></table>
<p class="helptext">Red = at or below the low-stock limit ({{ threshold }} units). All components are added together here;
see US-34 for the component breakdown.</p></div>"""


def _sum(qs):
    return qs.aggregate(t=Sum("quantity"))["t"] or 0


# ---- View
@us04_role_required(*STAFF_ROLES)
def us30_view_overall_inventory(request):
    stock = BloodInventory.objects.all()
    banks = list(BloodBank.objects.filter(is_active=True))
    limit = us23_threshold()
    matrix = []
    for group, _label in BLOOD_GROUPS:
        cells = []
        for bank in banks:
            qty = _sum(stock.filter(blood_group=group, blood_bank=bank))
            cells.append((qty, qty <= limit))
        total = _sum(stock.filter(blood_group=group, blood_bank__in=banks))
        matrix.append((group, cells, total, total <= limit))
    bank_totals = [_sum(stock.filter(blood_bank=b)) for b in banks]
    context = {"banks": banks, "matrix": matrix, "bank_totals": bank_totals, "grand_total": sum(bank_totals), "threshold": limit}
    return render_page(request, TEMPLATE, context)


URLS = [path("inventory/overall/", us30_view_overall_inventory, name="us30_view_overall_inventory")]

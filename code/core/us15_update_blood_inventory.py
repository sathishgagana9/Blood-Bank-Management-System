"""US-15 Update Blood Inventory.

Tasks: update form (bank, group, component, add / remove / set, reason) -> view (change stock, never below
zero, log it) -> GUI page -> URL.
"""
from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect
from django.urls import path

from .common import FORM_FIELDS, render_page
from .models import BLOOD_GROUPS, ActivityLog, BloodBank, BloodInventory, Donation
from .us04_user_roles import STAFF_ROLES, us04_role_required


# ---- Form
class US15UpdateInventoryForm(forms.Form):
    ACTIONS = [
        ("ADD", "Add units (stock received)"),
        ("REMOVE", "Remove units (expired / damaged / transferred)"),
        ("SET", "Set exact quantity (stock-count correction)"),
    ]
    blood_bank = forms.ModelChoiceField(queryset=BloodBank.objects.filter(is_active=True))
    blood_group = forms.ChoiceField(choices=BLOOD_GROUPS)
    component = forms.ChoiceField(choices=Donation.COMPONENT_CHOICES)
    action = forms.ChoiceField(choices=ACTIONS)
    quantity = forms.IntegerField(min_value=0, label="Quantity (units)")
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), help_text="Required for the audit trail (US-33).")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("action") in ("ADD", "REMOVE") and cleaned.get("quantity") == 0:
            self.add_error("quantity", "Enter at least 1 unit.")
        return cleaned


# ---- GUI
TEMPLATE = (
    """<div class="card narrow"><h2>US-15 Update Blood Inventory</h2>
<form method="post" novalidate>{% csrf_token %}"""
    + FORM_FIELDS
    + """<button class="btn" type="submit">Update inventory</button>
<a class="btn secondary" href="{% url 'us14_view_blood_inventory' %}">View inventory</a></form></div>"""
)


# ---- View
@us04_role_required(*STAFF_ROLES)
def us15_update_blood_inventory(request):
    form = US15UpdateInventoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        current = BloodInventory.objects.filter(
            blood_bank=d["blood_bank"], blood_group=d["blood_group"], component=d["component"]
        ).first()
        before = current.quantity if current else 0
        delta = {"ADD": d["quantity"], "REMOVE": -d["quantity"], "SET": d["quantity"] - before}[d["action"]]
        try:
            with transaction.atomic():
                row = BloodInventory.adjust(d["blood_bank"], d["blood_group"], d["component"], delta)
                ActivityLog.record(
                    request.user, "INVENTORY_UPDATED",
                    f"{d['blood_bank']} {d['blood_group']} {d['component']}: {before} -> {row.quantity} ({d['reason']})",
                )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, f"Inventory updated: {before} -> {row.quantity} unit(s).")
            return redirect("us14_view_blood_inventory")
    return render_page(request, TEMPLATE, {"form": form})


URLS = [path("inventory/update/", us15_update_blood_inventory, name="us15_update_blood_inventory")]

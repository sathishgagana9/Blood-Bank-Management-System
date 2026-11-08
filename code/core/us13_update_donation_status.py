"""US-13 Update Donation Status.

Tasks: status form -> view (change status; add/remove inventory when moving to/from Stored; never below
zero) -> GUI page -> URL.
"""
from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import path

from .common import FORM_FIELDS, render_page
from .models import Donation, apply_donation_inventory_effect
from .us04_user_roles import STAFF_ROLES, us04_role_required


# ---- Form
class US13DonationStatusForm(forms.Form):
    status = forms.ChoiceField(choices=Donation.STATUS_CHOICES)


# ---- GUI
TEMPLATE = (
    """<div class="card narrow"><h2>US-13 Update Donation Status</h2>
<p>{{ donation.donation_id }} &middot; {{ donation.donor.name }} ({{ donation.blood_group }}) &middot;
{{ donation.get_component_display }} &middot; {{ donation.quantity }} unit(s) &middot; {{ donation.blood_bank }}</p>
<form method="post" novalidate>{% csrf_token %}"""
    + FORM_FIELDS
    + """<button class="btn" type="submit">Update status</button>
<a class="btn secondary" href="{% url 'us12_view_donation_records' %}">Cancel</a></form></div>"""
)


# ---- View
@us04_role_required(*STAFF_ROLES)
def us13_update_donation_status(request, donation_pk):
    donation = get_object_or_404(Donation.objects.select_related("donor", "blood_bank"), pk=donation_pk)
    form = US13DonationStatusForm(request.POST or None, initial={"status": donation.status})
    if request.method == "POST" and form.is_valid():
        old_status = donation.status
        donation.status = form.cleaned_data["status"]
        try:
            with transaction.atomic():
                donation.save()
                apply_donation_inventory_effect(donation, old_status)
        except ValidationError as exc:
            donation.status = old_status  # change was rolled back
            form.add_error(None, exc)
        else:
            messages.success(request, f"Status of {donation.donation_id} changed to {donation.get_status_display()}.")
            return redirect("us12_view_donation_records")
    return render_page(request, TEMPLATE, {"form": form, "donation": donation})


URLS = [
    path("donations/<int:donation_pk>/status/", us13_update_donation_status, name="us13_update_donation_status")
]

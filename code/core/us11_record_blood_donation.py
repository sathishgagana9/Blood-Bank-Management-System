"""US-11 Record Blood Donation.

Tasks: donation form (donor, group, date, bank, quantity, component, status; validated) -> view (save with
auto ID DON-00001..., update inventory when status is Stored) -> GUI page -> URL.
"""
from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect
from django.urls import path
from django.utils import timezone

from .common import FORM_FIELDS, render_page
from .models import BloodBank, Donation, Donor, apply_donation_inventory_effect
from .us04_user_roles import STAFF_ROLES, us04_role_required


# ---- Form
class US11RecordDonationForm(forms.ModelForm):
    donor = forms.ModelChoiceField(queryset=Donor.objects.all())
    blood_bank = forms.ModelChoiceField(queryset=BloodBank.objects.filter(is_active=True))

    class Meta:
        model = Donation
        fields = ("donor", "blood_group", "donation_date", "blood_bank", "quantity", "component", "status")
        widgets = {"donation_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def clean(self):
        cleaned = super().clean()
        donor, group = cleaned.get("donor"), cleaned.get("blood_group")
        if donor and group and donor.blood_group != group:
            self.add_error("blood_group", f"Blood group must match the donor's registered group ({donor.blood_group}).")
        date = cleaned.get("donation_date")
        if date and date > timezone.localdate():
            self.add_error("donation_date", "Donation date cannot be in the future.")
        return cleaned


# ---- GUI
TEMPLATE = (
    """<div class="card narrow"><h2>US-11 Record Blood Donation</h2>
<form method="post" novalidate>{% csrf_token %}"""
    + FORM_FIELDS
    + """<button class="btn" type="submit">Record donation</button></form>
<p class="helptext">A donation is added to inventory (US-14) once its status is "Stored".
If no blood bank is listed, add one in the Django admin.</p></div>"""
)


# ---- View
@us04_role_required(*STAFF_ROLES)
def us11_record_blood_donation(request):
    initial = {}
    donor = Donor.objects.filter(pk=request.GET.get("donor") or 0).first()
    if donor:
        initial = {"donor": donor, "blood_group": donor.blood_group}
    form = US11RecordDonationForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                donation = form.save(commit=False)
                donation.recorded_by = request.user
                donation.save()
                apply_donation_inventory_effect(donation, old_status=None)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, f"Donation recorded with ID {donation.donation_id}.")
            return redirect("us12_view_donation_records")
    return render_page(request, TEMPLATE, {"form": form})


URLS = [path("donations/record/", us11_record_blood_donation, name="us11_record_blood_donation")]

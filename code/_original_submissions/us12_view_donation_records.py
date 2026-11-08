"""US-12 View Donation Records.

Tasks: filter form -> view (list/filter all donations) -> GUI table -> URL.
"""
from django import forms
from django.urls import path

from .common import render_page
from .models import BLOOD_GROUPS, Donation
from .us04_user_roles import STAFF_ROLES, us04_role_required


# ---- Form
class US12DonationFilterForm(forms.Form):
    donation_id = forms.CharField(required=False, label="Donation ID")
    donor_id = forms.CharField(required=False, label="Donor ID")
    blood_group = forms.ChoiceField(required=False, choices=[("", "Any")] + BLOOD_GROUPS)
    component = forms.ChoiceField(required=False, choices=[("", "Any")] + Donation.COMPONENT_CHOICES)
    status = forms.ChoiceField(required=False, choices=[("", "Any")] + Donation.STATUS_CHOICES)


# ---- GUI
TEMPLATE = """<div class="card"><h2>US-12 Donation Records</h2>
<a class="btn" href="{% url 'us11_record_blood_donation' %}">Record donation</a>
<form method="get" class="filters" style="margin-top:12px">
 <div>{{ form.donation_id.label_tag }}{{ form.donation_id }}</div>
 <div>{{ form.donor_id.label_tag }}{{ form.donor_id }}</div>
 <div>{{ form.blood_group.label_tag }}{{ form.blood_group }}</div>
 <div>{{ form.component.label_tag }}{{ form.component }}</div>
 <div>{{ form.status.label_tag }}{{ form.status }}</div>
 <div><button class="btn" type="submit">Filter</button></div>
</form>
<table><tr><th>Donation ID</th><th>Donor</th><th>Group</th><th>Date</th><th>Blood bank</th><th>Component</th><th>Units</th><th>Status</th><th></th></tr>
{% for d in donations %}
<tr><td>{{ d.donation_id }}</td><td>{{ d.donor.donor_id }} {{ d.donor.name }}</td><td>{{ d.blood_group }}</td>
<td>{{ d.donation_date }}</td><td>{{ d.blood_bank }}</td><td>{{ d.get_component_display }}</td>
<td>{{ d.quantity }}</td><td>{{ d.get_status_display }}</td>
<td><a href="{% url 'us13_update_donation_status' d.pk %}">Update status</a></td></tr>
{% empty %}<tr><td colspan="9">No donation records found.</td></tr>{% endfor %}
</table></div>"""


# ---- View
@us04_role_required(*STAFF_ROLES)
def us12_view_donation_records(request):
    form = US12DonationFilterForm(request.GET or None)
    donations = Donation.objects.select_related("donor", "blood_bank")
    if form.is_valid():
        data = form.cleaned_data
        if data["donation_id"]:
            donations = donations.filter(donation_id__icontains=data["donation_id"])
        if data["donor_id"]:
            donations = donations.filter(donor__donor_id__icontains=data["donor_id"])
        if data["blood_group"]:
            donations = donations.filter(blood_group=data["blood_group"])
        if data["component"]:
            donations = donations.filter(component=data["component"])
        if data["status"]:
            donations = donations.filter(status=data["status"])
    return render_page(request, TEMPLATE, {"form": form, "donations": donations})


URLS = [path("donations/", us12_view_donation_records, name="us12_view_donation_records")]

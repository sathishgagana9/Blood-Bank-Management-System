"""US-32 Search and Filter Records.

Tasks: search form (record type, keyword, group, status, blood bank, date range) -> view (search donors,
donations or blood requests in one place) -> GUI table -> URL.
"""
from django import forms
from django.db.models import Q
from django.urls import path, reverse

from .common import render_page
from .models import BLOOD_GROUPS, BloodBank, BloodRequest, Donation, Donor
from .us04_user_roles import STAFF_ROLES, us04_role_required


# ---- Form
class US32RecordSearchForm(forms.Form):
    RECORD_TYPES = [("DONATIONS", "Donations"), ("REQUESTS", "Blood requests"), ("DONORS", "Donors")]
    record_type = forms.ChoiceField(choices=RECORD_TYPES)
    q = forms.CharField(required=False, label="Keyword", help_text="ID, name, username or phone")
    blood_group = forms.ChoiceField(required=False, choices=[("", "Any")] + BLOOD_GROUPS)
    status = forms.ChoiceField(required=False, choices=[("", "Any")] + Donation.STATUS_CHOICES + BloodRequest.STATUS_CHOICES[1:])
    blood_bank = forms.ModelChoiceField(queryset=BloodBank.objects.all(), required=False, empty_label="All blood banks")
    location = forms.CharField(required=False, help_text="Blood bank location (donors: address)")
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="From date")
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="To date")


# ---- GUI
TEMPLATE = """<div class="card"><h2>US-32 Search and Filter Records</h2>
<form method="get" class="filters">
 <div>{{ form.record_type.label_tag }}{{ form.record_type }}</div>
 <div>{{ form.q.label_tag }}{{ form.q }}</div>
 <div>{{ form.blood_group.label_tag }}{{ form.blood_group }}</div>
 <div>{{ form.status.label_tag }}{{ form.status }}</div>
 <div>{{ form.blood_bank.label_tag }}{{ form.blood_bank }}</div>
 <div>{{ form.location.label_tag }}{{ form.location }}</div>
 <div>{{ form.date_from.label_tag }}{{ form.date_from }}</div>
 <div>{{ form.date_to.label_tag }}{{ form.date_to }}</div>
 <div><button class="btn" type="submit">Search</button></div>
</form>
{% if searched %}<p><strong>{{ rows|length }}</strong> record(s) found.</p>
<table><tr><th>ID</th><th>Name / details</th><th>Blood group</th><th>Status</th><th>Date</th><th></th></tr>
{% for r in rows %}<tr><td>{{ r.id }}</td><td>{{ r.name }}</td><td>{{ r.group }}</td><td>{{ r.status }}</td><td>{{ r.date }}</td><td>{% if r.url %}<a href="{{ r.url }}">Open</a>{% endif %}</td></tr>
{% empty %}<tr><td colspan="6">No records match.</td></tr>{% endfor %}</table>{% endif %}</div>"""


# ---- Search helpers
def _donors(d):
    qs = Donor.objects.all()
    if d["q"]:
        qs = qs.filter(Q(donor_id__icontains=d["q"]) | Q(name__icontains=d["q"]) | Q(contact__icontains=d["q"]))
    if d["blood_group"]:
        qs = qs.filter(blood_group=d["blood_group"])
    if d["location"]:
        qs = qs.filter(address__icontains=d["location"])
    if d["date_from"]:
        qs = qs.filter(created_at__date__gte=d["date_from"])
    if d["date_to"]:
        qs = qs.filter(created_at__date__lte=d["date_to"])
    return [{"id": x.donor_id, "name": x.name, "group": x.blood_group, "status": "-", "date": x.created_at.date(), "url": reverse("us06_view_donor_detail", args=[x.pk])} for x in qs]


def _donations(d):
    qs = Donation.objects.select_related("donor", "blood_bank")
    if d["q"]:
        qs = qs.filter(Q(donation_id__icontains=d["q"]) | Q(donor__name__icontains=d["q"]) | Q(donor__donor_id__icontains=d["q"]))
    if d["blood_group"]:
        qs = qs.filter(blood_group=d["blood_group"])
    if d["status"] in dict(Donation.STATUS_CHOICES):
        qs = qs.filter(status=d["status"])
    elif d["status"]:
        qs = qs.none()
    if d["blood_bank"]:
        qs = qs.filter(blood_bank=d["blood_bank"])
    if d["location"]:
        qs = qs.filter(blood_bank__location__icontains=d["location"])
    if d["date_from"]:
        qs = qs.filter(donation_date__gte=d["date_from"])
    if d["date_to"]:
        qs = qs.filter(donation_date__lte=d["date_to"])
    return [{"id": x.donation_id, "name": f"{x.donor.name} - {x.get_component_display()} x{x.quantity}", "group": x.blood_group, "status": x.get_status_display(), "date": x.donation_date, "url": reverse("us13_update_donation_status", args=[x.pk])} for x in qs]


def _requests(d):
    qs = BloodRequest.objects.select_related("requester", "blood_bank")
    if d["q"]:
        qs = qs.filter(Q(request_id__icontains=d["q"]) | Q(patient_name__icontains=d["q"]) | Q(requester__username__icontains=d["q"]))
    if d["blood_group"]:
        qs = qs.filter(blood_group=d["blood_group"])
    if d["status"] in dict(BloodRequest.STATUS_CHOICES):
        qs = qs.filter(status=d["status"])
    elif d["status"]:
        qs = qs.none()
    if d["blood_bank"]:
        qs = qs.filter(blood_bank=d["blood_bank"])
    if d["location"]:
        qs = qs.filter(blood_bank__location__icontains=d["location"])
    if d["date_from"]:
        qs = qs.filter(created_at__date__gte=d["date_from"])
    if d["date_to"]:
        qs = qs.filter(created_at__date__lte=d["date_to"])
    return [{"id": x.request_id, "name": f"{x.patient_name} - {x.get_component_display()} x{x.quantity} ({x.blood_bank})", "group": x.blood_group, "status": x.get_status_display(), "date": x.created_at.date(), "url": reverse("us19_view_blood_requests")} for x in qs]


SEARCHERS = {"DONORS": _donors, "DONATIONS": _donations, "REQUESTS": _requests}


# ---- View
@us04_role_required(*STAFF_ROLES)
def us32_search_and_filter_records(request):
    form = US32RecordSearchForm(request.GET or None)
    rows, searched = [], False
    if request.GET and form.is_valid():
        searched = True
        rows = SEARCHERS[form.cleaned_data["record_type"]](form.cleaned_data)
    return render_page(request, TEMPLATE, {"form": form, "rows": rows, "searched": searched})


URLS = [path("records/", us32_search_and_filter_records, name="us32_search_and_filter_records")]

"""US-31 Generate Reports.

Tasks: report form (type, date range, blood bank, group) -> view (build Inventory / Donations / Blood Requests
report, show on screen, download as CSV) -> GUI page -> URL.
"""
import csv

from django import forms
from django.http import HttpResponse
from django.urls import path

from .common import render_page
from django.db.models import Count

from .models import BLOOD_GROUPS, BloodBank, BloodInventory, BloodRequest, Donation, Donor
from .us04_user_roles import STAFF_ROLES, us04_role_required


# ---- Form
class US31ReportForm(forms.Form):
    REPORT_TYPES = [
        ("DONORS", "Donors"),
        ("DONATIONS", "Donations"),
        ("INVENTORY", "Inventory (current stock)"),
        ("AVAILABILITY", "Availability (blood in stock)"),
        ("REQUESTS", "Blood requests"),
    ]
    report_type = forms.ChoiceField(choices=REPORT_TYPES)
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="From date")
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="To date")
    blood_bank = forms.ModelChoiceField(queryset=BloodBank.objects.all(), required=False, empty_label="All blood banks")
    blood_group = forms.ChoiceField(required=False, choices=[("", "Any blood group")] + BLOOD_GROUPS)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("date_from") and cleaned.get("date_to") and cleaned["date_from"] > cleaned["date_to"]:
            self.add_error("date_to", "'To date' must be after 'From date'.")
        return cleaned


# ---- GUI
TEMPLATE = """<div class="card"><h2>US-31 Generate Reports</h2>
<form method="get" class="filters">
 <div>{{ form.report_type.label_tag }}{{ form.report_type }}</div>
 <div>{{ form.date_from.label_tag }}{{ form.date_from }}{{ form.date_from.errors }}</div>
 <div>{{ form.date_to.label_tag }}{{ form.date_to }}{{ form.date_to.errors }}</div>
 <div>{{ form.blood_bank.label_tag }}{{ form.blood_bank }}</div>
 <div>{{ form.blood_group.label_tag }}{{ form.blood_group }}</div>
 <div><button class="btn" type="submit">Generate</button></div>
</form>
{% if title %}<h3>{{ title }}</h3>
<p><strong>Records:</strong> {{ rows|length }} &nbsp; {% if total_units is not None %}<strong>Total units:</strong> {{ total_units }}{% endif %}
&nbsp; <a class="btn secondary" style="margin:0" href="?{{ query }}&amp;download=csv">Download CSV</a></p>
<table><tr>{% for h in headers %}<th>{{ h }}</th>{% endfor %}</tr>
{% for row in rows %}<tr>{% for cell in row %}<td>{{ cell }}</td>{% endfor %}</tr>
{% empty %}<tr><td colspan="{{ headers|length }}">No records for these filters.</td></tr>{% endfor %}</table>{% endif %}</div>"""


# ---- Report builders: each returns (title, headers, rows, index of the units column)
def _inventory_report(d):
    qs = BloodInventory.objects.select_related("blood_bank")
    if d["blood_bank"]:
        qs = qs.filter(blood_bank=d["blood_bank"])
    if d["blood_group"]:
        qs = qs.filter(blood_group=d["blood_group"])
    rows = [(r.blood_bank.name, r.blood_group, r.get_component_display(), r.quantity, r.updated_at.strftime("%Y-%m-%d %H:%M")) for r in qs]
    return "Inventory report", ["Blood bank", "Blood group", "Component", "Units", "Last updated"], rows, 3


def _donations_report(d):
    qs = Donation.objects.select_related("donor", "blood_bank")
    if d["blood_bank"]:
        qs = qs.filter(blood_bank=d["blood_bank"])
    if d["blood_group"]:
        qs = qs.filter(blood_group=d["blood_group"])
    if d["date_from"]:
        qs = qs.filter(donation_date__gte=d["date_from"])
    if d["date_to"]:
        qs = qs.filter(donation_date__lte=d["date_to"])
    rows = [(x.donation_id, x.donor.name, x.blood_group, x.get_component_display(), x.quantity, x.get_status_display(), x.blood_bank.name, x.donation_date) for x in qs]
    return "Donations report", ["Donation ID", "Donor", "Group", "Component", "Units", "Status", "Blood bank", "Date"], rows, 4


def _requests_report(d):
    qs = BloodRequest.objects.select_related("requester", "blood_bank")
    if d["blood_bank"]:
        qs = qs.filter(blood_bank=d["blood_bank"])
    if d["blood_group"]:
        qs = qs.filter(blood_group=d["blood_group"])
    if d["date_from"]:
        qs = qs.filter(created_at__date__gte=d["date_from"])
    if d["date_to"]:
        qs = qs.filter(created_at__date__lte=d["date_to"])
    rows = [(x.request_id, x.requester.username if x.requester else "-", x.patient_name, x.blood_group, x.get_component_display(), x.quantity, x.get_status_display(), x.blood_bank.name, x.created_at.strftime("%Y-%m-%d")) for x in qs]
    return "Blood requests report", ["Request ID", "Requested by", "Patient", "Group", "Component", "Units", "Status", "Blood bank", "Created"], rows, 5


def _availability_report(d):
    qs = BloodInventory.objects.select_related("blood_bank").filter(quantity__gt=0, blood_bank__is_active=True)
    if d["blood_bank"]:
        qs = qs.filter(blood_bank=d["blood_bank"])
    if d["blood_group"]:
        qs = qs.filter(blood_group=d["blood_group"])
    rows = [(r.blood_group, r.get_component_display(), r.blood_bank.name, r.blood_bank.location, r.quantity) for r in qs.order_by("blood_group", "-quantity")]
    return "Availability report", ["Blood group", "Component", "Blood bank", "Location", "Units available"], rows, 4


def _donors_report(d):
    qs = Donor.objects.annotate(n=Count("donations"))
    if d["blood_group"]:
        qs = qs.filter(blood_group=d["blood_group"])
    if d["date_from"]:
        qs = qs.filter(created_at__date__gte=d["date_from"])
    if d["date_to"]:
        qs = qs.filter(created_at__date__lte=d["date_to"])
    rows = [(x.donor_id, x.name, x.blood_group, x.contact, x.address, x.n, x.created_at.strftime("%Y-%m-%d")) for x in qs]
    return "Donors report", ["Donor ID", "Name", "Group", "Contact", "Address", "Donations", "Registered"], rows, None


BUILDERS = {"INVENTORY": _inventory_report, "DONATIONS": _donations_report, "REQUESTS": _requests_report,
            "AVAILABILITY": _availability_report, "DONORS": _donors_report}


# ---- View
@us04_role_required(*STAFF_ROLES)
def us31_generate_reports(request):
    params = request.GET.copy()
    download = params.pop("download", [""])[0]
    form = US31ReportForm(params or None)
    context = {"form": form}
    if params and form.is_valid():
        title, headers, rows, units_col = BUILDERS[form.cleaned_data["report_type"]](form.cleaned_data)
        if download == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="{form.cleaned_data["report_type"].lower()}_report.csv"'
            writer = csv.writer(response)
            writer.writerow(headers)
            writer.writerows(rows)
            return response
        context.update(title=title, headers=headers, rows=rows, total_units=None if units_col is None else sum(r[units_col] for r in rows), query=params.urlencode())
    return render_page(request, TEMPLATE, context)


URLS = [path("reports/", us31_generate_reports, name="us31_generate_reports")]

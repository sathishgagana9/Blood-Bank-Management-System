"""US-12 View Donation Records.

Tasks: search donation records -> view donation details & history -> GUI pages -> URLs.
"""
from django import forms
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import path

from .common import render_page
from .models import BLOOD_GROUPS, Donation
from .us04_user_roles import STAFF_ROLES, us04_role_required


# ---- Form
class US12SearchDonationForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search by Donation ID, Donor Name, or Donor ID",
    )
    blood_group = forms.ChoiceField(
        required=False,
        choices=[("", "Any blood group")] + BLOOD_GROUPS,
        label="Blood Group",
    )


# ---- GUI
TEMPLATE_LIST = """<div class="card"><h2>US-12 View Donation Records</h2>
<p>Search and verify blood donation information and donor donation history.</p>
<form method="get" class="filters">
 <div>{{ form.q.label_tag }}{{ form.q }}</div>
 <div>{{ form.blood_group.label_tag }}{{ form.blood_group }}</div>
 <div><button class="btn" type="submit">Search</button></div>
</form>
<table>
 <tr>
  <th>Donation ID</th>
  <th>Donor Name</th>
  <th>Donor ID</th>
  <th>Blood Group</th>
  <th>Date</th>
  <th>Quantity</th>
  <th>Blood Bank</th>
  <th>Status</th>
  <th>Action</th>
 </tr>
 {% for don in donations %}
 <tr>
  <td>{{ don.donation_id }}</td>
  <td>{{ don.donor.name }}</td>
  <td>{{ don.donor.donor_id }}</td>
  <td><span class="badge">{{ don.blood_group }}</span></td>
  <td>{{ don.date }}</td>
  <td>{{ don.quantity }} ml</td>
  <td>{{ don.blood_bank }}</td>
  <td>{{ don.status }}</td>
  <td><a class="btn" href="{% url 'us12_view_donation_detail' don.pk %}">View</a></td>
 </tr>
 {% empty %}
 <tr><td colspan="9">No donation records found.</td></tr>
 {% endfor %}
</table></div>"""

TEMPLATE_DETAIL = """<div class="card">
<h2>US-12 Donation Record: {{ donation.donation_id }}</h2>
<div class="donor-details">
 <h3>Donation Details</h3>
 <p><strong>Donation ID:</strong> {{ donation.donation_id }}</p>
 <p><strong>Blood Group:</strong> <span class="badge">{{ donation.blood_group }}</span></p>
 <p><strong>Quantity:</strong> {{ donation.quantity }} ml</p>
 <p><strong>Donation Date:</strong> {{ donation.date }}</p>
 <p><strong>Blood Bank / Center:</strong> {{ donation.blood_bank }}</p>
 <p><strong>Status:</strong> {{ donation.status }}</p>

 <h3>Associated Donor Details</h3>
 <p><strong>Donor ID:</strong> {{ donation.donor.donor_id }}</p>
 <p><strong>Donor Name:</strong> {{ donation.donor.name }}</p>
 <p><strong>Contact:</strong> {{ donation.donor.contact }}</p>
 <p><strong>Email:</strong> {{ donation.donor.email|default:"N/A" }}</p>
</div>
<p style="margin-top: 1.5rem;"><a class="btn" href="{% url 'us12_view_donation_records' %}">Back to Donation Records</a></p>
</div>"""


# ---- Views
@us04_role_required(*STAFF_ROLES)
def us12_view_donation_records(request):
    form = US12SearchDonationForm(request.GET or None)
    donations = Donation.objects.select_related("donor").all().order_by("-date")
    if form.is_valid():
        q = form.cleaned_data.get("q", "").strip()
        bg = form.cleaned_data.get("blood_group", "").strip()
        if q:
            donations = donations.filter(
                Q(donation_id__icontains=q)
                | Q(donor__name__icontains=q)
                | Q(donor__donor_id__icontains=q)
            )
        if bg:
            donations = donations.filter(blood_group=bg)
    return render_page(
        request,
        TEMPLATE_LIST,
        {"form": form, "donations": donations},
    )


@us04_role_required(*STAFF_ROLES)
def us12_view_donation_detail(request, pk):
    donation = get_object_or_404(Donation.objects.select_related("donor"), pk=pk)
    return render_page(
        request,
        TEMPLATE_DETAIL,
        {"donation": donation},
    )


URLS = [
    path("donations/", us12_view_donation_records, name="us12_view_donation_records"),
    path(
        "donations/<int:pk>/",
        us12_view_donation_detail,
        name="us12_view_donation_detail",
    ),
]

"""US-06 View Donor.

Tasks: donor search & list -> donor detail view (with donation history) -> GUI pages -> URLs.
"""
from django import forms
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import path

from .common import render_page
from .models import Donor
from .us04_user_roles import STAFF_ROLES, us04_role_required


# ---- Form
class US06SearchDonorForm(forms.Form):
    q = forms.CharField(required=False, label="Search by donor ID, name, or blood group")


# ---- GUI
TEMPLATE_LIST = """<div class="card"><h2>US-06 View Donors</h2>
<form method="get" class="filters">
 <div>{{ form.q.label_tag }}{{ form.q }}</div>
 <div><button class="btn" type="submit">Search</button></div>
</form>
<table>
 <tr><th>Donor ID</th><th>Name</th><th>Blood Group</th><th>Contact</th><th>Action</th></tr>
 {% for d in donors %}
 <tr>
  <td>{{ d.donor_id }}</td>
  <td>{{ d.name }}</td>
  <td><span class="badge">{{ d.blood_group }}</span></td>
  <td>{{ d.contact }}</td>
  <td><a class="btn" href="{% url 'us06_view_donor_detail' d.pk %}">View Details</a></td>
 </tr>
 {% empty %}
 <tr><td colspan="5">No donors found.</td></tr>
 {% endfor %}
</table></div>"""

TEMPLATE_DETAIL = """<div class="card">
<h2>US-06 Donor Details: {{ donor.name }}</h2>
<div class="donor-details">
 <p><strong>Donor ID:</strong> {{ donor.donor_id }}</p>
 <p><strong>Full Name:</strong> {{ donor.name }}</p>
 <p><strong>Blood Group:</strong> <span class="badge">{{ donor.blood_group }}</span></p>
 <p><strong>Contact:</strong> {{ donor.contact }}</p>
 <p><strong>Email:</strong> {{ donor.email|default:"N/A" }}</p>
 <p><strong>Address:</strong> {{ donor.address|default:"N/A" }}</p>
 {% if donor.date_of_birth %}<p><strong>Date of Birth:</strong> {{ donor.date_of_birth }}</p>{% endif %}
 {% if donor.gender %}<p><strong>Gender:</strong> {{ donor.gender }}</p>{% endif %}
</div>

<h3>Donation History</h3>
<table>
 <tr><th>Donation ID</th><th>Date</th><th>Blood Bank</th><th>Quantity</th><th>Status</th></tr>
 {% for don in donations %}
 <tr>
  <td>{{ don.donation_id }}</td>
  <td>{{ don.date }}</td>
  <td>{{ don.blood_bank }}</td>
  <td>{{ don.quantity }} ml</td>
  <td>{{ don.status }}</td>
 </tr>
 {% empty %}
 <tr><td colspan="5">No past donations recorded.</td></tr>
 {% endfor %}
</table>
<p><a class="btn" href="{% url 'us06_view_donor' %}">Back to Donors List</a></p>
</div>"""


# ---- Views
@us04_role_required(*STAFF_ROLES)
def us06_view_donor(request):
    form = US06SearchDonorForm(request.GET or None)
    donors = Donor.objects.all().order_by("donor_id")
    if form.is_valid() and form.cleaned_data["q"]:
        q = form.cleaned_data["q"].strip()
        donors = donors.filter(
            Q(donor_id__icontains=q)
            | Q(name__icontains=q)
            | Q(blood_group__iexact=q)
        )
    return render_page(request, TEMPLATE_LIST, {"form": form, "donors": donors})


@us04_role_required(*STAFF_ROLES)
def us06_view_donor_detail(request, pk):
    donor = get_object_or_404(Donor, pk=pk)
    donations = getattr(donor, "donations", None)
    if donations is not None:
        donations = donations.all().order_by("-date")
    else:
        donations = []
    return render_page(
        request,
        TEMPLATE_DETAIL,
        {"donor": donor, "donations": donations},
    )


URLS = [
    path("donors/", us06_view_donor, name="us06_view_donor"),
    path("donors/<int:pk>/", us06_view_donor_detail, name="us06_view_donor_detail"),
]

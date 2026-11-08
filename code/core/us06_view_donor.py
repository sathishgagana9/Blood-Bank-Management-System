"""US-06 View Donor.

Tasks: donor list view -> donor detail view -> GUI pages -> URLs.
"""
from django.shortcuts import get_object_or_404
from django.urls import path

from .common import render_page
from .models import Donor
from .us04_user_roles import STAFF_ROLES, us04_role_required

# ---- GUI
LIST_TEMPLATE = """<div class="card"><h2>US-06 View Donors</h2>
<a class="btn" href="{% url 'us05_register_donor' %}">Register donor</a>
<a class="btn secondary" href="{% url 'us08_search_donor' %}">Search donors</a>
<table><tr><th>Donor ID</th><th>Name</th><th>Blood group</th><th>Contact</th><th></th></tr>
{% for d in donors %}
<tr><td>{{ d.donor_id }}</td><td>{{ d.name }}</td><td>{{ d.blood_group }}</td><td>{{ d.contact }}</td>
<td><a href="{% url 'us06_view_donor_detail' d.pk %}">View</a></td></tr>
{% empty %}<tr><td colspan="5">No donors registered yet.</td></tr>{% endfor %}
</table></div>"""

DETAIL_TEMPLATE = """<div class="card"><h2>US-06 Donor {{ donor.donor_id }}</h2>
<table>
<tr><th>Name</th><td>{{ donor.name }}</td></tr>
<tr><th>Blood group</th><td>{{ donor.blood_group }}</td></tr>
<tr><th>Contact</th><td>{{ donor.contact }}</td></tr>
<tr><th>Address</th><td>{{ donor.address|linebreaksbr }}</td></tr>
<tr><th>Linked account</th><td>{{ donor.user.username|default:"None" }}</td></tr>
<tr><th>Total donations</th><td>{{ donation_count }}</td></tr>
</table>
<a class="btn" href="{% url 'us07_update_donor' donor.pk %}">Update donor</a>
<a class="btn secondary" href="{% url 'us09_view_donation_history' donor.pk %}">Donation history</a>
<a class="btn secondary" href="{% url 'us11_record_blood_donation' %}?donor={{ donor.pk }}">Record donation</a>
<a class="btn secondary" href="{% url 'us06_view_donor' %}">Back to list</a></div>"""


# ---- Views
@us04_role_required(*STAFF_ROLES)
def us06_view_donor(request):
    return render_page(request, LIST_TEMPLATE, {"donors": Donor.objects.all()})


@us04_role_required(*STAFF_ROLES)
def us06_view_donor_detail(request, donor_pk):
    donor = get_object_or_404(Donor.objects.select_related("user"), pk=donor_pk)
    return render_page(
        request, DETAIL_TEMPLATE, {"donor": donor, "donation_count": donor.donations.count()}
    )


URLS = [
    path("donors/", us06_view_donor, name="us06_view_donor"),
    path("donors/<int:donor_pk>/", us06_view_donor_detail, name="us06_view_donor_detail"),
]

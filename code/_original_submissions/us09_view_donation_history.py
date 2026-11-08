"""US-09 View Donation History.

Tasks: view (donors see only their own history, staff can see any donor's) -> GUI table -> URLs.
"""
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import path

from .common import render_page
from .models import Donor
from .us04_user_roles import ALL_ROLES, us04_role_required

# ---- GUI
TEMPLATE = """<div class="card"><h2>US-09 Donation History &mdash; {{ donor.name }} ({{ donor.donor_id }}, {{ donor.blood_group }})</h2>
<table><tr><th>Donation ID</th><th>Date</th><th>Blood bank</th><th>Component</th><th>Units</th><th>Status</th></tr>
{% for d in donations %}
<tr><td>{{ d.donation_id }}</td><td>{{ d.donation_date }}</td><td>{{ d.blood_bank }}</td>
<td>{{ d.get_component_display }}</td><td>{{ d.quantity }}</td><td>{{ d.get_status_display }}</td></tr>
{% empty %}<tr><td colspan="6">No donations recorded yet.</td></tr>{% endfor %}
</table></div>"""


# ---- View
@us04_role_required(*ALL_ROLES)
def us09_view_donation_history(request, donor_pk=None):
    if request.user.is_blood_bank_staff:
        if donor_pk is None:
            messages.info(request, "Select a donor to view their donation history.")
            return redirect("us06_view_donor")
        donor = get_object_or_404(Donor, pk=donor_pk)
    else:
        donor = Donor.objects.filter(user=request.user).first()
        if donor is None:
            messages.info(request, "No donor record is linked to your account yet. Please ask blood bank staff.")
            return redirect("home")
        if donor_pk is not None and donor.pk != donor_pk:
            raise PermissionDenied("You can only view your own donation history.")
    return render_page(
        request, TEMPLATE, {"donor": donor, "donations": donor.donations.select_related("blood_bank")}
    )


URLS = [
    path("my-donations/", us09_view_donation_history, name="us09_view_my_donation_history"),
    path("donors/<int:donor_pk>/donations/", us09_view_donation_history, name="us09_view_donation_history"),
]

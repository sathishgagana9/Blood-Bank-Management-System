"""US-07 Update Donor.

Tasks: reuse the donor form from US-05 -> view (save changes) -> GUI page -> URL.
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import path

from .common import FORM_FIELDS, render_page
from .models import Donor
from .us04_user_roles import STAFF_ROLES, us04_role_required
from .us05_register_donor import US05DonorForm

# ---- GUI
TEMPLATE = (
    """<div class="card narrow"><h2>US-07 Update Donor {{ donor.donor_id }}</h2>
<form method="post" novalidate>{% csrf_token %}"""
    + FORM_FIELDS
    + """<button class="btn" type="submit">Save changes</button>
<a class="btn secondary" href="{% url 'us06_view_donor_detail' donor.pk %}">Cancel</a></form></div>"""
)


# ---- View
@us04_role_required(*STAFF_ROLES)
def us07_update_donor(request, donor_pk):
    donor = get_object_or_404(Donor, pk=donor_pk)
    form = US05DonorForm(request.POST or None, instance=donor)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Donor {donor.donor_id} updated.")
        return redirect("us06_view_donor_detail", donor_pk=donor.pk)
    return render_page(request, TEMPLATE, {"form": form, "donor": donor})


URLS = [path("donors/<int:donor_pk>/update/", us07_update_donor, name="us07_update_donor")]

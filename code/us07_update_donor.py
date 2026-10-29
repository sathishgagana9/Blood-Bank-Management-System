"""US-07 Update Donor.

Tasks: donor selection/search -> donor update form (validation) -> view (save updates) -> GUI page -> URLs.
"""
import re

from django import forms
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import path

from .common import FORM_FIELDS, render_page
from .models import BLOOD_GROUPS, Donor
from .us04_user_roles import STAFF_ROLES, us04_role_required


# ---- Form
class US07UpdateDonorForm(forms.ModelForm):
    """Form for updating donor information with strict server-side validation."""

    class Meta:
        model = Donor
        fields = (
            "name",
            "blood_group",
            "contact",
            "email",
            "address",
            "date_of_birth",
            "gender",
        )
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ("name", "blood_group", "contact"):
            self.fields[field].required = True

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Donor name cannot be empty.")
        if len(name) < 2:
            raise forms.ValidationError("Donor name must be at least 2 characters long.")
        return name

    def clean_contact(self):
        contact = self.cleaned_data.get("contact", "").strip()
        # Remove common phone formatting characters like +, -, spaces, ()
        digits_only = re.sub(r"[\s\-\+\(\)]", "", contact)
        if not digits_only.isdigit() or len(digits_only) < 7 or len(digits_only) > 15:
            raise forms.ValidationError(
                "Invalid contact number. Must contain between 7 and 15 digits."
            )
        return contact

    def clean_blood_group(self):
        bg = self.cleaned_data.get("blood_group", "").strip().upper()
        valid_bgs = [choice[0] for choice in BLOOD_GROUPS]
        if bg not in valid_bgs:
            raise forms.ValidationError(f"Invalid blood group '{bg}'. Must be one of: {', '.join(valid_bgs)}.")
        return bg


# ---- GUI
TEMPLATE_SELECT = """<div class="card">
<h2>US-07 Update Donor Records</h2>
<p>Select a donor to update contact and personal details.</p>
<form method="get" class="filters">
 <div>
  <label for="id_q">Search Donor ID or Name:</label>
  <input type="text" id="id_q" name="q" value="{{ q }}" placeholder="e.g. D001 or John">
 </div>
 <div><button class="btn" type="submit">Search</button></div>
</form>

<table>
 <tr>
  <th>Donor ID</th>
  <th>Name</th>
  <th>Blood Group</th>
  <th>Contact</th>
  <th>Email</th>
  <th>Action</th>
 </tr>
 {% for d in donors %}
 <tr>
  <td><strong>{{ d.donor_id }}</strong></td>
  <td>{{ d.name }}</td>
  <td><span class="badge">{{ d.blood_group }}</span></td>
  <td>{{ d.contact }}</td>
  <td>{{ d.email|default:"N/A" }}</td>
  <td><a class="btn" href="{% url 'us07_update_donor' d.pk %}">Edit Donor</a></td>
 </tr>
 {% empty %}
 <tr><td colspan="6">No donors found.</td></tr>
 {% endfor %}
</table>
</div>"""

TEMPLATE_FORM = (
    """<div class="card narrow">
<h2>US-07 Update Donor: {{ donor.donor_id }}</h2>
<p>Update information for <strong>{{ donor.name }}</strong> (ID: {{ donor.donor_id }}).</p>
<form method="post" novalidate>{% csrf_token %}"""
    + FORM_FIELDS
    + """<button class="btn" type="submit">Save Changes</button>
<a class="btn" style="background:#64748b;margin-left:0.5rem;" href="{% url 'us07_select_donor_to_update' %}">Cancel</a>
</form></div>"""
)


# ---- Views
@us04_role_required(*STAFF_ROLES)
def us07_select_donor_to_update(request):
    """Staff view to browse and search donors to select for update."""
    q = request.GET.get("q", "").strip()
    donors = Donor.objects.all().order_by("donor_id")
    if q:
        donors = donors.filter(
            Q(donor_id__icontains=q)
            | Q(name__icontains=q)
            | Q(contact__icontains=q)
        )
    return render_page(
        request,
        TEMPLATE_SELECT,
        {"donors": donors, "q": q},
    )


@us04_role_required(*STAFF_ROLES)
def us07_update_donor(request, pk):
    """Staff view to edit and save updated donor information."""
    donor = get_object_or_404(Donor, pk=pk)
    form = US07UpdateDonorForm(request.POST or None, instance=donor)

    if request.method == "POST":
        if form.is_valid():
            updated_donor = form.save()
            messages.success(
                request,
                f"Donor '{updated_donor.donor_id}' ({updated_donor.name}) updated successfully.",
            )
            return redirect("us07_select_donor_to_update")
        else:
            messages.error(request, "Failed to update donor. Please correct the errors below.")

    return render_page(
        request,
        TEMPLATE_FORM,
        {"donor": donor, "form": form},
    )


URLS = [
    path("donors/update/", us07_select_donor_to_update, name="us07_select_donor_to_update"),
    path("donors/<int:pk>/update/", us07_update_donor, name="us07_update_donor"),
]

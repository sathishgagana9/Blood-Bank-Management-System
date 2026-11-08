"""US-08 Search Donor.

Tasks: search form (donor ID / name, blood group, contact) -> view (filter donors) -> GUI page -> URL.
"""
from django import forms
from django.db.models import Q
from django.urls import path

from .common import render_page
from .models import BLOOD_GROUPS, Donor
from .us04_user_roles import STAFF_ROLES, us04_role_required


# ---- Form
class US08SearchDonorForm(forms.Form):
    q = forms.CharField(required=False, label="Donor ID or name")
    blood_group = forms.ChoiceField(required=False, choices=[("", "Any blood group")] + BLOOD_GROUPS)
    contact = forms.CharField(required=False, label="Contact number")


# ---- GUI
TEMPLATE = """<div class="card"><h2>US-08 Search Donor</h2>
<form method="get" class="filters">
 <div>{{ form.q.label_tag }}{{ form.q }}</div>
 <div>{{ form.blood_group.label_tag }}{{ form.blood_group }}</div>
 <div>{{ form.contact.label_tag }}{{ form.contact }}</div>
 <div><button class="btn" type="submit">Search</button></div>
</form>
{% if searched %}
<table><tr><th>Donor ID</th><th>Name</th><th>Blood group</th><th>Contact</th><th></th></tr>
{% for d in donors %}
<tr><td>{{ d.donor_id }}</td><td>{{ d.name }}</td><td>{{ d.blood_group }}</td><td>{{ d.contact }}</td>
<td><a href="{% url 'us06_view_donor_detail' d.pk %}">View</a></td></tr>
{% empty %}<tr><td colspan="5">No donors match your search.</td></tr>{% endfor %}
</table>{% endif %}</div>"""


# ---- View
@us04_role_required(*STAFF_ROLES)
def us08_search_donor(request):
    form = US08SearchDonorForm(request.GET or None)
    donors, searched = Donor.objects.none(), False
    if form.is_valid() and any(form.cleaned_data.values()):
        searched = True
        data = form.cleaned_data
        donors = Donor.objects.all()
        if data["q"]:
            donors = donors.filter(Q(donor_id__icontains=data["q"]) | Q(name__icontains=data["q"]))
        if data["blood_group"]:
            donors = donors.filter(blood_group=data["blood_group"])
        if data["contact"]:
            donors = donors.filter(contact__icontains=data["contact"])
    return render_page(request, TEMPLATE, {"form": form, "donors": donors, "searched": searched})


URLS = [path("donors/search/", us08_search_donor, name="us08_search_donor")]

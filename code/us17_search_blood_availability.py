"""US-17 Search Blood Availability.

Tasks: search form (group, component, blood bank / location) -> view (list banks that have stock) -> GUI table
with "Request" and "Notify me" shortcuts -> URL.
"""
from django import forms
from django.db.models import Q
from django.urls import path

from .common import render_page
from .models import BLOOD_GROUPS, BloodInventory, Donation
from .us04_user_roles import ALL_ROLES, us04_role_required


# ---- Form
class US17AvailabilityForm(forms.Form):
    blood_group = forms.ChoiceField(required=False, choices=[("", "Any blood group")] + BLOOD_GROUPS)
    component = forms.ChoiceField(required=False, choices=[("", "Any component")] + Donation.COMPONENT_CHOICES)
    location = forms.CharField(required=False, label="Blood bank / location")


# ---- GUI
TEMPLATE = """<div class="card"><h2>US-17 Search Blood Availability</h2>
<form method="get" class="filters">
 <div>{{ form.blood_group.label_tag }}{{ form.blood_group }}</div>
 <div>{{ form.component.label_tag }}{{ form.component }}</div>
 <div>{{ form.location.label_tag }}{{ form.location }}</div>
 <div><button class="btn" type="submit">Search</button></div>
</form>
<table><tr><th>Blood bank</th><th>Location</th><th>Contact</th><th>Group</th><th>Component</th><th>Units available</th><th></th></tr>
{% for r in rows %}
<tr><td>{{ r.blood_bank.name }}</td><td>{{ r.blood_bank.location }}</td><td>{{ r.blood_bank.contact }}</td>
<td>{{ r.blood_group }}</td><td>{{ r.get_component_display }}</td><td>{{ r.quantity }}</td>
<td><a href="{% url 'us18_submit_blood_request' %}?blood_bank={{ r.blood_bank.pk }}&amp;blood_group={{ r.blood_group }}&amp;component={{ r.component }}">Request</a></td></tr>
{% empty %}<tr><td colspan="7">No matching blood is available right now.
<a href="{% url 'us26_availability_notification' %}?blood_group={{ request.GET.blood_group }}&amp;component={{ request.GET.component }}">Notify me when it becomes available</a> (US-26).</td></tr>{% endfor %}
</table></div>"""


# ---- View
@us04_role_required(*ALL_ROLES)
def us17_search_blood_availability(request):
    form = US17AvailabilityForm(request.GET or None)
    rows = BloodInventory.objects.select_related("blood_bank").filter(quantity__gt=0, blood_bank__is_active=True)
    if form.is_valid():
        data = form.cleaned_data
        if data["blood_group"]:
            rows = rows.filter(blood_group=data["blood_group"])
        if data["component"]:
            rows = rows.filter(component=data["component"])
        if data["location"]:
            rows = rows.filter(Q(blood_bank__name__icontains=data["location"]) | Q(blood_bank__location__icontains=data["location"]))
    return render_page(request, TEMPLATE, {"form": form, "rows": rows.order_by("-quantity")})


URLS = [path("availability/", us17_search_blood_availability, name="us17_search_blood_availability")]

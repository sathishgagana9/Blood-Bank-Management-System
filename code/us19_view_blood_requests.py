"""US-19 View Blood Requests.

Tasks: filter form -> view (staff see all requests; other users see only their own) -> GUI table with
Accept / Reject / Fulfill actions for staff (US-20, US-21, US-22) -> URL.
"""
from django import forms
from django.urls import path

from .common import render_page
from .models import BLOOD_GROUPS, BloodBank, BloodRequest
from .us04_user_roles import ALL_ROLES, us04_role_required


# ---- Form
class US19RequestFilterForm(forms.Form):
    request_id = forms.CharField(required=False, label="Request ID")
    status = forms.ChoiceField(required=False, choices=[("", "Any")] + BloodRequest.STATUS_CHOICES)
    blood_group = forms.ChoiceField(required=False, choices=[("", "Any")] + BLOOD_GROUPS)
    blood_bank = forms.ModelChoiceField(queryset=BloodBank.objects.all(), required=False, empty_label="All blood banks")


# ---- GUI
TEMPLATE = """<div class="card"><h2>US-19 {% if user.is_blood_bank_staff %}Blood Requests{% else %}My Blood Requests{% endif %}</h2>
<a class="btn" href="{% url 'us18_submit_blood_request' %}">New request</a>
<form method="get" class="filters" style="margin-top:12px">
 <div>{{ form.request_id.label_tag }}{{ form.request_id }}</div>
 <div>{{ form.status.label_tag }}{{ form.status }}</div>
 <div>{{ form.blood_group.label_tag }}{{ form.blood_group }}</div>
 <div>{{ form.blood_bank.label_tag }}{{ form.blood_bank }}</div>
 <div><button class="btn" type="submit">Filter</button></div>
</form>
<table><tr><th>Request</th>{% if user.is_blood_bank_staff %}<th>Requested by</th>{% endif %}<th>Patient</th><th>Blood bank</th><th>Group</th><th>Component</th><th>Units</th><th>Urgency</th><th>Needed by</th><th>Status</th>{% if user.is_blood_bank_staff %}<th>Actions</th>{% endif %}</tr>
{% for r in requests %}
<tr><td>{{ r.request_id }}</td>{% if user.is_blood_bank_staff %}<td>{{ r.requester.username }}</td>{% endif %}
<td>{{ r.patient_name }}{% if user.is_blood_bank_staff %}<br><small>{{ r.contact }}</small>{% endif %}</td><td>{{ r.blood_bank }}</td><td>{{ r.blood_group }}</td><td>{{ r.get_component_display }}</td>
<td>{{ r.quantity }}</td><td>{{ r.get_urgency_display }}</td><td>{{ r.required_by }}</td>
<td>{{ r.get_status_display }}{% if r.status == 'REJECTED' and r.rejection_reason %}<br><small>Reason: {{ r.rejection_reason }}</small>{% endif %}</td>
{% if user.is_blood_bank_staff %}<td>
 {% if r.status == 'PENDING' %}<form class="inline" method="post" action="{% url 'us20_accept_blood_request' r.pk %}">{% csrf_token %}<button class="btn" style="margin:0" type="submit">Accept</button></form>{% endif %}
 {% if r.status == 'ACCEPTED' %}<form class="inline" method="post" action="{% url 'us22_fulfill_blood_request' r.pk %}">{% csrf_token %}<button class="btn" style="margin:0" type="submit">Fulfill</button></form>{% endif %}
 {% if r.status == 'PENDING' or r.status == 'ACCEPTED' %}<a class="btn secondary" style="margin:0" href="{% url 'us21_reject_blood_request' r.pk %}">Reject</a>{% endif %}
</td>{% endif %}</tr>
{% empty %}<tr><td colspan="11">No blood requests found.</td></tr>{% endfor %}
</table></div>"""


# ---- View
@us04_role_required(*ALL_ROLES)
def us19_view_blood_requests(request):
    form = US19RequestFilterForm(request.GET or None)
    requests_qs = BloodRequest.objects.select_related("requester", "blood_bank")
    if not request.user.is_blood_bank_staff:
        requests_qs = requests_qs.filter(requester=request.user)
    if form.is_valid():
        data = form.cleaned_data
        if data["request_id"]:
            requests_qs = requests_qs.filter(request_id__icontains=data["request_id"])
        if data["status"]:
            requests_qs = requests_qs.filter(status=data["status"])
        if data["blood_group"]:
            requests_qs = requests_qs.filter(blood_group=data["blood_group"])
        if data["blood_bank"]:
            requests_qs = requests_qs.filter(blood_bank=data["blood_bank"])
    return render_page(request, TEMPLATE, {"form": form, "requests": requests_qs})


URLS = [path("requests/", us19_view_blood_requests, name="us19_view_blood_requests")]

"""US-18 Submit Blood Request.

Tasks: blood request form (blood group, quantity, location/blood bank, urgency, contact, patient name,
required by; validated) -> view (generate unique request ID REQ-00001..., status Pending, link requester)
-> GUI page -> URL.
"""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import path
from django.utils import timezone

from .common import FORM_FIELDS, render_page
from .models import ActivityLog, BloodBank, BloodRequest, Notification


# ---- Form
class US18BloodRequestForm(forms.ModelForm):
    blood_bank = forms.ModelChoiceField(
        queryset=BloodBank.objects.filter(is_active=True),
        label="Blood Bank / Location",
        empty_label="Select a blood bank / location",
    )

    class Meta:
        model = BloodRequest
        fields = (
            "patient_name",
            "blood_group",
            "component",
            "quantity",
            "blood_bank",
            "urgency",
            "contact",
            "required_by",
            "notes",
        )
        widgets = {
            "required_by": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ("patient_name", "blood_group", "component", "quantity", "blood_bank", "urgency", "contact", "required_by"):
            self.fields[field].required = True
        self.fields["quantity"].help_text = "Quantity required (in units, must be > 0)."

    def clean_quantity(self):
        qty = self.cleaned_data.get("quantity")
        if qty is None or qty <= 0:
            raise ValidationError("Quantity must be greater than 0.")
        return qty

    def clean_contact(self):
        contact = self.cleaned_data.get("contact", "").strip()
        if not contact:
            raise ValidationError("Contact information is required.")
        return contact

    def clean_required_by(self):
        required_by = self.cleaned_data.get("required_by")
        if required_by and required_by < timezone.localdate():
            raise ValidationError("Required-by date cannot be in the past.")
        return required_by


# ---- GUI
TEMPLATE = (
    """<div class="card narrow"><h2>US-18 Submit Blood Request</h2>
<p>Submit a request for blood units needed for a patient. Please fill all fields accurately.</p>
<form method="post" novalidate>{% csrf_token %}"""
    + FORM_FIELDS
    + """<button class="btn" type="submit">Submit Request</button></form>
<p style="margin-top:1rem;"><a href="{% url 'us18_my_blood_requests' %}">View My Blood Requests</a></p></div>"""
)

TEMPLATE_MY_REQUESTS = """<div class="card"><h2>My Blood Requests</h2>
<p>List of blood requests you have submitted and their current statuses.</p>
<table>
 <tr>
  <th>Request ID</th>
  <th>Patient</th>
  <th>Blood Group</th>
  <th>Component</th>
  <th>Quantity</th>
  <th>Location / Bank</th>
  <th>Urgency</th>
  <th>Status</th>
  <th>Submitted</th>
 </tr>
 {% for req in requests %}
 <tr>
  <td><strong>{{ req.request_id }}</strong></td>
  <td>{{ req.patient_name }}</td>
  <td>{{ req.blood_group }}</td>
  <td>{{ req.get_component_display }}</td>
  <td>{{ req.quantity }} unit(s)</td>
  <td>{{ req.blood_bank.name }}</td>
  <td>{{ req.get_urgency_display }}</td>
  <td>{{ req.get_status_display }}</td>
  <td>{{ req.created_at|date:"Y-m-d H:i" }}</td>
 </tr>
 {% empty %}
 <tr><td colspan="9">No blood requests submitted yet.</td></tr>
 {% endfor %}
</table>
<p style="margin-top:1.5rem;"><a class="btn" href="{% url 'us18_submit_blood_request' %}">Submit New Request</a></p>
</div>"""


# ---- Views
@login_required
def us18_submit_blood_request(request):
    initial = {}
    if getattr(request.user, "phone", None):
        initial["contact"] = request.user.phone
    form = US18BloodRequestForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        blood_request = form.save(commit=False)
        blood_request.requester = request.user
        blood_request.status = BloodRequest.STATUS_PENDING
        blood_request.save()

        # Audit log entry (US-33)
        ActivityLog.record(
            request.user,
            "SUBMIT_REQUEST",
            f"Submitted blood request {blood_request.request_id} for {blood_request.blood_group} ({blood_request.quantity} units).",
        )

        messages.success(
            request,
            f"Blood request submitted successfully with Request ID {blood_request.request_id} (Status: Pending).",
        )
        return redirect("us18_my_blood_requests")

    return render_page(request, TEMPLATE, {"form": form})


@login_required
def us18_my_blood_requests(request):
    requests = BloodRequest.objects.filter(requester=request.user).select_related("blood_bank").order_by("-created_at")
    return render_page(request, TEMPLATE_MY_REQUESTS, {"requests": requests})


URLS = [
    path("requests/submit/", us18_submit_blood_request, name="us18_submit_blood_request"),
    path("requests/my/", us18_my_blood_requests, name="us18_my_blood_requests"),
]

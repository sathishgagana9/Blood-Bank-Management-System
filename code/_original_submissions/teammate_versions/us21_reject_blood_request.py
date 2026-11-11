"""US-21 Reject Blood Request.

Tasks: reject request form (rejection reason) -> view (select pending request, transition status to Rejected,
save, record ActivityLog, send Notification to requester) -> GUI pages -> URLs.
"""
from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import path

from .common import FORM_FIELDS, render_page
from .models import ActivityLog, BloodRequest, Notification
from .us04_user_roles import STAFF_ROLES, us04_role_required


# ---- Form
class US21RejectRequestForm(forms.Form):
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Enter reason for rejection (e.g., Blood stock not available, invalid request details)"}),
        label="Reason for Rejection",
        required=True,
        help_text="Please provide a clear reason so the requester understands why the request cannot be fulfilled.",
    )

    def clean_rejection_reason(self):
        reason = self.cleaned_data.get("rejection_reason", "").strip()
        if not reason:
            raise ValidationError("A reason for rejection must be provided.")
        if len(reason) < 5:
            raise ValidationError("Please provide a more descriptive rejection reason (at least 5 characters).")
        return reason


# ---- GUI
TEMPLATE_LIST = """<div class="card">
<h2>US-21 Reject Blood Request</h2>
<p>Authorized blood-bank staff can review pending blood requests and reject those that cannot be fulfilled.</p>

<form method="get" class="filters">
 <div>
  <label for="id_q">Search Request ID, Patient, or Blood Group:</label>
  <input type="text" id="id_q" name="q" value="{{ q }}" placeholder="e.g. REQ-00001, O+, Jane">
 </div>
 <div><button class="btn" type="submit">Filter</button></div>
</form>

<table>
 <tr>
  <th>Request ID</th>
  <th>Patient</th>
  <th>Blood Group</th>
  <th>Component</th>
  <th>Quantity</th>
  <th>Location / Bank</th>
  <th>Urgency</th>
  <th>Required By</th>
  <th>Status</th>
  <th>Action</th>
 </tr>
 {% for req in pending_requests %}
 <tr>
  <td><strong>{{ req.request_id }}</strong></td>
  <td>{{ req.patient_name }}</td>
  <td><span class="badge">{{ req.blood_group }}</span></td>
  <td>{{ req.get_component_display }}</td>
  <td>{{ req.quantity }} unit(s)</td>
  <td>{{ req.blood_bank.name }}</td>
  <td>{{ req.get_urgency_display }}</td>
  <td>{{ req.required_by }}</td>
  <td>{{ req.get_status_display }}</td>
  <td>
   <a class="btn secondary" style="background:#b91c1c;" href="{% url 'us21_reject_blood_request' req.pk %}">Reject</a>
  </td>
 </tr>
 {% empty %}
 <tr><td colspan="10">No pending blood requests awaiting action.</td></tr>
 {% endfor %}
</table>
</div>"""

TEMPLATE_REJECT = (
    """<div class="card narrow">
<h2>US-21 Reject Request: {{ blood_request.request_id }}</h2>
<div class="summary" style="background:#fef2f2;border-left:4px solid #b91c1c;padding:0.8rem 1rem;border-radius:4px;margin-bottom:1.2rem;">
 <p><strong>Patient:</strong> {{ blood_request.patient_name }}</p>
 <p><strong>Blood Group / Component:</strong> {{ blood_request.blood_group }} &middot; {{ blood_request.get_component_display }}</p>
 <p><strong>Quantity:</strong> {{ blood_request.quantity }} unit(s)</p>
 <p><strong>Location / Bank:</strong> {{ blood_request.blood_bank.name }}</p>
 <p><strong>Urgency:</strong> {{ blood_request.get_urgency_display }}</p>
 <p><strong>Requester:</strong> {{ blood_request.requester.username }} ({{ blood_request.contact }})</p>
</div>

<form method="post" novalidate>{% csrf_token %}"""
    + FORM_FIELDS
    + """<button class="btn" style="background:#b91c1c;" type="submit">Confirm Rejection</button>
<a class="btn secondary" style="background:#64748b;margin-left:0.5rem;" href="{% url 'us21_pending_requests_list' %}">Cancel</a>
</form></div>"""
)


# ---- Views
@us04_role_required(*STAFF_ROLES)
def us21_pending_requests_list(request):
    """Staff view to browse and select pending blood requests to reject."""
    q = request.GET.get("q", "").strip()
    requests = BloodRequest.objects.filter(status=BloodRequest.STATUS_PENDING).select_related("blood_bank", "requester")
    if q:
        requests = requests.filter(
            forms.models.Q(request_id__icontains=q)
            | forms.models.Q(patient_name__icontains=q)
            | forms.models.Q(blood_group__iexact=q)
        )
    return render_page(request, TEMPLATE_LIST, {"pending_requests": requests, "q": q})


@us04_role_required(*STAFF_ROLES)
def us21_reject_blood_request(request, pk):
    """Staff view to reject a pending blood request with a reason and notify the requester."""
    blood_request = get_object_or_404(BloodRequest.objects.select_related("blood_bank", "requester"), pk=pk)

    # Acceptance criteria / test cases: cannot re-reject or modify fulfilled/already resolved requests
    if blood_request.status != BloodRequest.STATUS_PENDING:
        messages.error(request, f"Request {blood_request.request_id} is already {blood_request.get_status_display()} and cannot be rejected.")
        return redirect("us21_pending_requests_list")

    form = US21RejectRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        reason = form.cleaned_data["rejection_reason"]
        blood_request.status = BloodRequest.STATUS_REJECTED
        blood_request.rejection_reason = reason
        blood_request.handled_by = request.user
        blood_request.save()

        # Notify requester (US-21 / US-25)
        if blood_request.requester:
            Notification.objects.create(
                user=blood_request.requester,
                category="REQUEST_STATUS",
                message=f"Your blood request {blood_request.request_id} has been Rejected. Reason: {reason}",
                link="/requests/my/",
            )

        # Audit log entry (US-33)
        ActivityLog.record(
            request.user,
            "REJECT_REQUEST",
            f"Rejected blood request {blood_request.request_id}. Reason: {reason}",
        )

        messages.success(request, f"Blood request {blood_request.request_id} has been rejected and the requester notified.")
        return redirect("us21_pending_requests_list")

    return render_page(request, TEMPLATE_REJECT, {"blood_request": blood_request, "form": form})


URLS = [
    path("requests/pending/", us21_pending_requests_list, name="us21_pending_requests_list"),
    path("requests/<int:pk>/reject/", us21_reject_blood_request, name="us21_reject_blood_request"),
]

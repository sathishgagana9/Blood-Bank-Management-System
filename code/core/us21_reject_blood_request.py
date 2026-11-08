"""US-21 Reject Blood Request.

Tasks: reason form -> view (Pending or Accepted requests only; mark Rejected with reason, notify requester via
US-25, log) -> GUI page -> URL.
"""
from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import path

from .common import FORM_FIELDS, render_page
from .models import ActivityLog, BloodRequest
from .us04_user_roles import STAFF_ROLES, us04_role_required
from .us25_request_status_notification import us25_notify_request_status


# ---- Form
class US21RejectRequestForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), label="Reason for rejection")


# ---- GUI
TEMPLATE = (
    """<div class="card narrow"><h2>US-21 Reject Blood Request</h2>
<p>{{ blood_request.request_id }} &middot; {{ blood_request.patient_name }} &middot; {{ blood_request.blood_group }}
&middot; {{ blood_request.get_component_display }} &middot; {{ blood_request.quantity }} unit(s)</p>
<form method="post" novalidate>{% csrf_token %}"""
    + FORM_FIELDS
    + """<button class="btn" type="submit">Reject request</button>
<a class="btn secondary" href="{% url 'us19_view_blood_requests' %}">Cancel</a></form></div>"""
)


# ---- View
@us04_role_required(*STAFF_ROLES)
def us21_reject_blood_request(request, request_pk):
    blood_request = get_object_or_404(BloodRequest.objects.select_related("blood_bank"), pk=request_pk)
    if blood_request.status not in (BloodRequest.STATUS_PENDING, BloodRequest.STATUS_ACCEPTED):
        messages.error(request, f"{blood_request.request_id} is {blood_request.get_status_display()} and can no longer be rejected.")
        return redirect("us19_view_blood_requests")
    form = US21RejectRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        blood_request.status = BloodRequest.STATUS_REJECTED
        blood_request.rejection_reason = form.cleaned_data["reason"]
        blood_request.handled_by = request.user
        blood_request.save()
        ActivityLog.record(request.user, "REQUEST_REJECTED", f"{blood_request.request_id}: {blood_request.rejection_reason}")
        us25_notify_request_status(blood_request)
        messages.success(request, f"{blood_request.request_id} rejected.")
        return redirect("us19_view_blood_requests")
    return render_page(request, TEMPLATE, {"form": form, "blood_request": blood_request})


URLS = [path("requests/<int:request_pk>/reject/", us21_reject_blood_request, name="us21_reject_blood_request")]

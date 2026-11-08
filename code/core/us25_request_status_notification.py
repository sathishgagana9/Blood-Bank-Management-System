"""US-25 Request Status Notification.

Tasks: logic only (no page of its own): tell the requester when their request is Accepted (US-20), Rejected
with the reason (US-21) or Fulfilled (US-22). The message appears in the US-24 notification inbox.
"""
from django.urls import reverse

from .models import Notification


def us25_notify_request_status(blood_request):
    if not blood_request.requester:
        return
    text = f"Your blood request {blood_request.request_id} ({blood_request.quantity} x {blood_request.blood_group}) was {blood_request.get_status_display().lower()}."
    if blood_request.status == blood_request.STATUS_REJECTED and blood_request.rejection_reason:
        text += f" Reason: {blood_request.rejection_reason}"
    Notification.send([blood_request.requester], "REQUEST_STATUS", text, link=reverse("us19_view_blood_requests"))

"""US-22 Fulfill Blood Request.

Tasks: view (POST only: Accepted requests only; deduct stock automatically via US-16, mark Fulfilled, notify
requester via US-25, log; refuse if stock is no longer enough) -> button on the US-19 table -> URL.
"""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import path

from .models import ActivityLog, BloodRequest
from .us04_user_roles import STAFF_ROLES, us04_role_required
from .us16_automatic_inventory_update import us16_automatic_inventory_update
from .us25_request_status_notification import us25_notify_request_status


@us04_role_required(*STAFF_ROLES)
def us22_fulfill_blood_request(request, request_pk):
    blood_request = get_object_or_404(BloodRequest, pk=request_pk)
    if request.method == "POST":
        if blood_request.status != BloodRequest.STATUS_ACCEPTED:
            messages.error(request, f"{blood_request.request_id} must be Accepted before it can be fulfilled.")
        else:
            try:
                with transaction.atomic():
                    us16_automatic_inventory_update(blood_request, request.user)
                    blood_request.status = BloodRequest.STATUS_FULFILLED
                    blood_request.handled_by = request.user
                    blood_request.save()
                    ActivityLog.record(request.user, "REQUEST_FULFILLED", blood_request.request_id)
            except ValidationError:
                messages.error(request, f"Cannot fulfill {blood_request.request_id}: not enough units left in inventory.")
            else:
                us25_notify_request_status(blood_request)
                messages.success(request, f"{blood_request.request_id} fulfilled; inventory updated automatically.")
    return redirect("us19_view_blood_requests")


URLS = [path("requests/<int:request_pk>/fulfill/", us22_fulfill_blood_request, name="us22_fulfill_blood_request")]

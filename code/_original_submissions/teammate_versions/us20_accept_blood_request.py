"""US-20 Accept Blood Request.

Tasks: view (POST only: only Pending requests; blood bank must currently hold enough units; mark Accepted,
notify requester via US-25, log) -> button on the US-19 table -> URL.
Stock is deducted when the request is fulfilled (US-22 -> US-16), not when it is accepted.
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import path

from .models import ActivityLog, BloodInventory, BloodRequest
from .us04_user_roles import STAFF_ROLES, us04_role_required
from .us25_request_status_notification import us25_notify_request_status


@us04_role_required(*STAFF_ROLES)
def us20_accept_blood_request(request, request_pk):
    blood_request = get_object_or_404(BloodRequest, pk=request_pk)
    if request.method == "POST":
        if blood_request.status != BloodRequest.STATUS_PENDING:
            messages.error(request, f"{blood_request.request_id} is {blood_request.get_status_display()}; only Pending requests can be accepted.")
        else:
            stock = BloodInventory.objects.filter(
                blood_bank=blood_request.blood_bank, blood_group=blood_request.blood_group, component=blood_request.component
            ).first()
            available = stock.quantity if stock else 0
            if available < blood_request.quantity:
                messages.error(request, f"Cannot accept {blood_request.request_id}: only {available} unit(s) in stock, {blood_request.quantity} requested.")
            else:
                blood_request.status = BloodRequest.STATUS_ACCEPTED
                blood_request.handled_by = request.user
                blood_request.save()
                ActivityLog.record(request.user, "REQUEST_ACCEPTED", blood_request.request_id)
                us25_notify_request_status(blood_request)
                messages.success(request, f"{blood_request.request_id} accepted.")
    return redirect("us19_view_blood_requests")


URLS = [path("requests/<int:request_pk>/accept/", us20_accept_blood_request, name="us20_accept_blood_request")]

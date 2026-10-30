"""US-16 Automatic Inventory Update.

Tasks: logic only (no page of its own, like US-03). Fulfilling a blood request (US-22) automatically deducts
the units from inventory. The matching "add" side is Sprint 1: a donation marked Stored adds stock
(US-11 / US-13 via apply_donation_inventory_effect). Low-stock (US-23) and availability (US-26) alerts fire
automatically from BloodInventory.adjust().
"""
from .models import ActivityLog, BloodInventory


def us16_automatic_inventory_update(blood_request, user=None):
    """Deduct the request's units. Raises ValidationError if stock is not enough. Call inside transaction.atomic()."""
    row = BloodInventory.adjust(
        blood_request.blood_bank, blood_request.blood_group, blood_request.component, -blood_request.quantity
    )
    ActivityLog.record(
        user, "INVENTORY_AUTO_UPDATED",
        f"{blood_request.request_id}: -{blood_request.quantity} {blood_request.blood_group} "
        f"{blood_request.component} at {blood_request.blood_bank} (now {row.quantity})",
    )
    return row

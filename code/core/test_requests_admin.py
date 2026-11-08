"""US-15..US-34: inventory updates, blood requests, alerts/notifications, admin pages, reports, search, activity log."""
import unittest
from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (ActivityLog, AvailabilitySubscription, BloodBank, BloodInventory, BloodRequest, Donation,
                     Notification, User)
from .test_support import PASSWORD, BaseCase
from .us25_request_status_notification import us25_notify_request_status


# ====================================================================== models
class ModelBehaviourTests(BaseCase):
    def test_string_representations(self):
        donor = self.make_donor()
        donation = Donation.objects.create(donor=donor, blood_group="O+", blood_bank=self.bank, recorded_by=self.staff)
        row = self.stock(3)
        req = self.make_request()
        self.assertEqual(str(self.bank), "Central Blood Bank")
        self.assertIn(donor.donor_id, str(donor))
        self.assertIn(donation.donation_id, str(donation))
        self.assertIn("Central Blood Bank", str(row))
        self.assertIn(req.request_id, str(req))

    def test_activity_log_handles_anonymous_user_and_truncates(self):
        ActivityLog.record(AnonymousUser(), "X_TEST", "y" * 400)
        log = ActivityLog.objects.get(action="X_TEST")
        self.assertIsNone(log.user)
        self.assertEqual(len(log.details), 300)

    def test_adjust_refuses_negative_and_leaves_no_row(self):  # NFR-04
        with self.assertRaises(ValidationError):
            BloodInventory.adjust(self.bank, "O+", "WHOLE_BLOOD", -1)
        self.assertEqual(BloodInventory.objects.count(), 0)

    def test_creation_of_donation_cannot_fail_normally_but_is_handled(self):
        """Forces the ValidationError branch of US-11 (otherwise unreachable)."""
        self.login(self.staff)
        donor = self.make_donor()
        with mock.patch("core.us11_record_blood_donation.apply_donation_inventory_effect", side_effect=ValidationError("boom")):
            r = self.client.post(reverse("us11_record_blood_donation"), self.donation_payload(donor))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Donation.objects.count(), 0)  # rolled back


# ====================================================================== US-15
class UpdateInventoryTests(BaseCase):
    def setUp(self):
        self.login(self.staff)
        self.url = reverse("us15_update_blood_inventory")

    def update(self, action, qty, /, reason="stock count", **extra):
        data = {"blood_bank": self.bank.pk, "blood_group": "O+", "component": "WHOLE_BLOOD",
                "action": action, "quantity": qty, "reason": reason}
        data.update(extra)
        return self.client.post(self.url, data)

    def test_add_remove_set(self):  # 7-002, 7-003
        self.assertRedirects(self.update("ADD", 10), reverse("us14_view_blood_inventory"))
        self.assertEqual(self.units(), 10)
        self.update("REMOVE", 3)
        self.assertEqual(self.units(), 7)
        self.update("SET", 2)
        self.assertEqual(self.units(), 2)

    def test_change_is_logged_with_reason_and_user(self):  # 7-009
        self.stock(10)
        self.update("SET", 2, reason="damaged bags")
        log = ActivityLog.objects.get(action="INVENTORY_UPDATED")
        self.assertEqual(log.user, self.staff)
        self.assertIn("10 -> 2", log.details)
        self.assertIn("damaged bags", log.details)

    def test_cannot_remove_more_than_available(self):  # 7-004, 8-008
        self.stock(5)
        r = self.update("REMOVE", 6)
        self.assertContains(r, "negative")
        self.assertEqual(self.units(), 5)

    def test_remove_from_empty_row_creates_nothing(self):
        self.assertContains(self.update("REMOVE", 1), "negative")
        self.assertEqual(BloodInventory.objects.count(), 0)

    def test_validation(self):
        for override in ({"reason": ""}, {"blood_group": "XYZ"}, {"action": "STEAL"}, {"quantity": -1}):
            with self.subTest(override=override):
                self.assertEqual(self.update("ADD", 1, **override).status_code, 200)
        self.assertEqual(self.update("ADD", 0).status_code, 200)  # zero is only allowed for SET
        self.assertEqual(self.update("REMOVE", 0).status_code, 200)
        self.assertEqual(BloodInventory.objects.count(), 0)
        self.update("SET", 0)
        self.assertEqual(self.units(), 0)

    def test_inactive_bank_cannot_be_updated(self):  # 6-004 effect
        self.bank.is_active = False
        self.bank.save()
        self.update("ADD", 5)
        self.assertEqual(BloodInventory.objects.count(), 0)


# ====================================================================== US-17
class SearchAvailabilityTests(BaseCase):
    def setUp(self):
        self.stock(6, "O+")
        self.stock(2, "A+", "PLASMA", bank=self.bank2)
        self.url = reverse("us17_search_blood_availability")
        self.login(self.donor_user)

    def test_lists_everything_without_filters(self):
        r = self.client.get(self.url)
        self.assertContains(r, "Central Blood Bank")
        self.assertContains(r, "North Blood Bank")

    def test_filters(self):  # 9-001..9-004, 9-010
        cases = [({"blood_group": "O+"}, "Central Blood Bank", "North Blood Bank"),
                 ({"component": "PLASMA"}, "North Blood Bank", "Central Blood Bank"),
                 ({"location": "mysuru"}, "North Blood Bank", "Central Blood Bank"),
                 ({"location": "Central"}, "Central Blood Bank", "North Blood Bank"),
                 ({"min_quantity": 5}, "Central Blood Bank", "North Blood Bank"),
                 ({"blood_group": "O+", "location": "Bengaluru", "min_quantity": 6}, "Central Blood Bank", "North Blood Bank")]
        for params, present, absent in cases:
            with self.subTest(params=params):
                r = self.client.get(self.url, params)
                self.assertContains(r, present)
                self.assertNotContains(r, absent)

    def test_inactive_banks_and_zero_stock_are_hidden(self):
        self.bank2.is_active = False
        self.bank2.save()
        self.assertNotContains(self.client.get(self.url), "North Blood Bank")
        self.stock(0, "AB+")
        self.assertContains(self.client.get(self.url, {"blood_group": "AB+"}), "No matching blood is available")

    def test_empty_result_offers_notification(self):  # 9-006
        self.assertContains(self.client.get(self.url, {"blood_group": "AB-"}), "Notify me when it becomes available")

    def test_result_shows_contact_details(self):  # 9-008
        self.assertContains(self.client.get(self.url, {"blood_group": "O+"}), "9876500001")

    def test_invalid_min_quantity_does_not_crash(self):
        self.assertEqual(self.client.get(self.url, {"min_quantity": 0}).status_code, 200)

    def test_anonymous_cannot_search(self):  # 9-009 (differs from the old test case: login is required)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)


# ====================================================================== US-18
class SubmitRequestTests(BaseCase):
    def setUp(self):
        self.login(self.donor_user)
        self.url = reverse("us18_submit_blood_request")

    def payload(self, **o):
        data = {"patient_name": "Ravi", "blood_bank": self.bank.pk, "blood_group": "O+", "component": "WHOLE_BLOOD",
                "quantity": 2, "urgency": "URGENT", "contact": "9876543210",
                "required_by": (timezone.localdate() + timedelta(days=2)).isoformat(), "notes": ""}
        data.update(o)
        return data

    def test_valid_request(self):  # 10-001
        self.stock(5)
        r = self.client.post(self.url, self.payload())
        self.assertRedirects(r, reverse("us19_view_blood_requests"))
        req = BloodRequest.objects.get()
        self.assertEqual((req.status, req.requester), ("PENDING", self.donor_user))
        self.assertEqual(req.request_id, f"REQ-{req.pk:05d}")
        self.assertTrue(ActivityLog.objects.filter(action="REQUEST_SUBMITTED", user=self.donor_user).exists())

    def test_request_is_saved_even_when_stock_is_short(self):  # 10-002
        self.client.post(self.url, self.payload(quantity=9))
        self.assertEqual(BloodRequest.objects.get().status, "PENDING")

    def test_staff_and_admin_are_notified_with_urgency(self):  # 10-009, 13-001
        self.client.post(self.url, self.payload(urgency="CRITICAL"))
        recipients = set(Notification.objects.filter(category="NEW_REQUEST").values_list("user__username", flat=True))
        self.assertEqual(recipients, {"staff1", "admin"})
        self.assertIn("CRITICAL", Notification.objects.filter(user=self.staff).first().message)

    def test_invalid_requests_are_rejected(self):  # 10-003..10-006
        yesterday = (timezone.localdate() - timedelta(days=1)).isoformat()
        for override in ({"blood_group": ""}, {"quantity": 0}, {"quantity": -2}, {"contact": ""}, {"contact": "abc"},
                         {"patient_name": ""}, {"required_by": yesterday}, {"required_by": ""}, {"urgency": "WHENEVER"},
                         {"blood_bank": self.bank2.pk + 100}):
            with self.subTest(override=override):
                self.assertEqual(self.client.post(self.url, self.payload(**override)).status_code, 200)
        self.assertEqual(BloodRequest.objects.count(), 0)

    def test_past_date_message(self):
        yesterday = (timezone.localdate() - timedelta(days=1)).isoformat()
        self.assertContains(self.client.post(self.url, self.payload(required_by=yesterday)), "cannot be in the past")

    def test_form_is_prefilled_from_search_result(self):
        r = self.client.get(self.url, {"blood_bank": self.bank.pk, "blood_group": "O+", "component": "PLASMA"})
        self.assertEqual(r.status_code, 200)


# ====================================================================== US-19
class ViewRequestsTests(BaseCase):
    def setUp(self):
        self.mine = self.make_request(self.donor_user, blood_group="O+")
        self.theirs = self.make_request(self.other_user, blood_group="A-", blood_bank=self.bank2, patient_name="Meena")
        BloodRequest.objects.filter(pk=self.theirs.pk).update(status="ACCEPTED")
        self.url = reverse("us19_view_blood_requests")

    def test_donor_sees_only_own_requests(self):  # 10-007
        self.login(self.donor_user)
        r = self.client.get(self.url)
        self.assertContains(r, self.mine.request_id)
        self.assertNotContains(r, self.theirs.request_id)

    def test_staff_sees_all_and_can_filter(self):  # 11-001, 11-006..11-008
        self.login(self.staff)
        self.assertContains(self.client.get(self.url), self.theirs.request_id)
        cases = [({"request_id": self.mine.request_id}, self.mine, self.theirs),
                 ({"status": "ACCEPTED"}, self.theirs, self.mine), ({"status": "PENDING"}, self.mine, self.theirs),
                 ({"blood_group": "A-"}, self.theirs, self.mine), ({"blood_bank": self.bank2.pk}, self.theirs, self.mine)]
        for params, present, absent in cases:
            with self.subTest(params=params):
                r = self.client.get(self.url, params)
                self.assertContains(r, present.request_id)
                self.assertNotContains(r, absent.request_id)

    def test_rejection_reason_is_shown_to_requester(self):
        BloodRequest.objects.filter(pk=self.mine.pk).update(status="REJECTED", rejection_reason="Blood not available")
        self.login(self.donor_user)
        self.assertContains(self.client.get(self.url), "Blood not available")

    def test_empty_message(self):
        BloodRequest.objects.all().delete()
        self.login(self.donor_user)
        self.assertContains(self.client.get(self.url), "No blood requests found")


# ====================================================================== US-20 / 21 / 22 / 16 / 25
class RequestLifecycleTests(BaseCase):
    def setUp(self):
        self.login(self.staff)
        self.stock(5)
        self.req = self.make_request(quantity=3)

    def act(self, name, **data):
        return self.client.post(reverse(name, args=[self.req.pk]), data)

    def status(self):
        self.req.refresh_from_db()
        return self.req.status

    def status_notes(self):
        return Notification.objects.filter(user=self.donor_user, category="REQUEST_STATUS").count()

    def test_accept_does_not_deduct_stock(self):  # 11-002
        self.act("us20_accept_blood_request")
        self.assertEqual(self.status(), "ACCEPTED")
        self.assertEqual(self.req.handled_by, self.staff)
        self.assertEqual(self.units(), 5)
        self.assertEqual(self.status_notes(), 1)
        self.assertTrue(ActivityLog.objects.filter(action="REQUEST_ACCEPTED", user=self.staff).exists())

    def test_accept_only_works_once_and_only_by_post(self):
        self.client.get(reverse("us20_accept_blood_request", args=[self.req.pk]))
        self.assertEqual(self.status(), "PENDING")
        self.act("us20_accept_blood_request")
        self.act("us20_accept_blood_request")
        self.assertEqual(self.status_notes(), 1)

    def test_cannot_accept_when_stock_is_short(self):
        short = self.make_request(quantity=9)
        self.client.post(reverse("us20_accept_blood_request", args=[short.pk]))
        short.refresh_from_db()
        self.assertEqual(short.status, "PENDING")

    def test_reject_needs_a_reason_and_notifies_with_it(self):  # 11-003
        self.assertEqual(self.client.get(reverse("us21_reject_blood_request", args=[self.req.pk])).status_code, 200)
        self.act("us21_reject_blood_request", reason="")
        self.assertEqual(self.status(), "PENDING")
        self.act("us21_reject_blood_request", reason="Out of stock")
        self.assertEqual(self.status(), "REJECTED")
        self.assertEqual(self.req.rejection_reason, "Out of stock")
        self.assertIn("Reason: Out of stock", Notification.objects.get(user=self.donor_user, category="REQUEST_STATUS").message)

    def test_accepted_request_can_still_be_rejected(self):
        self.act("us20_accept_blood_request")
        self.act("us21_reject_blood_request", reason="Changed")
        self.assertEqual(self.status(), "REJECTED")

    def test_finished_requests_cannot_be_rejected(self):  # 11-010
        for final in ("FULFILLED", "REJECTED"):
            BloodRequest.objects.filter(pk=self.req.pk).update(status=final)
            r = self.client.get(reverse("us21_reject_blood_request", args=[self.req.pk]))
            self.assertRedirects(r, reverse("us19_view_blood_requests"))
            self.act("us21_reject_blood_request", reason="again")
            self.assertEqual(self.status(), final)

    def test_fulfil_deducts_stock_automatically(self):  # 8-002, 11-004
        self.act("us20_accept_blood_request")
        self.act("us22_fulfill_blood_request")
        self.assertEqual(self.status(), "FULFILLED")
        self.assertEqual(self.units(), 2)
        self.assertEqual(self.status_notes(), 2)
        self.assertTrue(ActivityLog.objects.filter(action="INVENTORY_AUTO_UPDATED").exists())
        self.assertTrue(ActivityLog.objects.filter(action="REQUEST_FULFILLED").exists())
        for user in (self.staff, self.admin):  # 5 - 3 = 2 units is below the low-stock limit
            self.assertEqual(Notification.objects.filter(user=user, category="LOW_STOCK").count(), 1)

    def test_fulfil_requires_acceptance_and_post(self):
        self.act("us22_fulfill_blood_request")
        self.assertEqual((self.status(), self.units()), ("PENDING", 5))
        self.act("us20_accept_blood_request")
        self.client.get(reverse("us22_fulfill_blood_request", args=[self.req.pk]))
        self.assertEqual((self.status(), self.units()), ("ACCEPTED", 5))

    def test_fulfil_fails_cleanly_if_stock_disappeared(self):
        self.act("us20_accept_blood_request")
        BloodInventory.adjust(self.bank, "O+", "WHOLE_BLOOD", -5)
        self.act("us22_fulfill_blood_request")
        self.assertEqual((self.status(), self.units()), ("ACCEPTED", 0))

    def test_fulfilled_request_is_locked_and_never_deducted_twice(self):
        self.act("us20_accept_blood_request")
        self.act("us22_fulfill_blood_request")
        for name in ("us20_accept_blood_request", "us22_fulfill_blood_request"):
            self.act(name)
        self.assertEqual((self.status(), self.units()), ("FULFILLED", 2))

    def test_unknown_request_is_404(self):
        self.assertEqual(self.client.post(reverse("us20_accept_blood_request", args=[9999])).status_code, 404)

    def test_status_notification_skipped_when_requester_is_gone(self):
        BloodRequest.objects.filter(pk=self.req.pk).update(requester=None)
        self.req.refresh_from_db()
        us25_notify_request_status(self.req)
        self.assertEqual(Notification.objects.count(), 0)


# ====================================================================== US-23
class LowStockTests(BaseCase):
    def setUp(self):
        self.stock(10)

    def alerts(self, user):
        return Notification.objects.filter(user=user, category="LOW_STOCK").count()

    def test_no_alert_above_threshold(self):  # 12-002
        self.stock(-4)
        self.assertEqual(self.alerts(self.staff), 0)

    def test_alert_when_stock_falls_below_threshold(self):  # 12-001, 12-004, 12-005
        self.stock(-6)
        self.assertEqual((self.alerts(self.staff), self.alerts(self.admin), self.alerts(self.donor_user)), (1, 1, 0))
        message = Notification.objects.filter(user=self.staff).first().message
        self.assertIn("O+", message)
        self.assertIn("4 unit", message)

    def test_alert_at_exactly_the_threshold(self):  # 12-003
        self.stock(-5)
        self.assertEqual(self.alerts(self.staff), 1)

    def test_no_alert_when_stock_increases(self):
        self.stock(-6)
        self.stock(20)
        self.assertEqual(self.alerts(self.staff), 1)

    def test_alert_repeats_on_each_decrease_while_low(self):
        """Documents the current behaviour (FR-12 says 'falls below'); change if you decide on 'only once'."""
        self.stock(-6)
        self.stock(-1)
        self.assertEqual(self.alerts(self.staff), 2)

    def test_inactive_staff_are_not_alerted(self):
        User.objects.filter(pk=self.staff.pk).update(is_active=False)
        self.stock(-6)
        self.assertEqual((self.alerts(self.staff), self.alerts(self.admin)), (0, 1))

    @override_settings(LOW_STOCK_THRESHOLD=2)
    def test_threshold_is_configurable(self):
        self.stock(-6)
        self.assertEqual(self.alerts(self.staff), 0)
        self.stock(-2)
        self.assertEqual(self.alerts(self.staff), 1)

    def test_page_lists_only_low_items_of_active_banks(self):
        self.stock(3, "A+", bank=self.bank2)
        self.login(self.staff)
        r = self.client.get(reverse("us23_low_stock_alert"))
        self.assertContains(r, "North Blood Bank")
        self.assertNotContains(r, "Central Blood Bank")
        self.bank2.is_active = False
        self.bank2.save()
        self.assertContains(self.client.get(reverse("us23_low_stock_alert")), "No low-stock items")


# ====================================================================== US-24
class NotificationInboxTests(BaseCase):
    def test_each_user_sees_only_own_notifications(self):
        Notification.send([self.donor_user], "AVAILABILITY", "Blood for donor one only")
        self.login(self.donor_user)
        self.assertContains(self.client.get(reverse("us24_view_notifications")), "Blood for donor one only")
        self.login(self.staff)
        self.assertNotContains(self.client.get(reverse("us24_view_notifications")), "Blood for donor one only")

    def test_mark_all_read_needs_post(self):
        Notification.send([self.donor_user], "AVAILABILITY", "msg")
        self.login(self.donor_user)
        self.client.get(reverse("us24_mark_notifications_read"))
        self.assertEqual(self.donor_user.notifications.filter(is_read=False).count(), 1)
        self.client.post(reverse("us24_mark_notifications_read"))
        self.assertEqual(self.donor_user.notifications.filter(is_read=False).count(), 0)

    def test_empty_inbox(self):
        self.login(self.donor_user)
        self.assertContains(self.client.get(reverse("us24_view_notifications")), "No notifications yet")


# ====================================================================== US-26
class AvailabilitySubscriptionTests(BaseCase):
    def setUp(self):
        self.login(self.donor_user)
        self.url = reverse("us26_availability_notification")

    def subscribe(self, **o):
        data = {"blood_group": "O+", "component": "", "blood_bank": ""}
        data.update(o)
        return self.client.post(self.url, data)

    def notified(self):
        return Notification.objects.filter(user=self.donor_user, category="AVAILABILITY").count()

    def test_page_loads_with_prefill(self):
        self.assertEqual(self.client.get(self.url, {"blood_group": "O+", "component": "PLASMA"}).status_code, 200)

    def test_subscribe_then_notified_once_when_stock_arrives(self):
        self.subscribe()
        self.stock(4)
        self.assertEqual(self.notified(), 1)
        self.assertFalse(AvailabilitySubscription.objects.get().is_active)
        self.stock(-4)
        self.stock(4)  # subscription is closed, so no second message
        self.assertEqual(self.notified(), 1)

    def test_subscribing_when_stock_exists_is_allowed(self):
        self.stock(4)
        self.subscribe()
        self.assertEqual(AvailabilitySubscription.objects.count(), 1)
        self.subscribe(component="PLASMA", blood_bank=self.bank.pk)
        self.subscribe(blood_bank=self.bank2.pk)
        self.assertEqual(AvailabilitySubscription.objects.count(), 3)

    def test_component_and_bank_filters_are_respected(self):
        self.subscribe(component="PLASMA", blood_bank=self.bank2.pk)
        self.stock(5)  # wrong component and bank
        self.assertEqual(self.notified(), 0)
        BloodInventory.adjust(self.bank2, "O+", "PLASMA", 3)
        self.assertEqual(self.notified(), 1)

    def test_no_message_when_stock_was_already_positive(self):
        self.stock(2)
        self.subscribe()
        self.stock(3)
        self.assertEqual(self.notified(), 0)

    def test_cancel_own_subscription_only_by_post(self):
        sub = AvailabilitySubscription.objects.create(user=self.donor_user, blood_group="O+")
        self.client.get(reverse("us26_cancel_subscription", args=[sub.pk]))
        self.assertEqual(AvailabilitySubscription.objects.count(), 1)
        self.client.post(reverse("us26_cancel_subscription", args=[sub.pk]))
        self.assertEqual(AvailabilitySubscription.objects.count(), 0)

    def test_cannot_cancel_someone_elses_subscription(self):
        sub = AvailabilitySubscription.objects.create(user=self.other_user, blood_group="O+")
        self.assertEqual(self.client.post(reverse("us26_cancel_subscription", args=[sub.pk])).status_code, 404)
        self.assertEqual(AvailabilitySubscription.objects.count(), 1)


# ====================================================================== US-27
class ManageBloodBanksTests(BaseCase):
    def setUp(self):
        self.login(self.admin)

    def test_add_blood_bank(self):  # 6-001
        r = self.client.post(reverse("us27_add_blood_bank"), {"name": "East Bank", "location": "Hubli", "address": "", "contact": "9876500009", "is_active": "on"})
        self.assertRedirects(r, reverse("us27_manage_blood_banks"))
        self.assertTrue(BloodBank.objects.get(name="East Bank").is_active)
        self.assertTrue(ActivityLog.objects.filter(action="BLOOD_BANK_ADDED", user=self.admin).exists())

    def test_add_validation(self):  # 6-006, 6-002
        base = {"name": "East Bank", "location": "Hubli", "address": "", "contact": "", "is_active": "on"}
        for override in ({"name": ""}, {"location": ""}, {"name": "Central Blood Bank"}, {"contact": "abc"}):
            with self.subTest(override=override):
                self.assertEqual(self.client.post(reverse("us27_add_blood_bank"), {**base, **override}).status_code, 200)
        self.assertEqual(BloodBank.objects.count(), 2)

    def test_edit_blood_bank(self):  # 6-003
        url = reverse("us27_edit_blood_bank", args=[self.bank.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.post(url, {"name": "Central Blood Bank", "location": "Chennai", "address": "", "contact": "9999999999", "is_active": "on"})
        self.bank.refresh_from_db()
        self.assertEqual((self.bank.location, self.bank.contact), ("Chennai", "9999999999"))
        self.assertTrue(ActivityLog.objects.filter(action="BLOOD_BANK_UPDATED").exists())

    def test_deactivate_and_reactivate(self):  # 6-004
        url = reverse("us27_toggle_blood_bank", args=[self.bank.pk])
        self.client.get(url)
        self.bank.refresh_from_db()
        self.assertTrue(self.bank.is_active)
        self.client.post(url)
        self.bank.refresh_from_db()
        self.assertFalse(self.bank.is_active)
        self.client.post(url)
        self.bank.refresh_from_db()
        self.assertTrue(self.bank.is_active)
        self.assertTrue(ActivityLog.objects.filter(action="BLOOD_BANK_DEACTIVATED").exists())
        self.assertTrue(ActivityLog.objects.filter(action="BLOOD_BANK_ACTIVATED").exists())

    def test_list_shows_all_banks(self):  # 6-007
        r = self.client.get(reverse("us27_manage_blood_banks"))
        self.assertContains(r, "Central Blood Bank")
        self.assertContains(r, "North Blood Bank")

    def test_banks_with_history_are_never_deleted(self):  # 6-010
        urls = [str(p.pattern) for p in __import__("core.urls", fromlist=["urlpatterns"]).urlpatterns]
        self.assertFalse(any("delete" in u for u in urls))


# ====================================================================== US-28
class ManageUsersTests(BaseCase):
    def setUp(self):
        self.login(self.admin)

    def new_user(self, **o):
        data = {"username": "newstaff", "first_name": "New", "last_name": "Staff", "email": "new@test.com", "phone": "9000000011",
                "address": "X", "role": "STAFF", "password1": "Strong@12345x", "password2": "Strong@12345x"}
        data.update(o)
        return data

    def test_search(self):
        url = reverse("us28_manage_users")
        r = self.client.get(url, {"q": "donor1"})
        self.assertContains(r, "donor1@test.com")
        self.assertNotContains(r, "staff1@test.com")
        self.assertContains(self.client.get(url, {"q": "nobody-here"}), "No users found")
        self.assertContains(self.client.get(url), "staff1@test.com")

    def test_create_user_with_role(self):
        r = self.client.post(reverse("us28_create_user"), self.new_user())
        self.assertRedirects(r, reverse("us28_manage_users"))
        self.assertEqual(User.objects.get(username="newstaff").role, User.ROLE_STAFF)
        self.assertTrue(ActivityLog.objects.filter(action="USER_CREATED", user=self.admin).exists())

    def test_create_user_validation(self):
        before = User.objects.count()
        for override in ({"password2": "different"}, {"email": "staff1@test.com"}, {"username": "staff1"}, {"role": "KING"}):
            with self.subTest(override=override):
                self.assertEqual(self.client.post(reverse("us28_create_user"), self.new_user(**override)).status_code, 200)
        self.assertEqual(User.objects.count(), before)

    def test_edit_user(self):
        url = reverse("us28_edit_user", args=[self.staff.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        data = {"first_name": "Stan", "last_name": "Lee", "email": "staff1@test.com", "phone": "9000000022", "address": "X", "is_active": "on"}
        self.assertRedirects(self.client.post(url, data), reverse("us28_manage_users"))
        self.staff.refresh_from_db()
        self.assertEqual((self.staff.first_name, self.staff.phone), ("Stan", "9000000022"))
        self.assertTrue(ActivityLog.objects.filter(action="USER_UPDATED").exists())

    def test_admin_cannot_deactivate_self(self):
        url = reverse("us28_edit_user", args=[self.admin.pk])
        r = self.client.post(url, {"first_name": "", "last_name": "", "email": "admin@test.com", "phone": "", "address": ""})
        self.assertContains(r, "cannot deactivate your own account")
        self.client.post(reverse("us28_toggle_user", args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_deactivated_user_cannot_log_in_until_reactivated(self):
        toggle = reverse("us28_toggle_user", args=[self.donor_user.pk])
        self.client.get(toggle)
        self.donor_user.refresh_from_db()
        self.assertTrue(self.donor_user.is_active)
        self.client.post(toggle)
        other = Client()
        other.post(reverse("us02_login"), {"username": "donor1", "password": PASSWORD})
        self.assertNotIn("_auth_user_id", other.session)
        self.client.post(toggle)
        other.post(reverse("us02_login"), {"username": "donor1", "password": PASSWORD})
        self.assertIn("_auth_user_id", other.session)
        self.assertTrue(ActivityLog.objects.filter(action="USER_DEACTIVATED").exists())
        self.assertTrue(ActivityLog.objects.filter(action="USER_ACTIVATED").exists())


# ====================================================================== US-29
class AssignRolesTests(BaseCase):
    def setUp(self):
        self.login(self.admin)

    def assign(self, target, role):
        return self.client.post(reverse("us29_update_user_role", args=[target.pk]), {f"u{target.pk}-role": role})

    def test_page_shows_summary_and_filter(self):
        r = self.client.get(reverse("us29_assign_roles"))
        self.assertContains(r, "Administrator")
        r = self.client.get(reverse("us29_assign_roles"), {"role": "STAFF"})
        self.assertContains(r, "staff1")
        self.assertNotContains(r, "donor1")

    def test_assign_role_is_logged(self):
        self.assign(self.donor_user, "STAFF")
        self.donor_user.refresh_from_db()
        self.assertEqual(self.donor_user.role, "STAFF")
        log = ActivityLog.objects.get(action="ROLE_ASSIGNED")
        self.assertEqual(log.user, self.admin)
        self.assertIn("DONOR -> STAFF", log.details)

    def test_guards(self):
        self.assign(self.donor_user, "SUPERHERO")
        self.donor_user.refresh_from_db()
        self.assertEqual(self.donor_user.role, "DONOR")
        self.assign(self.admin, "DONOR")
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, "ADMIN")
        root2 = User.objects.create_superuser("root2", "root2@test.com", PASSWORD)
        self.assign(root2, "DONOR")
        root2.refresh_from_db()
        self.assertEqual(root2.role, "ADMIN")

    def test_last_active_administrator_is_protected(self):
        old_admin = User.objects.create_user("oldadmin", "old@test.com", PASSWORD, role="ADMIN", is_active=False)
        self.assign(old_admin, "DONOR")
        old_admin.refresh_from_db()
        self.assertEqual(old_admin.role, "ADMIN")

    def test_second_administrator_can_be_demoted(self):
        other = User.objects.create_user("admin2", "admin2@test.com", PASSWORD, role="ADMIN")
        self.assign(other, "STAFF")
        other.refresh_from_db()
        self.assertEqual(other.role, "STAFF")


# ====================================================================== US-31
class ReportTests(BaseCase):
    def setUp(self):
        self.login(self.staff)
        self.url = reverse("us31_generate_reports")
        donor = self.make_donor()
        today = timezone.localdate()
        self.new = Donation.objects.create(donor=donor, blood_group="O+", blood_bank=self.bank, quantity=2, status="STORED", donation_date=today)
        self.old = Donation.objects.create(donor=donor, blood_group="A+", blood_bank=self.bank2, quantity=1, status="STORED", donation_date=today - timedelta(days=40))
        self.stock(5, "O+")
        self.stock(3, "A+", bank=self.bank2)
        self.make_request()

    def csv(self, **params):
        r = self.client.get(self.url, {**params, "download": "csv"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "text/csv")
        return r.content.decode()

    def test_every_report_renders(self):  # 14-001..14-004
        titles = {"INVENTORY": "Inventory report", "DONATIONS": "Donations report", "REQUESTS": "Blood requests report",
                  "AVAILABILITY": "Availability report", "DONORS": "Donors report"}
        for kind, title in titles.items():
            for extra in ({}, {"blood_group": "O+"}, {"blood_bank": self.bank.pk},
                          {"date_from": (timezone.localdate() - timedelta(days=5)).isoformat(), "date_to": timezone.localdate().isoformat()}):
                with self.subTest(report=kind, extra=extra):
                    self.assertContains(self.client.get(self.url, {"report_type": kind, **extra}), title)

    def test_totals(self):
        self.assertContains(self.client.get(self.url, {"report_type": "INVENTORY"}), "Total units:</strong> 8")
        self.assertNotContains(self.client.get(self.url, {"report_type": "DONORS"}), "Total units:")

    def test_csv_downloads(self):  # 14-006 (CSV is the only export format)
        r = self.client.get(self.url, {"report_type": "INVENTORY", "download": "csv"})
        self.assertIn("inventory_report.csv", r["Content-Disposition"])
        body = r.content.decode()
        self.assertTrue(body.startswith("Blood bank,Blood group,Component,Units,Last updated"))
        self.assertIn("Central Blood Bank", body)

    def test_date_filter_on_donations(self):
        body = self.csv(report_type="DONATIONS", date_from=(timezone.localdate() - timedelta(days=5)).isoformat())
        self.assertIn(self.new.donation_id, body)
        self.assertNotIn(self.old.donation_id, body)
        body = self.csv(report_type="DONATIONS", date_to=(timezone.localdate() - timedelta(days=5)).isoformat())
        self.assertIn(self.old.donation_id, body)
        self.assertNotIn(self.new.donation_id, body)

    def test_group_and_bank_filters(self):
        body = self.csv(report_type="DONATIONS", blood_group="A+")
        self.assertIn(self.old.donation_id, body)
        self.assertNotIn(self.new.donation_id, body)
        body = self.csv(report_type="DONATIONS", blood_bank=self.bank.pk)
        self.assertIn(self.new.donation_id, body)
        self.assertNotIn(self.old.donation_id, body)

    def test_empty_report_message(self):
        tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()
        for kind in ("DONATIONS", "REQUESTS", "DONORS"):
            with self.subTest(report=kind):
                self.assertContains(self.client.get(self.url, {"report_type": kind, "date_from": tomorrow}), "No records for these filters")

    def test_invalid_date_range_and_missing_type(self):
        r = self.client.get(self.url, {"report_type": "DONATIONS", "date_from": "2030-01-02", "date_to": "2030-01-01"})
        self.assertContains(r, "must be after")
        self.assertNotContains(r, "Records:")
        r = self.client.get(self.url, {"blood_group": "O+"})
        self.assertNotContains(r, "Records:")

    def test_download_without_filters_does_not_crash(self):
        self.assertEqual(self.client.get(self.url, {"download": "csv"}).status_code, 200)


# ====================================================================== US-32
class SearchRecordsTests(BaseCase):
    def setUp(self):
        self.login(self.staff)
        self.url = reverse("us32_search_and_filter_records")
        today = timezone.localdate()
        self.d_a = self.make_donor("John Doe", "O+", "9876543210")
        self.d_b = self.make_donor("Priya Nair", "A-", "9123456780")
        type(self.d_b).objects.filter(pk=self.d_b.pk).update(address="Hubli")
        self.don1 = Donation.objects.create(donor=self.d_a, blood_group="O+", blood_bank=self.bank, status="STORED", donation_date=today)
        self.don2 = Donation.objects.create(donor=self.d_b, blood_group="A-", blood_bank=self.bank2, status="PENDING", donation_date=today - timedelta(days=40))
        self.r1 = self.make_request(self.donor_user, patient_name="Ravi")
        self.r2 = self.make_request(self.other_user, patient_name="Meena", blood_group="A-", blood_bank=self.bank2)
        BloodRequest.objects.filter(pk=self.r2.pk).update(status="ACCEPTED")

    def found(self, record_type, count, **params):
        r = self.client.get(self.url, {"record_type": record_type, **params})
        self.assertContains(r, f"<strong>{count}</strong> record(s) found.", msg_prefix=f"{record_type} {params}")
        return r

    def test_nothing_shown_until_a_search_is_made(self):
        self.assertNotContains(self.client.get(self.url), "record(s) found")
        self.assertNotContains(self.client.get(self.url, {"record_type": "NONSENSE"}), "record(s) found")

    def test_donor_search(self):  # 15-001, 15-003, 15-004
        today = timezone.localdate().isoformat()
        tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()
        self.found("DONORS", 2)
        self.found("DONORS", 1, q="priya")
        self.found("DONORS", 1, q=self.d_a.donor_id)
        self.found("DONORS", 1, q="9123456780")
        self.found("DONORS", 1, blood_group="O+")
        self.found("DONORS", 1, location="hubli")
        self.found("DONORS", 2, date_to=today)
        self.found("DONORS", 0, date_from=tomorrow)

    def test_donation_search(self):  # 15-002, 15-006, 15-007
        today = timezone.localdate()
        self.found("DONATIONS", 2)
        self.found("DONATIONS", 1, q=self.don1.donation_id)
        self.found("DONATIONS", 1, q="priya")
        self.found("DONATIONS", 1, blood_group="O+")
        self.found("DONATIONS", 1, status="STORED")
        self.found("DONATIONS", 0, status="ACCEPTED")  # a request status never matches a donation
        self.found("DONATIONS", 1, blood_bank=self.bank2.pk)
        self.found("DONATIONS", 1, location="mysuru")
        self.found("DONATIONS", 1, date_from=(today - timedelta(days=5)).isoformat())
        self.found("DONATIONS", 1, date_to=(today - timedelta(days=5)).isoformat())
        self.found("DONATIONS", 1, blood_group="O+", blood_bank=self.bank.pk, status="STORED")
        self.found("DONATIONS", 0, blood_group="A-", blood_bank=self.bank.pk)

    def test_request_search(self):  # 15-005
        today = timezone.localdate()
        self.found("REQUESTS", 2)
        self.found("REQUESTS", 1, q=self.r1.request_id)
        self.found("REQUESTS", 1, q="meena")
        self.found("REQUESTS", 1, q="donor1")
        self.found("REQUESTS", 1, blood_group="A-")
        self.found("REQUESTS", 1, status="ACCEPTED")
        self.found("REQUESTS", 0, status="STORED")
        self.found("REQUESTS", 1, blood_bank=self.bank2.pk)
        self.found("REQUESTS", 1, location="bengaluru")
        self.found("REQUESTS", 2, date_to=today.isoformat())
        self.found("REQUESTS", 0, date_from=(today + timedelta(days=1)).isoformat())

    def test_no_match_message(self):
        self.assertContains(self.client.get(self.url, {"record_type": "DONORS", "q": "zzzz"}), "No records match")


# ====================================================================== US-33  (NFR-12)
class ActivityLogTests(BaseCase):
    def setUp(self):
        self.login(self.admin)
        self.url = reverse("us33_view_system_activities")
        ActivityLog.record(self.staff, "CUSTOM_ACTION", "something happened")

    def test_filters(self):
        self.assertContains(self.client.get(self.url, {"user": "staff"}), "CUSTOM_ACTION")
        self.assertContains(self.client.get(self.url, {"action": "custom"}), "CUSTOM_ACTION")
        self.assertContains(self.client.get(self.url, {"action": "NOPE_NOPE"}), "No activity recorded")
        self.assertContains(self.client.get(self.url, {"user": "donor1", "action": "CUSTOM_ACTION"}), "No activity recorded")
        today = timezone.localdate()
        self.assertContains(self.client.get(self.url, {"date_to": today.isoformat()}), "CUSTOM_ACTION")
        self.assertContains(self.client.get(self.url, {"date_from": (today + timedelta(days=1)).isoformat()}), "No activity recorded")

    def test_paging(self):
        ActivityLog.objects.bulk_create([ActivityLog(action="BULK", details=str(i)) for i in range(60)])
        self.assertContains(self.client.get(self.url, {"action": "BULK"}), "Page 1 of 2")
        self.assertContains(self.client.get(self.url, {"action": "BULK", "page": 2}), "Page 2 of 2")
        self.assertContains(self.client.get(self.url, {"action": "BULK", "page": "abc"}), "Page 1 of 2")
        self.assertContains(self.client.get(self.url, {"action": "BULK", "page": 99}), "Page 2 of 2")
        self.assertContains(self.client.get(self.url, {"action": "BULK"}), "page=2")

    def test_signals_record_important_events(self):
        self.assertTrue(ActivityLog.objects.filter(action="USER_REGISTERED", details__startswith="donor1").exists())
        self.client.post(reverse("us02_logout"))
        self.assertTrue(ActivityLog.objects.filter(action="LOGOUT", details="admin").exists())

    @unittest.expectedFailure
    def test_status_change_log_records_who_changed_it(self):
        """KNOWN DEFECT (NFR-12): DONATION_UPDATED is logged against recorded_by, not the staff member who changed it."""
        staff2 = User.objects.create_user("staff2", "staff2@test.com", PASSWORD, role=User.ROLE_STAFF)
        donation = Donation.objects.create(donor=self.make_donor(), blood_group="O+", blood_bank=self.bank, recorded_by=self.staff)
        self.login(staff2)
        self.client.post(reverse("us13_update_donation_status", args=[donation.pk]), {"status": "TESTED"})
        self.assertEqual(ActivityLog.objects.get(action="DONATION_UPDATED").user, staff2)

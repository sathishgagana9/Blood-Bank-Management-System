"""Sprint 2 end-to-end tests:  python manage.py test"""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (ActivityLog, AvailabilitySubscription, BloodBank, BloodInventory, BloodRequest, Notification, User)


class Sprint2Flow(TestCase):
    def setUp(self):
        self.bank = BloodBank.objects.create(name="Central", location="Bengaluru")
        self.admin = User.objects.create_superuser("admin", "a@x.com", "pw12345!")
        self.staff = User.objects.create_user("staff", "s@x.com", "pw12345!", role=User.ROLE_STAFF)
        self.donor = User.objects.create_user("hosp", "h@x.com", "pw12345!")

    def login(self, user):
        self.client.force_login(user)

    def stock(self, qty, action="SET"):
        self.login(self.staff)
        return self.client.post(reverse("us15_update_blood_inventory"), {
            "blood_bank": self.bank.pk, "blood_group": "O+", "component": "WHOLE_BLOOD",
            "action": action, "quantity": qty, "reason": "count"})

    def test_us15_update_inventory_and_no_negative(self):
        self.stock(20)
        self.assertEqual(BloodInventory.objects.get().quantity, 20)
        r = self.stock(50, "REMOVE")  # would go below zero
        self.assertContains(r, "negative")
        self.assertEqual(BloodInventory.objects.get().quantity, 20)

    def test_request_lifecycle_us18_to_us25(self):
        self.stock(8)
        self.login(self.donor)
        self.client.post(reverse("us18_submit_blood_request"), {
            "patient_name": "Ravi", "blood_bank": self.bank.pk, "blood_group": "O+", "component": "WHOLE_BLOOD",
            "quantity": 5, "urgency": "URGENT", "contact": "9876543210", "required_by": (timezone.localdate() + timedelta(days=2)).isoformat(), "notes": ""})
        req = BloodRequest.objects.get()
        self.assertEqual(req.request_id, "REQ-00001")
        self.assertTrue(Notification.objects.filter(user=self.staff, category="NEW_REQUEST").exists())  # US-24
        self.login(self.staff)
        self.client.post(reverse("us20_accept_blood_request", args=[req.pk]))
        req.refresh_from_db(); self.assertEqual(req.status, "ACCEPTED")
        self.client.post(reverse("us22_fulfill_blood_request", args=[req.pk]))
        req.refresh_from_db(); self.assertEqual(req.status, "FULFILLED")
        self.assertEqual(BloodInventory.objects.get().quantity, 3)  # US-16 automatic deduction
        self.assertTrue(Notification.objects.filter(user=self.staff, category="LOW_STOCK").exists())  # US-23
        self.assertEqual(Notification.objects.filter(user=self.donor, category="REQUEST_STATUS").count(), 2)  # US-25

    def test_us20_cannot_accept_without_stock_and_us21_reject(self):
        self.login(self.donor)
        req = BloodRequest.objects.create(requester=self.donor, patient_name="X", blood_bank=self.bank, blood_group="O+",
                                          quantity=2, contact="9876543210", required_by=timezone.localdate())
        self.login(self.staff)
        self.client.post(reverse("us20_accept_blood_request", args=[req.pk]))
        req.refresh_from_db(); self.assertEqual(req.status, "PENDING")
        self.client.post(reverse("us21_reject_blood_request", args=[req.pk]), {"reason": "No stock"})
        req.refresh_from_db(); self.assertEqual((req.status, req.rejection_reason), ("REJECTED", "No stock"))

    def test_us26_availability_notification(self):
        self.login(self.donor)
        self.client.post(reverse("us26_availability_notification"), {"blood_group": "O+", "component": "", "blood_bank": ""})
        self.assertEqual(AvailabilitySubscription.objects.count(), 1)
        self.stock(10)
        self.assertTrue(Notification.objects.filter(user=self.donor, category="AVAILABILITY").exists())
        self.assertFalse(AvailabilitySubscription.objects.get().is_active)

    def test_role_protection(self):
        self.login(self.donor)
        for name in ("us15_update_blood_inventory", "us27_manage_blood_banks", "us28_manage_users", "us33_view_system_activities", "us31_generate_reports"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)

    def test_admin_stories(self):
        self.login(self.admin)
        self.client.post(reverse("us27_add_blood_bank"), {"name": "North", "location": "Mysuru", "is_active": "on"})
        self.assertTrue(BloodBank.objects.filter(name="North").exists())
        self.client.post(reverse("us29_update_user_role", args=[self.donor.pk]), {f"u{self.donor.pk}-role": User.ROLE_STAFF})
        self.donor.refresh_from_db(); self.assertEqual(self.donor.role, User.ROLE_STAFF)
        self.client.post(reverse("us28_toggle_user", args=[self.staff.pk]))
        self.staff.refresh_from_db(); self.assertFalse(self.staff.is_active)
        self.assertTrue(ActivityLog.objects.filter(action="ROLE_ASSIGNED").exists())
        self.assertEqual(self.client.get(reverse("us33_view_system_activities")).status_code, 200)

    def test_all_pages_load_for_staff_and_donor(self):
        self.login(self.staff)
        for name in ("home", "us14_view_blood_inventory", "us17_search_blood_availability", "us19_view_blood_requests", "us23_low_stock_alert",
                     "us24_view_notifications", "us30_view_overall_inventory", "us31_generate_reports", "us32_search_and_filter_records", "us15_update_blood_inventory"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        for q in ("?report_type=INVENTORY", "?report_type=DONATIONS", "?report_type=DONORS", "?report_type=AVAILABILITY", "?report_type=REQUESTS&download=csv"):
            self.assertEqual(self.client.get(reverse("us31_generate_reports") + q).status_code, 200, q)
        for rt in ("DONORS", "DONATIONS", "REQUESTS"):
            self.assertEqual(self.client.get(reverse("us32_search_and_filter_records") + f"?record_type={rt}").status_code, 200, rt)
        self.login(self.donor)
        for name in ("home", "us17_search_blood_availability", "us18_submit_blood_request", "us19_view_blood_requests", "us26_availability_notification"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)


class SharedRequirementChecks(TestCase):
    """Checks taken from the SRS test cases (FR-01, FR-02, FR-09)."""

    def test_fr01_registration_validation(self):
        base = {"username": "john", "first_name": "John", "last_name": "Doe", "email": "john@test.com",
                "phone": "9876543210", "address": "X", "password1": "Test@1234x", "password2": "Test@1234x"}
        bad_name = self.client.post(reverse("us01_register_user"), {**base, "first_name": "John@#$"})
        self.assertContains(bad_name, "Invalid characters in name")
        weak = self.client.post(reverse("us01_register_user"), {**base, "password1": "123", "password2": "123"})
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(weak.status_code, 200)
        self.client.post(reverse("us01_register_user"), base)
        self.assertEqual(User.objects.count(), 1)
        dup = self.client.post(reverse("us01_register_user"), {**base, "username": "john2"})
        self.assertContains(dup, "already registered")

    def test_fr02_login_with_email_and_us03_error(self):
        User.objects.create_user("jane", "jane@test.com", "Pass@123x")
        ok = self.client.post(reverse("us02_login"), {"username": "jane@test.com", "password": "Pass@123x"})
        self.assertEqual(ok.status_code, 302)
        self.client.logout()
        bad = self.client.post(reverse("us02_login"), {"username": "jane@test.com", "password": "WrongPass"})
        self.assertContains(bad, "Invalid username/email or password")

    def test_fr09_search_by_required_quantity(self):
        bank = BloodBank.objects.create(name="B", location="Hubli")
        BloodInventory.adjust(bank, "A+", "WHOLE_BLOOD", 6)
        u = User.objects.create_user("u", "u@x.com", "pw12345!"); self.client.force_login(u)
        url = reverse("us17_search_blood_availability")
        self.assertContains(self.client.get(url + "?min_quantity=5"), "Hubli")
        self.assertNotContains(self.client.get(url + "?min_quantity=7"), "Hubli</td>")

    def test_fr02_lockout_after_five_failed_attempts(self):
        User.objects.create_user("lock", "lock@test.com", "Right@123x")
        for _ in range(5):
            self.client.post(reverse("us02_login"), {"username": "lock", "password": "bad"})
        locked = self.client.post(reverse("us02_login"), {"username": "lock", "password": "Right@123x"})
        self.assertContains(locked, "Account locked")
        self.assertNotIn("_auth_user_id", self.client.session)

"""US-01 Register, US-02 Login/Logout, US-03 Invalid login + lockout, US-04 Roles, FR-16 permission matrix."""
import unittest
from datetime import timedelta

from django.contrib.auth import SESSION_KEY
from django.urls import reverse
from django.utils import timezone

from .models import ActivityLog, BloodBank, User
from .test_support import PASSWORD, BaseCase
from .us03_invalid_login_error import us03_is_locked


# ====================================================================== US-01  (FR-01)
class RegistrationTests(BaseCase):
    def setUp(self):
        self.url = reverse("us01_register_user")

    def reg(self, **overrides):
        data = {"username": "john", "first_name": "John", "last_name": "Doe", "email": "john@test.com",
                "phone": "9876543210", "address": "12 MG Road", "password1": "Test@1234x", "password2": "Test@1234x"}
        data.update(overrides)
        return data

    def rejected(self, response, before):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), before)

    def test_valid_registration_creates_donor_account(self):  # 1-001
        r = self.client.post(self.url, self.reg())
        self.assertRedirects(r, reverse("us02_login"))
        user = User.objects.get(username="john")
        self.assertEqual(user.role, User.ROLE_DONOR)
        self.assertTrue(user.check_password("Test@1234x"))
        self.assertTrue(ActivityLog.objects.filter(action="USER_REGISTERED", details__startswith="john").exists())

    def test_cannot_self_assign_a_higher_role(self):
        self.client.post(self.url, self.reg(role="ADMIN"))
        self.assertEqual(User.objects.get(username="john").role, User.ROLE_DONOR)

    def test_duplicate_email_rejected_case_insensitive(self):  # 1-002
        before = User.objects.count()
        r = self.client.post(self.url, self.reg(email="STAFF1@TEST.COM"))
        self.rejected(r, before)
        self.assertContains(r, "already registered")

    def test_duplicate_phone_rejected(self):  # 1-009
        self.client.post(self.url, self.reg())
        before = User.objects.count()
        r = self.client.post(self.url, self.reg(username="john2", email="j2@test.com"))
        self.rejected(r, before)
        self.assertContains(r, "already registered")

    def test_duplicate_username_rejected(self):
        before = User.objects.count()
        self.rejected(self.client.post(self.url, self.reg(username="staff1")), before)

    def test_invalid_email_rejected(self):  # 1-003
        before = User.objects.count()
        self.rejected(self.client.post(self.url, self.reg(email="invalidemail")), before)

    def test_weak_or_mismatched_password_rejected(self):  # 1-004
        before = User.objects.count()
        self.rejected(self.client.post(self.url, self.reg(password1="123", password2="123")), before)
        self.rejected(self.client.post(self.url, self.reg(password2="Different@123")), before)

    def test_each_required_field_is_mandatory(self):  # 1-005
        before = User.objects.count()
        for field in ("first_name", "last_name", "email", "phone", "address", "username"):
            with self.subTest(field=field):
                self.rejected(self.client.post(self.url, self.reg(**{field: ""})), before)

    def test_special_characters_or_digits_in_name_rejected(self):  # 1-006
        before = User.objects.count()
        for bad in ("John@#$", "J0hn", "'; DROP TABLE users;--"):
            with self.subTest(name=bad):
                r = self.client.post(self.url, self.reg(first_name=bad))
                self.rejected(r, before)
                self.assertContains(r, "Invalid characters in name")

    def test_overlong_name_rejected(self):  # 1-007
        before = User.objects.count()
        self.rejected(self.client.post(self.url, self.reg(last_name="A" * 151)), before)

    def test_invalid_phone_rejected(self):
        before = User.objects.count()
        self.rejected(self.client.post(self.url, self.reg(phone="ABC123")), before)

    def test_sql_text_in_free_text_field_is_stored_harmlessly(self):  # 1-008
        before = User.objects.count()
        self.client.post(self.url, self.reg(address="'; DROP TABLE users;--"))
        self.assertEqual(User.objects.count(), before + 1)
        self.assertEqual(User.objects.get(username="john").address, "'; DROP TABLE users;--")

    def test_logged_in_user_is_redirected_away(self):
        self.login(self.staff)
        self.assertRedirects(self.client.get(self.url), reverse("home"))


# ====================================================================== US-02 / US-03  (FR-02)
class LoginTests(BaseCase):
    def setUp(self):
        self.url = reverse("us02_login")

    def attempt(self, username="staff1", password=PASSWORD, **extra):
        return self.client.post(self.url, {"username": username, "password": password, **extra})

    def test_valid_login_by_username(self):  # 2-001
        r = self.attempt()
        self.assertRedirects(r, reverse("home"), fetch_redirect_response=False)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.staff.pk))
        self.assertTrue(ActivityLog.objects.filter(user=self.staff, action="LOGIN").exists())

    def test_wrong_password_shows_single_generic_message(self):  # 2-002
        r = self.attempt(password="WrongPass")
        self.assertContains(r, "Invalid username/email or password", count=1)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_unknown_user_gets_same_message(self):  # 2-003
        r = self.attempt(username="nobody")
        self.assertContains(r, "Invalid username/email or password", count=1)

    def test_empty_fields_rejected(self):  # 2-006, 2-007
        for data in ({"username": "", "password": PASSWORD}, {"username": "staff1", "password": ""}):
            with self.subTest(data=data):
                self.assertEqual(self.client.post(self.url, data).status_code, 200)
                self.assertNotIn(SESSION_KEY, self.client.session)

    def test_sql_injection_in_login_is_just_a_failed_login(self):  # 2-008
        r = self.attempt(username="' OR 1=1--")
        self.assertContains(r, "Invalid username/email or password")
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_inactive_account_cannot_log_in(self):
        self.donor_user.is_active = False
        self.donor_user.save()
        self.attempt(username="donor1")
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_next_parameter_only_allows_local_paths(self):
        r = self.attempt(next="/donors/")
        self.assertRedirects(r, "/donors/", fetch_redirect_response=False)
        self.client.logout()
        for evil in ("//evil.example.com", "http://evil.example.com"):
            with self.subTest(next=evil):
                r = self.attempt(next=evil)
                self.assertRedirects(r, reverse("home"), fetch_redirect_response=False)
                self.client.logout()

    def test_login_page_redirects_when_already_logged_in(self):
        self.login(self.staff)
        self.assertRedirects(self.client.get(self.url), reverse("home"), fetch_redirect_response=False)

    def test_logout_requires_post(self):
        self.login(self.staff)
        self.client.get(reverse("us02_logout"))
        self.assertIn(SESSION_KEY, self.client.session)
        self.client.post(reverse("us02_logout"))
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertTrue(ActivityLog.objects.filter(action="LOGOUT", details="staff1").exists())

    def test_failed_login_is_logged(self):
        self.attempt(password="bad")
        self.assertTrue(ActivityLog.objects.filter(action="LOGIN_FAILED", details="staff1").exists())

    def test_two_sessions_are_independent(self):  # 2-010
        from django.test import Client
        other = Client()
        self.login(self.staff)
        other.force_login(self.donor_user)
        self.assertEqual(self.client.get(reverse("us12_view_donation_records")).status_code, 200)
        self.assertEqual(other.get(reverse("us12_view_donation_records")).status_code, 403)


class LockoutTests(BaseCase):
    def setUp(self):
        self.url = reverse("us02_login")

    def bad(self, who="staff1"):
        return self.client.post(self.url, {"username": who, "password": "wrong"})

    def test_account_locks_on_fifth_failure(self):  # 2-004
        for _ in range(4):
            r = self.bad()
            self.assertContains(r, "Invalid username/email or password")
            self.assertNotContains(r, "Account locked")
        self.assertContains(self.bad(), "Account locked")

    def test_successful_login_resets_the_counter(self):
        for _ in range(3):
            self.bad()
        self.client.post(self.url, {"username": "staff1", "password": PASSWORD})
        self.client.post(reverse("us02_logout"))
        for _ in range(4):
            r = self.bad()
        self.assertNotContains(r, "Account locked")

    def test_lock_expires_after_fifteen_minutes(self):
        for _ in range(5):
            ActivityLog.record(None, "LOGIN_FAILED", "staff1")
        self.assertTrue(us03_is_locked("staff1"))
        ActivityLog.objects.filter(action="LOGIN_FAILED").update(created_at=timezone.now() - timedelta(minutes=16))
        self.assertFalse(us03_is_locked("staff1"))

    def test_is_locked_handles_blank_and_email_identifiers(self):
        self.assertFalse(us03_is_locked(""))
        for _ in range(5):
            ActivityLog.record(None, "LOGIN_FAILED", "staff1@test.com")
        self.assertTrue(us03_is_locked("staff1@test.com"))

    def test_failures_by_username_and_by_email_count_together(self):
        """Regression test, defect fixed: the counter is per typed identifier, so alternating username/e-mail avoids the lock."""
        for _ in range(3):
            ActivityLog.record(None, "LOGIN_FAILED", "staff1")
        for _ in range(2):
            ActivityLog.record(None, "LOGIN_FAILED", "staff1@test.com")
        self.assertTrue(us03_is_locked("staff1"))


# ====================================================================== US-04  (FR-16)
class UserRolePageTests(BaseCase):
    def post_role(self, target, role, url_name="us04_update_user_role"):
        return self.client.post(reverse(url_name, args=[target.pk]), {f"u{target.pk}-role": role})

    def test_admin_can_promote_donor_to_staff(self):
        self.login(self.admin)
        self.post_role(self.donor_user, User.ROLE_STAFF)
        self.donor_user.refresh_from_db()
        self.assertEqual(self.donor_user.role, User.ROLE_STAFF)

    def test_invalid_role_value_is_ignored(self):
        self.login(self.admin)
        self.post_role(self.donor_user, "SUPERHERO")
        self.donor_user.refresh_from_db()
        self.assertEqual(self.donor_user.role, User.ROLE_DONOR)

    def test_admin_cannot_change_own_role(self):
        self.login(self.admin)
        self.post_role(self.admin, User.ROLE_DONOR)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, User.ROLE_ADMIN)

    def test_superuser_is_always_administrator(self):
        other_admin = User.objects.create_superuser("root2", "root2@test.com", PASSWORD)
        self.login(self.admin)
        self.post_role(other_admin, User.ROLE_DONOR)
        other_admin.refresh_from_db()
        self.assertEqual(other_admin.role, User.ROLE_ADMIN)

    def test_get_request_changes_nothing(self):
        self.login(self.admin)
        self.client.get(reverse("us04_update_user_role", args=[self.donor_user.pk]))
        self.donor_user.refresh_from_db()
        self.assertEqual(self.donor_user.role, User.ROLE_DONOR)

    def test_role_change_takes_effect_immediately(self):  # 16-009
        self.login(self.donor_user)
        self.assertEqual(self.client.get(reverse("us06_view_donor")).status_code, 403)
        self.donor_user.role = User.ROLE_STAFF
        self.donor_user.save()
        self.assertEqual(self.client.get(reverse("us06_view_donor")).status_code, 200)

    def test_user_properties(self):
        self.assertTrue(self.staff.is_blood_bank_staff and not self.staff.is_administrator)
        self.assertTrue(self.admin.is_blood_bank_staff and self.admin.is_administrator)
        self.assertFalse(self.donor_user.is_blood_bank_staff)


# ====================================================================== FR-16 permission matrix
ALL_PAGES = ["us14_view_blood_inventory", "us17_search_blood_availability", "us18_submit_blood_request",
             "us19_view_blood_requests", "us24_view_notifications", "us26_availability_notification"]
STAFF_PAGES = ["us05_register_donor", "us06_view_donor", "us08_search_donor", "us11_record_blood_donation",
               "us12_view_donation_records", "us15_update_blood_inventory", "us23_low_stock_alert",
               "us30_view_overall_inventory", "us31_generate_reports", "us32_search_and_filter_records",
               "us34_blood_component_tracking"]
ADMIN_PAGES = ["us04_user_roles", "us27_manage_blood_banks", "us27_add_blood_bank", "us28_manage_users",
               "us28_create_user", "us29_assign_roles", "us33_view_system_activities"]


class RolePermissionMatrixTests(BaseCase):
    def check(self, names, user, expected):
        self.client.logout()
        if user:
            self.login(user)
        for name in names:
            with self.subTest(page=name, user=getattr(user, "username", "anonymous")):
                r = self.client.get(reverse(name))
                self.assertEqual(r.status_code, expected)
                if expected == 302:
                    self.assertIn("next=", r["Location"])

    def test_anonymous_is_sent_to_login_everywhere(self):  # 10-008, 16-007
        self.check(ALL_PAGES + STAFF_PAGES + ADMIN_PAGES + ["us10_update_personal_information"], None, 302)

    def test_donor_permissions(self):  # 16-001, 16-005
        self.check(ALL_PAGES + ["us10_update_personal_information"], self.donor_user, 200)
        self.check(STAFF_PAGES + ADMIN_PAGES, self.donor_user, 403)

    def test_staff_permissions(self):  # 16-002, 16-004
        self.check(ALL_PAGES + STAFF_PAGES, self.staff, 200)
        self.check(ADMIN_PAGES, self.staff, 403)

    def test_admin_permissions(self):  # 16-003
        self.check(ALL_PAGES + STAFF_PAGES + ADMIN_PAGES, self.admin, 200)

    def test_object_level_urls_are_protected(self):  # 16-007, 16-008
        from .models import Donation
        donor = self.make_donor()
        donation = Donation.objects.create(donor=donor, blood_group="O+", blood_bank=self.bank, recorded_by=self.staff)
        req = self.make_request()
        staff_only = [("us06_view_donor_detail", donor.pk), ("us07_update_donor", donor.pk),
                      ("us13_update_donation_status", donation.pk), ("us20_accept_blood_request", req.pk),
                      ("us21_reject_blood_request", req.pk), ("us22_fulfill_blood_request", req.pk)]
        admin_only = [("us27_edit_blood_bank", self.bank.pk), ("us27_toggle_blood_bank", self.bank.pk),
                      ("us28_edit_user", self.staff.pk), ("us28_toggle_user", self.staff.pk),
                      ("us29_update_user_role", self.staff.pk), ("us04_update_user_role", self.staff.pk)]
        self.login(self.donor_user)
        for name, pk in staff_only + admin_only:
            for method in ("get", "post"):
                with self.subTest(page=name, method=method, user="donor"):
                    self.assertEqual(getattr(self.client, method)(reverse(name, args=[pk])).status_code, 403)
        self.login(self.staff)
        for name, pk in admin_only:
            with self.subTest(page=name, user="staff"):
                self.assertEqual(self.client.post(reverse(name, args=[pk])).status_code, 403)
        self.client.logout()
        for name, pk in staff_only + admin_only:
            with self.subTest(page=name, user="anonymous"):
                self.assertEqual(self.client.post(reverse(name, args=[pk])).status_code, 302)
        # nothing changed
        req.refresh_from_db()
        self.assertEqual(req.status, "PENDING")
        self.assertTrue(BloodBank.objects.get(pk=self.bank.pk).is_active)
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)

"""Regression tests for the four defects found during testing (Sprint 3 fixes)."""
from django.urls import reverse

from .models import ActivityLog, Donation
from .test_support import BaseCase
from .us03_invalid_login_error import us03_is_locked


class Defect1NonNumericDonorParameter(BaseCase):
    def test_garbage_values_are_ignored(self):
        self.login(self.staff)
        donor = self.make_donor()
        for value in ("abc", "", "-1", "1.5", "1;DROP", "9999"):
            with self.subTest(value=value):
                self.assertEqual(self.client.get(reverse("us11_record_blood_donation"), {"donor": value}).status_code, 200)
        self.assertEqual(self.client.get(reverse("us11_record_blood_donation"), {"donor": donor.pk}).status_code, 200)


class Defect2DonorAuditHasUser(BaseCase):
    def test_register_update_and_profile_edit_record_the_user(self):
        self.login(self.staff)
        self.client.post(reverse("us05_register_donor"), self.donor_payload())
        from .models import Donor
        donor = Donor.objects.get()
        self.client.post(reverse("us07_update_donor", args=[donor.pk]), self.donor_payload(contact="9999999999"))
        self.assertEqual(ActivityLog.objects.get(action="DONOR_REGISTERED").user, self.staff)
        self.assertEqual(ActivityLog.objects.get(action="DONOR_UPDATED").user, self.staff)
        data = {"first_name": "Sam", "last_name": "Rao", "email": "staff1@test.com", "phone": "9123400000", "address": "Y"}
        self.client.post(reverse("us10_update_personal_information"), data)
        self.assertEqual(ActivityLog.objects.get(action="PROFILE_UPDATED").user, self.staff)


class Defect3LockoutCountsUsernameAndEmailTogether(BaseCase):
    def test_mixed_identifiers_trigger_the_lock(self):
        for _ in range(3):
            ActivityLog.record(None, "LOGIN_FAILED", "staff1")
        for _ in range(2):
            ActivityLog.record(None, "LOGIN_FAILED", "STAFF1@test.com")
        self.assertTrue(us03_is_locked("staff1"))
        self.assertTrue(us03_is_locked("staff1@test.com"))

    def test_other_accounts_are_not_affected(self):
        for _ in range(5):
            ActivityLog.record(None, "LOGIN_FAILED", "staff1")
        self.assertFalse(us03_is_locked("donor1"))
        self.assertFalse(us03_is_locked("donor1@test.com"))

    def test_unknown_identifier_still_counts_per_name(self):
        for _ in range(5):
            ActivityLog.record(None, "LOGIN_FAILED", "ghost")
        self.assertTrue(us03_is_locked("ghost"))


class Defect4StatusChangeLogsTheActor(BaseCase):
    def test_log_names_the_staff_member_who_changed_the_status(self):
        from .models import User
        staff2 = User.objects.create_user("staff2", "staff2@test.com", "Pw@12345x", role=User.ROLE_STAFF)
        donation = Donation.objects.create(donor=self.make_donor(), blood_group="O+", blood_bank=self.bank, recorded_by=self.staff)
        self.login(staff2)
        self.client.post(reverse("us13_update_donation_status", args=[donation.pk]), {"status": "TESTED"})
        log = ActivityLog.objects.get(action="DONATION_UPDATED")
        self.assertEqual(log.user, staff2)
        self.assertIn("PENDING -> TESTED", log.details)
        self.assertEqual(ActivityLog.objects.get(action="DONATION_RECORDED").user, self.staff)

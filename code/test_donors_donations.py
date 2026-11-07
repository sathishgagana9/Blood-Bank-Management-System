"""US-05..US-08 donors (FR-03, FR-04), US-09/US-10 history and profile, US-11..US-13 donations (FR-05), US-14 inventory view (FR-07)."""
import unittest
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from .models import ActivityLog, BloodInventory, Donation, Donor, User
from .test_support import PASSWORD, BaseCase


# ====================================================================== US-05  Register donor
class RegisterDonorTests(BaseCase):
    def setUp(self):
        self.url = reverse("us05_register_donor")
        self.login(self.staff)

    def test_staff_registers_donor_with_generated_id(self):  # 3-001
        r = self.client.post(self.url, self.donor_payload())
        donor = Donor.objects.get()
        self.assertEqual(donor.donor_id, f"DNR-{donor.pk:04d}")
        self.assertRedirects(r, reverse("us06_view_donor_detail", args=[donor.pk]))

    def test_two_donors_get_different_ids(self):  # 3-002, 4-006
        for n in range(2):
            self.client.post(self.url, self.donor_payload(name=f"Donor {n}"))
        ids = list(Donor.objects.values_list("donor_id", flat=True))
        self.assertEqual(len(set(ids)), 2)

    def test_invalid_input_is_rejected(self):  # 3-003, 3-004, 3-005, 3-008
        bad = [{"name": ""}, {"blood_group": "XYZ"}, {"contact": "ABC123"}, {"contact": "123"},
               {"name": "A" * 121}, {"address": ""}]
        for override in bad:
            with self.subTest(override=override):
                self.assertEqual(self.client.post(self.url, self.donor_payload(**override)).status_code, 200)
        self.assertEqual(Donor.objects.count(), 0)

    def test_link_to_donor_account(self):
        self.client.post(self.url, self.donor_payload(linked_username="donor1"))
        self.assertEqual(Donor.objects.get().user, self.donor_user)

    def test_link_validation(self):
        self.make_donor(user=self.other_user)
        cases = {"ghost": "No user with that username exists.",
                 "staff1": "Only donor-role accounts can be linked",
                 "donor2": "already linked to"}
        for username, message in cases.items():
            with self.subTest(username=username):
                self.assertContains(self.client.post(self.url, self.donor_payload(linked_username=username)), message)
        self.assertEqual(Donor.objects.count(), 1)

    def test_duplicate_contact_is_currently_allowed(self):  # 3-006 (not implemented: no warning)
        self.client.post(self.url, self.donor_payload())
        self.client.post(self.url, self.donor_payload(name="Jane Roe"))
        self.assertEqual(Donor.objects.count(), 2)

    def test_registration_is_logged(self):  # 3-009
        self.client.post(self.url, self.donor_payload())
        self.assertTrue(ActivityLog.objects.filter(action="DONOR_REGISTERED").exists())

    @unittest.expectedFailure
    def test_registration_log_records_the_staff_member(self):
        """KNOWN DEFECT (NFR-12): DONOR_REGISTERED is written with user=None."""
        self.client.post(self.url, self.donor_payload())
        self.assertEqual(ActivityLog.objects.get(action="DONOR_REGISTERED").user, self.staff)

    def test_donor_role_cannot_register(self):  # 3-007
        self.login(self.donor_user)
        self.assertEqual(self.client.post(self.url, self.donor_payload()).status_code, 403)
        self.assertEqual(Donor.objects.count(), 0)


# ====================================================================== US-06 / US-07 / US-08
class ViewUpdateSearchDonorTests(BaseCase):
    def setUp(self):
        self.login(self.staff)
        self.donor = self.make_donor("John Doe", "O+", "9876543210")
        self.other = self.make_donor("Priya Nair", "A-", "9123456780")

    def test_list_and_detail(self):  # 4-004
        r = self.client.get(reverse("us06_view_donor"))
        self.assertContains(r, "John Doe")
        self.assertContains(r, "Priya Nair")
        d = self.client.get(reverse("us06_view_donor_detail", args=[self.donor.pk]))
        self.assertContains(d, self.donor.donor_id)
        self.assertContains(d, "9876543210")

    def test_empty_list_message_and_404(self):
        Donor.objects.all().delete()
        self.assertContains(self.client.get(reverse("us06_view_donor")), "No donors registered yet")
        self.assertEqual(self.client.get(reverse("us06_view_donor_detail", args=[9999])).status_code, 404)

    def test_update_donor(self):  # 4-001
        url = reverse("us07_update_donor", args=[self.donor.pk])
        r = self.client.post(url, self.donor_payload(contact="9999999999", linked_username="donor1"))
        self.assertRedirects(r, reverse("us06_view_donor_detail", args=[self.donor.pk]))
        self.donor.refresh_from_db()
        self.assertEqual((self.donor.contact, self.donor.user), ("9999999999", self.donor_user))
        self.assertTrue(ActivityLog.objects.filter(action="DONOR_UPDATED").exists())

    def test_update_with_invalid_values_is_not_saved(self):  # 4-009
        url = reverse("us07_update_donor", args=[self.donor.pk])
        self.assertEqual(self.client.post(url, self.donor_payload(contact="ABC", blood_group="XYZ")).status_code, 200)
        self.donor.refresh_from_db()
        self.assertEqual((self.donor.contact, self.donor.blood_group), ("9876543210", "O+"))

    def test_update_form_shows_current_link_and_blank_unlinks(self):
        self.donor.user = self.donor_user
        self.donor.save()
        url = reverse("us07_update_donor", args=[self.donor.pk])
        self.assertContains(self.client.get(url), "donor1")
        self.client.post(url, self.donor_payload())
        self.donor.refresh_from_db()
        self.assertIsNone(self.donor.user)

    def test_search(self):  # 4-002, 4-003, 4-007
        url = reverse("us08_search_donor")
        self.assertNotContains(self.client.get(url), "<table>")  # nothing searched yet
        cases = [({"q": self.donor.donor_id}, "John Doe", "Priya Nair"), ({"q": "priya"}, "Priya Nair", "John Doe"),
                 ({"blood_group": "O+"}, "John Doe", "Priya Nair"), ({"contact": "91234"}, "Priya Nair", "John Doe")]
        for params, present, absent in cases:
            with self.subTest(params=params):
                r = self.client.get(url, params)
                self.assertContains(r, present)
                self.assertNotContains(r, absent)
        self.assertContains(self.client.get(url, {"q": "D9999"}), "No donors match")


# ====================================================================== US-09 / US-10
class HistoryAndProfileTests(BaseCase):
    def setUp(self):
        self.donor = self.make_donor("John Doe", "O+", user=self.donor_user)
        self.other = self.make_donor("Priya Nair", "A-", "9123456780", user=self.other_user)
        self.donation = Donation.objects.create(donor=self.donor, blood_group="O+", blood_bank=self.bank,
                                                quantity=2, status="STORED", recorded_by=self.staff)

    def test_donor_sees_own_history(self):
        self.login(self.donor_user)
        r = self.client.get(reverse("us09_view_my_donation_history"))
        self.assertContains(r, self.donation.donation_id)
        self.assertEqual(self.client.get(reverse("us09_view_donation_history", args=[self.donor.pk])).status_code, 200)

    def test_donor_cannot_see_someone_elses_history(self):  # 16-005
        self.login(self.donor_user)
        self.assertEqual(self.client.get(reverse("us09_view_donation_history", args=[self.other.pk])).status_code, 403)

    def test_donor_without_record_is_redirected_home(self):
        self.login(User.objects.create_user("new", "new@test.com", PASSWORD))
        self.assertRedirects(self.client.get(reverse("us09_view_my_donation_history")), reverse("home"), fetch_redirect_response=False)

    def test_staff_views_any_history_or_is_sent_to_list(self):
        self.login(self.staff)
        self.assertContains(self.client.get(reverse("us09_view_donation_history", args=[self.donor.pk])), self.donation.donation_id)
        self.assertRedirects(self.client.get(reverse("us09_view_my_donation_history")), reverse("us06_view_donor"), fetch_redirect_response=False)

    def test_profile_update_syncs_donor_record(self):  # 4-005
        self.login(self.donor_user)
        data = {"first_name": "Asha", "last_name": "Rao", "email": "asha@test.com", "phone": "9123456789", "address": "New Street"}
        self.assertRedirects(self.client.post(reverse("us10_update_personal_information"), data), reverse("us10_update_personal_information"))
        self.donor.refresh_from_db()
        self.donor_user.refresh_from_db()
        self.assertEqual(self.donor_user.email, "asha@test.com")
        self.assertEqual((self.donor.name, self.donor.contact, self.donor.address), ("Asha Rao", "9123456789", "New Street"))
        self.assertEqual(self.donor.blood_group, "O+")  # blood group cannot be changed by the donor

    def test_profile_update_rejects_missing_or_duplicate_data(self):
        self.login(self.donor_user)
        url = reverse("us10_update_personal_information")
        good = {"first_name": "Asha", "last_name": "Rao", "email": "asha@test.com", "phone": "9123456789", "address": "X"}
        self.client.post(url, {**good, "phone": ""})
        self.client.post(url, {**good, "email": "donor2@test.com"})
        self.donor_user.refresh_from_db()
        self.assertEqual(self.donor_user.email, "donor1@test.com")


# ====================================================================== US-11 / US-12 / US-13
class RecordDonationTests(BaseCase):
    def setUp(self):
        self.login(self.staff)
        self.donor = self.make_donor()
        self.url = reverse("us11_record_blood_donation")

    def test_stored_donation_adds_to_inventory(self):  # 5-001, 5-006
        r = self.client.post(self.url, self.donation_payload(self.donor))
        self.assertRedirects(r, reverse("us12_view_donation_records"))
        d = Donation.objects.get()
        self.assertEqual(d.donation_id, f"DON-{d.pk:05d}")
        self.assertEqual(d.recorded_by, self.staff)
        self.assertEqual(self.units(), 2)

    def test_pending_donation_does_not_change_inventory(self):
        self.client.post(self.url, self.donation_payload(self.donor, status="PENDING"))
        self.assertEqual(Donation.objects.count(), 1)
        self.assertEqual(BloodInventory.objects.count(), 0)

    def test_invalid_donations_are_rejected(self):  # 5-002, 5-003, 5-004, 5-007, 5-010
        tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()
        cases = [({"donation_date": tomorrow}, "cannot be in the future"), ({"quantity": 0}, None), ({"quantity": -100}, None),
                 ({"blood_group": "A+"}, "must match the donor"), ({"blood_group": "XYZ"}, None),
                 ({"donor": ""}, None), ({"blood_bank": ""}, None)]
        for override, message in cases:
            with self.subTest(override=override):
                r = self.client.post(self.url, self.donation_payload(self.donor, **override))
                self.assertEqual(r.status_code, 200)
                if message:
                    self.assertContains(r, message)
        self.assertEqual(Donation.objects.count(), 0)
        self.assertEqual(BloodInventory.objects.count(), 0)

    def test_inactive_bank_cannot_be_selected(self):
        self.bank2.is_active = False
        self.bank2.save()
        self.client.post(self.url, self.donation_payload(self.donor, blood_bank=self.bank2.pk))
        self.assertEqual(Donation.objects.count(), 0)

    def test_same_donor_same_day_twice_is_currently_allowed(self):  # 5-005 (not implemented)
        for _ in range(2):
            self.client.post(self.url, self.donation_payload(self.donor))
        self.assertEqual(Donation.objects.count(), 2)

    def test_prefill_from_query_string(self):
        self.assertEqual(self.client.get(self.url, {"donor": self.donor.pk}).status_code, 200)
        self.assertEqual(self.client.get(self.url, {"donor": 9999}).status_code, 200)

    @unittest.expectedFailure
    def test_non_numeric_donor_parameter_does_not_crash(self):
        """KNOWN DEFECT (NFR-11): ?donor=abc raises ValueError -> HTTP 500."""
        self.client.raise_request_exception = False
        self.assertEqual(self.client.get(self.url, {"donor": "abc"}).status_code, 200)

    def test_donation_is_logged_with_staff_user(self):  # 5-009
        self.client.post(self.url, self.donation_payload(self.donor))
        log = ActivityLog.objects.get(action="DONATION_RECORDED")
        self.assertEqual(log.user, self.staff)

    def test_donor_role_cannot_record(self):  # 5-008
        self.login(self.donor_user)
        self.assertEqual(self.client.post(self.url, self.donation_payload(self.donor)).status_code, 403)
        self.assertEqual(Donation.objects.count(), 0)


class DonationRecordsTests(BaseCase):
    def setUp(self):
        self.login(self.staff)
        self.donor = self.make_donor("John Doe", "O+")
        self.other = self.make_donor("Priya Nair", "A-", "9123456780")
        self.d1 = Donation.objects.create(donor=self.donor, blood_group="O+", blood_bank=self.bank, status="STORED", component="WHOLE_BLOOD")
        self.d2 = Donation.objects.create(donor=self.other, blood_group="A-", blood_bank=self.bank, status="PENDING", component="PLASMA")
        self.url = reverse("us12_view_donation_records")

    def test_lists_everything_without_filters(self):
        r = self.client.get(self.url)
        self.assertContains(r, self.d1.donation_id)
        self.assertContains(r, self.d2.donation_id)

    def test_filters(self):  # 15-002, 15-003
        cases = [({"donation_id": self.d1.donation_id}, self.d1, self.d2), ({"donor_id": self.other.donor_id}, self.d2, self.d1),
                 ({"blood_group": "O+"}, self.d1, self.d2), ({"component": "PLASMA"}, self.d2, self.d1),
                 ({"status": "STORED"}, self.d1, self.d2)]
        for params, present, absent in cases:
            with self.subTest(params=params):
                r = self.client.get(self.url, params)
                self.assertContains(r, present.donation_id)
                self.assertNotContains(r, absent.donation_id)

    def test_no_match_message(self):
        self.assertContains(self.client.get(self.url, {"donation_id": "DON-99999"}), "No donation records found")


class UpdateDonationStatusTests(BaseCase):
    def setUp(self):
        self.login(self.staff)
        self.donor = self.make_donor()
        self.client.post(reverse("us11_record_blood_donation"), self.donation_payload(self.donor, quantity=3, status="PENDING"))
        self.donation = Donation.objects.get()
        self.url = reverse("us13_update_donation_status", args=[self.donation.pk])

    def set_status(self, status):
        return self.client.post(self.url, {"status": status})

    def test_moving_to_stored_adds_stock_once(self):
        self.assertRedirects(self.set_status("STORED"), reverse("us12_view_donation_records"))
        self.assertEqual(self.units(), 3)
        self.set_status("STORED")  # repeat: no double count
        self.assertEqual(self.units(), 3)

    def test_leaving_stored_removes_stock(self):
        self.set_status("STORED")
        self.set_status("DISCARDED")
        self.assertEqual(self.units(), 0)
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.status, "DISCARDED")

    def test_pending_to_tested_changes_no_stock(self):
        self.set_status("TESTED")
        self.assertEqual(BloodInventory.objects.count(), 0)

    def test_status_change_is_rolled_back_when_stock_is_missing(self):  # 8-007, 8-008
        self.set_status("STORED")
        BloodInventory.adjust(self.bank, "O+", "WHOLE_BLOOD", -3)
        r = self.set_status("DISCARDED")
        self.assertContains(r, "negative")
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.status, "STORED")
        self.assertEqual(self.units(), 0)

    def test_invalid_status_and_missing_donation(self):
        self.assertEqual(self.set_status("LOST").status_code, 200)
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.status, "PENDING")
        self.assertEqual(self.client.get(reverse("us13_update_donation_status", args=[9999])).status_code, 404)

    def test_status_change_is_logged(self):
        self.set_status("TESTED")
        self.assertTrue(ActivityLog.objects.filter(action="DONATION_UPDATED").exists())


# ====================================================================== US-14
class ViewInventoryTests(BaseCase):
    def setUp(self):
        self.stock(5, "O+")
        self.stock(3, "A+", bank=self.bank2)
        self.stock(4, "O+", component="PLASMA")
        self.url = reverse("us14_view_blood_inventory")

    def test_staff_and_donor_can_view_totals(self):  # 7-001, 7-008
        for user in (self.staff, self.donor_user):
            self.login(user)
            r = self.client.get(self.url)
            self.assertContains(r, "</strong> 12</p>")

    def test_filters(self):  # 7-005, 7-010
        self.login(self.staff)
        self.assertContains(self.client.get(self.url, {"blood_group": "O+"}), "</strong> 9</p>")
        self.assertContains(self.client.get(self.url, {"blood_bank": self.bank2.pk}), "</strong> 3</p>")
        self.assertContains(self.client.get(self.url, {"component": "PLASMA"}), "</strong> 4</p>")
        both = self.client.get(self.url, {"blood_bank": self.bank.pk, "blood_group": "O+"})
        self.assertContains(both, "</strong> 9</p>")

    def test_empty_inventory_message(self):
        BloodInventory.objects.all().delete()
        self.login(self.staff)
        self.assertContains(self.client.get(self.url), "No inventory records yet")

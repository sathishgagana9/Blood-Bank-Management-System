"""Automated evidence for non-functional requirements (NFR-01, NFR-04, NFR-09, NFR-13)."""
import os
import tempfile
import time

from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.urls import reverse

from .models import BLOOD_GROUPS, BloodBank, BloodInventory, Donation, Donor
from .test_support import BaseCase


class PerformanceTests(BaseCase):
    """NFR-01: blood-availability search returns within 2 seconds on a realistic data set."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        banks = BloodBank.objects.bulk_create(
            [BloodBank(name=f"Bank {i:03d}", location=f"City {i % 10}", contact="9876500000") for i in range(100)]
        )
        rows = [
            BloodInventory(blood_bank=b, blood_group=g, component=c, quantity=(i % 20) + 1)
            for i, b in enumerate(banks) for g, _ in BLOOD_GROUPS for c, _l in Donation.COMPONENT_CHOICES
        ]
        BloodInventory.objects.bulk_create(rows)  # 100 banks x 8 groups x 4 components = 3,200 rows

    def timed_search(self, params):
        self.login(self.donor_user)
        start = time.perf_counter()
        response = self.client.get(reverse("us17_search_blood_availability"), params)
        elapsed = time.perf_counter() - start
        self.assertEqual(response.status_code, 200)
        print(f"\n[NFR-01] search {params or '(no filters)'}: {elapsed:.3f}s")
        return elapsed

    def test_filtered_search_under_two_seconds(self):
        self.assertLess(self.timed_search({"blood_group": "O+", "location": "City 3", "min_quantity": 5}), 2.0)

    def test_search_by_group_under_two_seconds(self):
        self.assertLess(self.timed_search({"blood_group": "A+"}), 2.0)

    def test_unfiltered_search_under_two_seconds(self):
        self.assertLess(self.timed_search({}), 2.0)


class BackupRestoreTests(BaseCase):
    """NFR-09: data can be exported and restored after a failure."""

    def test_dump_and_restore_round_trip(self):
        donor = self.make_donor()
        donation = Donation.objects.create(donor=donor, blood_group="O+", blood_bank=self.bank, quantity=2, status="STORED", recorded_by=self.staff)
        self.stock(7)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "backup.json")
            call_command("dumpdata", "core", output=path, verbosity=0)
            self.assertGreater(os.path.getsize(path), 0)
            # simulate data loss
            Donation.objects.all().delete()
            Donor.objects.all().delete()
            BloodInventory.objects.all().delete()
            self.assertEqual((Donor.objects.count(), BloodInventory.objects.count()), (0, 0))
            call_command("loaddata", path, verbosity=0)
        self.assertEqual(Donor.objects.get().donor_id, donor.donor_id)
        self.assertEqual(Donation.objects.get().donation_id, donation.donation_id)
        self.assertEqual(self.units(), 7)


class DataIntegrityTests(BaseCase):
    """NFR-13 / NFR-04: the database itself refuses duplicate IDs, duplicate stock rows and negative stock."""

    def test_duplicate_donor_id_rejected(self):
        self.make_donor()
        Donor.objects.filter().update(donor_id="DNR-TEST")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Donor.objects.create(donor_id="DNR-TEST", name="Clone", blood_group="O+", contact="9876543211", address="X")

    def test_duplicate_donation_id_rejected(self):
        donor = self.make_donor()
        Donation.objects.create(donor=donor, blood_group="O+", blood_bank=self.bank)
        existing = Donation.objects.get().donation_id
        with self.assertRaises(IntegrityError), transaction.atomic():
            Donation.objects.create(donation_id=existing, donor=donor, blood_group="O+", blood_bank=self.bank)

    def test_duplicate_inventory_row_rejected(self):
        self.stock(1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            BloodInventory.objects.create(blood_bank=self.bank, blood_group="O+", component="WHOLE_BLOOD", quantity=1)

    def test_database_refuses_negative_stock(self):
        self.stock(1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            BloodInventory.objects.filter(blood_bank=self.bank).update(quantity=-1)
        self.assertEqual(self.units(), 1)

    def test_donor_with_donations_cannot_be_deleted(self):
        donor = self.make_donor()
        Donation.objects.create(donor=donor, blood_group="O+", blood_bank=self.bank)
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            donor.delete()

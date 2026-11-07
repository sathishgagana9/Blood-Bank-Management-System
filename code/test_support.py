"""Shared fixtures for the automated tests (used by the Unit Test and System Validation reports)."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

# Importing this module registers the activity-log signal handlers (US-33), so the tests do not depend on
# whether the URL conf has been loaded yet.
from . import us33_view_system_activities  # noqa: F401
from .models import BloodBank, BloodInventory, BloodRequest, Donor, User

PASSWORD = "Pw@12345x"


class BaseCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bank = BloodBank.objects.create(name="Central Blood Bank", location="Bengaluru", contact="9876500001")
        cls.bank2 = BloodBank.objects.create(name="North Blood Bank", location="Mysuru", contact="9876500002")
        cls.admin = User.objects.create_superuser("admin", "admin@test.com", PASSWORD)
        cls.staff = User.objects.create_user("staff1", "staff1@test.com", PASSWORD, role=User.ROLE_STAFF)
        cls.donor_user = User.objects.create_user("donor1", "donor1@test.com", PASSWORD)
        cls.other_user = User.objects.create_user("donor2", "donor2@test.com", PASSWORD)

    # ---- helpers
    def login(self, user):
        self.client.force_login(user)

    def make_donor(self, name="John Doe", group="O+", contact="9876543210", user=None):
        return Donor.objects.create(name=name, blood_group=group, contact=contact, address="12 MG Road", user=user)

    def donor_payload(self, **overrides):
        data = {"name": "John Doe", "blood_group": "O+", "contact": "9876543210", "address": "12 MG Road", "linked_username": ""}
        data.update(overrides)
        return data

    def donation_payload(self, donor, **overrides):
        data = {
            "donor": donor.pk, "blood_group": donor.blood_group,
            "donation_date": timezone.localdate().isoformat(), "blood_bank": self.bank.pk,
            "quantity": 2, "component": "WHOLE_BLOOD", "status": "STORED",
        }
        data.update(overrides)
        return data

    def stock(self, qty, group="O+", component="WHOLE_BLOOD", bank=None):
        return BloodInventory.adjust(bank or self.bank, group, component, qty)

    def units(self, group="O+", component="WHOLE_BLOOD", bank=None):
        row = BloodInventory.objects.filter(blood_bank=bank or self.bank, blood_group=group, component=component).first()
        return row.quantity if row else 0

    def make_request(self, requester=None, **overrides):
        data = dict(
            requester=requester or self.donor_user, patient_name="Ravi", blood_bank=self.bank, blood_group="O+",
            component="WHOLE_BLOOD", quantity=2, contact="9876543210",
            required_by=timezone.localdate() + timedelta(days=2),
        )
        data.update(overrides)
        return BloodRequest.objects.create(**data)

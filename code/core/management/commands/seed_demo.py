"""Fills the database with demo data so every screen can be shown straight away:  python manage.py seed_demo"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (BloodBank, BloodInventory, BloodRequest, Donation, Donor, User,
                         apply_donation_inventory_effect)
from core.us24_new_request_notification import us24_notify_new_request

USERS = [  # username, password, role, first, last, phone
    ("admin", "Admin@12345", User.ROLE_ADMIN, "System", "Admin", "9000000001"),
    ("staff1", "Staff@12345", User.ROLE_STAFF, "Sita", "Rao", "9000000002"),
    ("donor1", "Donor@12345", User.ROLE_DONOR, "Ravi", "Kumar", "9000000003"),
    ("hospital1", "Hosp@12345", User.ROLE_DONOR, "City", "Hospital", "9000000004"),
]


class Command(BaseCommand):
    help = "Create demo users, blood banks, donors, donations, stock and requests."

    def handle(self, *args, **options):
        if User.objects.filter(username="admin").exists():
            self.stdout.write("Demo data already exists (user 'admin' found). Nothing to do.")
            return
        users = {}
        for username, pwd, role, first, last, phone in USERS:
            u = User.objects.create_user(username, f"{username}@example.com", pwd, role=role,
                                         first_name=first, last_name=last, phone=phone, address="Bengaluru")
            if role == User.ROLE_ADMIN:
                u.is_staff = u.is_superuser = True  # lets the admin also open /admin/
                u.save()
            users[username] = u

        central = BloodBank.objects.create(name="Central Blood Bank", location="Bengaluru", address="MG Road", contact="08000000001")
        north = BloodBank.objects.create(name="North Blood Bank", location="Mysuru", address="Ring Road", contact="08000000002")

        donor = Donor.objects.create(name="Ravi Kumar", blood_group="O+", contact="9000000003", address="Bengaluru", user=users["donor1"])
        donor2 = Donor.objects.create(name="Anita Sharma", blood_group="A+", contact="9000000005", address="Mysuru")

        # donations marked Stored add to inventory automatically (US-11 / US-13)
        for dn, group, bank, qty, comp in ((donor, "O+", central, 12, "WHOLE_BLOOD"), (donor2, "A+", north, 8, "RBC")):
            d = Donation.objects.create(donor=dn, blood_group=group, donation_date=timezone.localdate() - timedelta(days=3),
                                        blood_bank=bank, quantity=qty, component=comp, status=Donation.STATUS_STORED,
                                        recorded_by=users["staff1"])
            apply_donation_inventory_effect(d, None)
        Donation.objects.create(donor=donor, blood_group="O+", donation_date=timezone.localdate(), blood_bank=central,
                                quantity=1, component="PLASMA", status=Donation.STATUS_PENDING, recorded_by=users["staff1"])

        # extra stock (some deliberately low so US-23 has something to show)
        for bank, group, comp, qty in ((central, "B+", "WHOLE_BLOOD", 15), (central, "AB-", "WHOLE_BLOOD", 2),
                                       (central, "O-", "PLATELETS", 4), (north, "O+", "WHOLE_BLOOD", 20),
                                       (north, "B-", "PLASMA", 9)):
            BloodInventory.adjust(bank, group, comp, qty)

        req = BloodRequest.objects.create(requester=users["hospital1"], patient_name="Mohan", blood_bank=central, blood_group="O+",
                                          quantity=3, urgency="URGENT", contact="9000000004",
                                          required_by=timezone.localdate() + timedelta(days=1), notes="Surgery")
        us24_notify_new_request(req)
        self.stdout.write(self.style.SUCCESS("Demo data created."))
        self.stdout.write("Logins:  admin / Admin@12345   staff1 / Staff@12345   donor1 / Donor@12345   hospital1 / Hosp@12345")

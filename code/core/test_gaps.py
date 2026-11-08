"""Closes the last partially covered branches reported by `coverage report -m`."""
from django.urls import reverse

from .models import Donor, User
from .test_support import BaseCase
from .us01_register_user import US01RegisterUserForm
from .us05_register_donor import US05DonorForm


class RemainingBranchTests(BaseCase):
    def test_register_form_save_without_commit(self):  # us01 58->60
        form = US01RegisterUserForm({"username": "dry", "first_name": "Dry", "last_name": "Run", "email": "dry@test.com",
                                     "phone": "9000000099", "address": "X", "password1": "Test@1234x", "password2": "Test@1234x"})
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save(commit=False)
        self.assertIsNone(user.pk)
        self.assertEqual(user.role, User.ROLE_DONOR)

    def test_donor_form_save_without_commit(self):  # us05 51->53
        form = US05DonorForm(self.donor_payload())
        self.assertTrue(form.is_valid(), form.errors)
        donor = form.save(commit=False)
        self.assertIsNone(donor.pk)
        self.assertEqual(Donor.objects.count(), 0)

    def test_profile_update_for_user_without_donor_record(self):  # us10 46->51
        self.login(self.staff)
        data = {"first_name": "Sam", "last_name": "Rao", "email": "staff1@test.com", "phone": "9123400000", "address": "Y"}
        self.client.post(reverse("us10_update_personal_information"), data)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.first_name, "Sam")
        self.assertEqual(Donor.objects.count(), 0)

    def test_assign_role_url_ignores_get(self):  # us29 49->66
        self.login(self.admin)
        r = self.client.get(reverse("us29_update_user_role", args=[self.donor_user.pk]))
        self.assertRedirects(r, reverse("us29_assign_roles"))
        self.donor_user.refresh_from_db()
        self.assertEqual(self.donor_user.role, User.ROLE_DONOR)

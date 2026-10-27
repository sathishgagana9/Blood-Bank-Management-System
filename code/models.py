"""Shared data models for Blood Bank Management System."""
from django.contrib.auth.models import AbstractUser
from django.db import models

BLOOD_GROUPS = [
    ("A+", "A+"),
    ("A-", "A-"),
    ("B+", "B+"),
    ("B-", "B-"),
    ("AB+", "AB+"),
    ("AB-", "AB-"),
    ("O+", "O+"),
    ("O-", "O-"),
]


class User(AbstractUser):
    """Custom user model with role-based access control."""

    ROLE_DONOR = "donor"
    ROLE_STAFF = "staff"
    ROLE_ADMIN = "admin"

    ROLE_CHOICES = (
        (ROLE_DONOR, "Donor"),
        (ROLE_STAFF, "Staff"),
        (ROLE_ADMIN, "Administrator"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_DONOR)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    def is_donor(self):
        return self.role == self.ROLE_DONOR

    def is_blood_bank_staff(self):
        return self.role in (self.ROLE_STAFF, self.ROLE_ADMIN)

    def is_administrator(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser


class Donor(models.Model):
    """Donor registration and record model."""

    donor_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUPS)
    contact = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, blank=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="donor_profile",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.donor_id} - {self.name} ({self.blood_group})"


class Donation(models.Model):
    """Blood donation transaction record."""

    donation_id = models.CharField(max_length=20, unique=True)
    donor = models.ForeignKey(
        Donor,
        on_delete=models.CASCADE,
        related_name="donations",
    )
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUPS)
    date = models.DateField()
    blood_bank = models.CharField(max_length=100)
    quantity = models.IntegerField(help_text="Volume in ml")
    status = models.CharField(max_length=20, default="Completed")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.donation_id} - {self.donor.name} ({self.blood_group})"


class BloodRequest(models.Model):
    """Blood request record."""

    URGENCY_CHOICES = (
        ("Normal", "Normal"),
        ("Urgent", "Urgent"),
        ("Critical", "Critical"),
    )

    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Accepted", "Accepted"),
        ("Rejected", "Rejected"),
        ("Fulfilled", "Fulfilled"),
    )

    request_id = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="blood_requests",
    )
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUPS)
    quantity = models.IntegerField(help_text="Volume in ml or units")
    location = models.CharField(max_length=150)
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default="Normal")
    contact = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.request_id} - {self.blood_group} ({self.urgency})"

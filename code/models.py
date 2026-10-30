"""Shared data models used by the Sprint 1 user stories.

  User            -> US-01, US-02, US-04, US-10
  Donor           -> US-05, US-06, US-07, US-08, US-09
  BloodBank       -> US-11, US-14 (added through Django admin in Sprint 1)
  Donation        -> US-09, US-11, US-12, US-13, US-34
  BloodInventory  -> US-14, US-34 (Sprint 1);  US-15, US-16, US-23, US-26, US-30 (Sprint 2)

Sprint 2 additions:
  BloodRequest             -> US-18 .. US-22, US-24, US-25, US-31, US-32
  Notification             -> US-23, US-24, US-25, US-26
  AvailabilitySubscription -> US-26
  ActivityLog              -> US-33 (and every story that changes data)
"""
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

BLOOD_GROUPS = [(g, g) for g in ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")]

phone_validator = RegexValidator(
    regex=r"^\+?[0-9]{7,15}$",
    message="Enter a valid phone number (7-15 digits, optional leading +).",
)


class User(AbstractUser):
    ROLE_DONOR, ROLE_STAFF, ROLE_ADMIN = "DONOR", "STAFF", "ADMIN"
    ROLE_CHOICES = [
        (ROLE_DONOR, "Donor"),
        (ROLE_STAFF, "Blood Bank Staff"),
        (ROLE_ADMIN, "Administrator"),
    ]

    email = models.EmailField("email address", unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_DONOR)
    phone = models.CharField(max_length=16, validators=[phone_validator], blank=True)
    address = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if self.is_superuser:  # users made with `createsuperuser` are administrators
            self.role = self.ROLE_ADMIN
        super().save(*args, **kwargs)

    @property
    def is_blood_bank_staff(self):
        return self.role in (self.ROLE_STAFF, self.ROLE_ADMIN)

    @property
    def is_administrator(self):
        return self.role == self.ROLE_ADMIN


class BloodBank(models.Model):
    name = models.CharField(max_length=120, unique=True)
    address = models.TextField(blank=True)
    location = models.CharField(max_length=120)
    contact = models.CharField(max_length=16, validators=[phone_validator], blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Donor(models.Model):
    donor_id = models.CharField(max_length=12, unique=True, null=True, editable=False)  # DNR-0001
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="donor_profile")
    name = models.CharField(max_length=120)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUPS)
    contact = models.CharField(max_length=16, validators=[phone_validator])
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["donor_id"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.donor_id:
            self.donor_id = f"DNR-{self.pk:04d}"
            super().save(update_fields=["donor_id"])

    def __str__(self):
        return f"{self.donor_id} - {self.name} ({self.blood_group})"


class Donation(models.Model):
    COMPONENT_CHOICES = [
        ("WHOLE_BLOOD", "Whole Blood"),
        ("PLASMA", "Plasma"),
        ("PLATELETS", "Platelets"),
        ("RBC", "Red Blood Cells (RBC)"),
    ]
    STATUS_PENDING, STATUS_TESTED, STATUS_STORED, STATUS_DISCARDED = "PENDING", "TESTED", "STORED", "DISCARDED"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_TESTED, "Tested"),
        (STATUS_STORED, "Stored (added to inventory)"),
        (STATUS_DISCARDED, "Discarded"),
    ]

    donation_id = models.CharField(max_length=12, unique=True, null=True, editable=False)  # DON-00001
    donor = models.ForeignKey(Donor, on_delete=models.PROTECT, related_name="donations")
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUPS)
    donation_date = models.DateField(default=timezone.localdate)
    blood_bank = models.ForeignKey(BloodBank, on_delete=models.PROTECT, related_name="donations")
    quantity = models.PositiveIntegerField("quantity (units)", validators=[MinValueValidator(1)], default=1)
    component = models.CharField(max_length=12, choices=COMPONENT_CHOICES, default="WHOLE_BLOOD")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="recorded_donations")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-donation_date", "-id"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.donation_id:
            self.donation_id = f"DON-{self.pk:05d}"
            super().save(update_fields=["donation_id"])

    def __str__(self):
        return f"{self.donation_id} ({self.blood_group})"


class BloodInventory(models.Model):
    blood_bank = models.ForeignKey(BloodBank, on_delete=models.CASCADE, related_name="inventory")
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUPS)
    component = models.CharField(max_length=12, choices=Donation.COMPONENT_CHOICES)
    quantity = models.PositiveIntegerField(default=0)  # can never be negative
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["blood_bank__name", "blood_group", "component"]
        verbose_name_plural = "blood inventory"
        constraints = [
            models.UniqueConstraint(fields=["blood_bank", "blood_group", "component"], name="unique_inventory_row")
        ]

    def __str__(self):
        return f"{self.blood_bank} / {self.blood_group} / {self.component}: {self.quantity}"

    @classmethod
    def adjust(cls, blood_bank, blood_group, component, delta):
        """Add or remove units; refuses to let stock go below zero."""
        with transaction.atomic():
            row, _ = cls.objects.select_for_update().get_or_create(
                blood_bank=blood_bank, blood_group=blood_group, component=component
            )
            old_quantity = row.quantity
            if row.quantity + delta < 0:
                raise ValidationError("Not enough units in inventory: this change would make stock negative.")
            row.quantity += delta
            row.save()
        inventory_changed(row, old_quantity)  # Sprint 2: US-23 low stock alert + US-26 availability alert
        return row


def apply_donation_inventory_effect(donation, old_status):
    """A donation counts as stock only while its status is STORED (used by US-11 and US-13)."""
    was_stored = old_status == Donation.STATUS_STORED
    is_stored = donation.status == Donation.STATUS_STORED
    args = (donation.blood_bank, donation.blood_group, donation.component)
    if is_stored and not was_stored:
        BloodInventory.adjust(*args, donation.quantity)
    elif was_stored and not is_stored:
        BloodInventory.adjust(*args, -donation.quantity)


def inventory_changed(row, old_quantity):
    """Sprint 1 inventory update hook.

    Sprint 2 notifications are not included in this integration.
    """
    return None


# ======================================================================= Sprint 2 models
class BloodRequest(models.Model):
    STATUS_PENDING, STATUS_ACCEPTED, STATUS_REJECTED, STATUS_FULFILLED = "PENDING", "ACCEPTED", "REJECTED", "FULFILLED"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_FULFILLED, "Fulfilled"),
    ]

    request_id = models.CharField(max_length=12, unique=True, null=True, editable=False)  # REQ-00001
    requester = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="blood_requests")
    patient_name = models.CharField(max_length=120)
    blood_bank = models.ForeignKey(BloodBank, on_delete=models.PROTECT, related_name="blood_requests")
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUPS)
    component = models.CharField(max_length=12, choices=Donation.COMPONENT_CHOICES, default="WHOLE_BLOOD")
    quantity = models.PositiveIntegerField("quantity (units)", validators=[MinValueValidator(1)], default=1)
    URGENCY_CHOICES = [("NORMAL", "Normal"), ("URGENT", "Urgent"), ("CRITICAL", "Critical")]
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, default="NORMAL")
    contact = models.CharField("contact number", max_length=16, validators=[phone_validator])
    required_by = models.DateField()
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    rejection_reason = models.TextField(blank=True)
    handled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="handled_requests")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.request_id:
            self.request_id = f"REQ-{self.pk:05d}"
            super().save(update_fields=["request_id"])

    def __str__(self):
        return f"{self.request_id} ({self.blood_group} x{self.quantity})"


class Notification(models.Model):
    CATEGORY_CHOICES = [
        ("NEW_REQUEST", "New request"),
        ("REQUEST_STATUS", "Request status"),
        ("LOW_STOCK", "Low stock"),
        ("AVAILABILITY", "Availability"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    message = models.CharField(max_length=300)
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    @classmethod
    def send(cls, users, category, message, link=""):
        cls.objects.bulk_create([cls(user=u, category=category, message=message, link=link) for u in users])


class AvailabilitySubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="availability_subscriptions")
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUPS)
    component = models.CharField(max_length=12, choices=Donation.COMPONENT_CHOICES, blank=True)  # blank = any
    blood_bank = models.ForeignKey(BloodBank, on_delete=models.CASCADE, null=True, blank=True)  # null = any
    is_active = models.BooleanField(default=True)  # becomes False once the user has been notified
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="activities")
    action = models.CharField(max_length=40)
    details = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    @classmethod
    def record(cls, user, action, details=""):
        cls.objects.create(user=user if getattr(user, "pk", None) else None, action=action, details=details[:300])

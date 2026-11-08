"""Django admin registrations (blood banks are now managed on the US-27 page; admin stays as a backup)."""
from django.contrib import admin

from .models import ActivityLog, AvailabilitySubscription, BloodBank, BloodInventory, BloodRequest, Notification

for model in (BloodBank, BloodInventory, BloodRequest, Notification, AvailabilitySubscription, ActivityLog):
    admin.site.register(model)

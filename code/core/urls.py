"""Collects the URLs of every user story (Sprint 1 + Sprint 2)."""
from django.contrib import admin
from django.urls import path

from . import (
    us01_register_user, us02_login, us04_user_roles, us05_register_donor, us06_view_donor, us07_update_donor,
    us08_search_donor, us09_view_donation_history, us10_update_personal_information, us11_record_blood_donation,
    us12_view_donation_records, us13_update_donation_status, us14_view_blood_inventory,
    us34_blood_component_tracking,
    # ---- Sprint 2
    us15_update_blood_inventory, us17_search_blood_availability, us18_submit_blood_request,
    us19_view_blood_requests, us20_accept_blood_request, us21_reject_blood_request, us22_fulfill_blood_request,
    us23_low_stock_alert, us24_new_request_notification, us26_availability_notification,
    us27_manage_blood_banks, us28_manage_users, us29_assign_roles, us30_view_overall_inventory,
    us31_generate_reports, us32_search_and_filter_records, us33_view_system_activities,
)
from .common import home

urlpatterns = [path("admin/", admin.site.urls), path("", home, name="home")]

# US-03, US-16, US-25 have no page of their own (error message / automatic logic used by other stories).
for story in (
    us01_register_user, us02_login, us04_user_roles, us05_register_donor, us06_view_donor, us07_update_donor,
    us08_search_donor, us09_view_donation_history, us10_update_personal_information, us11_record_blood_donation,
    us12_view_donation_records, us13_update_donation_status, us14_view_blood_inventory,
    us34_blood_component_tracking,
    us15_update_blood_inventory, us17_search_blood_availability, us18_submit_blood_request,
    us19_view_blood_requests, us20_accept_blood_request, us21_reject_blood_request, us22_fulfill_blood_request,
    us23_low_stock_alert, us24_new_request_notification, us26_availability_notification,
    us27_manage_blood_banks, us28_manage_users, us29_assign_roles, us30_view_overall_inventory,
    us31_generate_reports, us32_search_and_filter_records, us33_view_system_activities,
):
    urlpatterns += story.URLS

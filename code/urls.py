from django.contrib import admin
from django.urls import path

from . import (
    common,
    us01_register_user,
    us02_login,
    us04_user_roles,
    us05_register_donor,
    us06_view_donor,
    us07_update_donor,
    us08_search_donor,
    us09_view_donation_history,
    us10_update_personal_information,
    us11_record_blood_donation,
    us12_view_donation_records,
    us13_update_donation_status,
    us14_view_blood_inventory,
    us15_update_blood_inventory,
    us17_search_blood_availability,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", common.home, name="home"),
]

for story in (
    us01_register_user,
    us02_login,
    us04_user_roles,
    us05_register_donor,
    us06_view_donor,
    us07_update_donor,
    us08_search_donor,
    us09_view_donation_history,
    us10_update_personal_information,
    us11_record_blood_donation,
    us12_view_donation_records,
    us13_update_donation_status,
    us14_view_blood_inventory,
    us15_update_blood_inventory,
    us17_search_blood_availability,
):
    urlpatterns += story.URLS
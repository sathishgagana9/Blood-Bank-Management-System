# Implementation Status

**Result: 34 of 34 user stories implemented** (Sprint 1: 15, Sprint 2: 19), connected through one shared data model, with 11 automated tests passing
(`python manage.py test`). Every page was also opened as Administrator, Staff, Donor and Requester with no server errors.

## Sprint 1

| Story | What it does | File (`code/core/`) | URL |
|---|---|---|---|
| US-01 Register User | Sign-up with validation (name characters, unique e-mail and phone, strong password) | `us01_register_user.py` | `/register/` |
| US-02 Login | Log in with username or e-mail; logout; 30-minute session | `us02_login.py` | `/login/` |
| US-03 Invalid Login Error | One clear error message; account locked for 15 min after 5 failed attempts | `us03_invalid_login_error.py` | (on login page) |
| US-04 User Roles | Donor / Staff / Administrator and the access check used by every page | `us04_user_roles.py` | `/roles/` |
| US-05 Register Donor | Staff create donors with auto ID DNR-0001; optional link to a user account | `us05_register_donor.py` | `/donors/register/` |
| US-06 View Donor | List and detail of donors | `us06_view_donor.py` | `/donors/` |
| US-07 Update Donor | Edit donor details | `us07_update_donor.py` | `/donors/<id>/update/` |
| US-08 Search Donor | Search by ID, name, group, contact | `us08_search_donor.py` | `/donors/search/` |
| US-09 View Donation History | Donor sees own history; staff see any donor's | `us09_view_donation_history.py` | `/my-donations/` |
| US-10 Update Personal Information | Edit own profile (kept in sync with donor record) | `us10_update_personal_information.py` | `/profile/` |
| US-11 Record Blood Donation | Record donation with auto ID DON-00001; Stored adds to inventory | `us11_record_blood_donation.py` | `/donations/record/` |
| US-12 View Donation Records | Filterable list of all donations | `us12_view_donation_records.py` | `/donations/` |
| US-13 Update Donation Status | Pending / Tested / Stored / Discarded; inventory follows | `us13_update_donation_status.py` | `/donations/<id>/status/` |
| US-14 View Blood Inventory | Stock by blood bank, group, component | `us14_view_blood_inventory.py` | `/inventory/` |
| US-34 Blood Component Tracking | Whole blood / plasma / platelets / RBC totals | `us34_blood_component_tracking.py` | `/inventory/components/` |

## Sprint 2

| Story | What it does | File (`code/core/`) | URL |
|---|---|---|---|
| US-15 Update Blood Inventory | Add / remove / set stock with a reason; never below zero | `us15_update_blood_inventory.py` | `/inventory/update/` |
| US-16 Automatic Inventory Update | Fulfilling a request deducts stock automatically | `us16_automatic_inventory_update.py` | (automatic) |
| US-17 Search Blood Availability | Search by group, component, location and units needed | `us17_search_blood_availability.py` | `/availability/` |
| US-18 Submit Blood Request | Request with group, units, urgency, contact, needed-by date; ID REQ-00001 | `us18_submit_blood_request.py` | `/requests/new/` |
| US-19 View Blood Requests | Staff see all; users see their own | `us19_view_blood_requests.py` | `/requests/` |
| US-20 Accept Blood Request | Only if the bank has enough stock | `us20_accept_blood_request.py` | `/requests/<id>/accept/` |
| US-21 Reject Blood Request | With a reason shown to the requester | `us21_reject_blood_request.py` | `/requests/<id>/reject/` |
| US-22 Fulfill Blood Request | Marks fulfilled and deducts stock (US-16) | `us22_fulfill_blood_request.py` | `/requests/<id>/fulfill/` |
| US-23 Low Stock Alert | Alert to staff when stock drops to 5 units or fewer; alert page | `us23_low_stock_alert.py` | `/alerts/low-stock/` |
| US-24 New Request Notification | Staff are notified of new requests; notification inbox | `us24_new_request_notification.py` | `/notifications/` |
| US-25 Request Status Notification | Requester is notified on accept / reject / fulfill | `us25_request_status_notification.py` | (automatic) |
| US-26 Availability Notification | Subscribe; notified when out-of-stock blood returns | `us26_availability_notification.py` | `/alerts/availability/` |
| US-27 Manage Blood Banks | Add, edit, activate / deactivate | `us27_manage_blood_banks.py` | `/manage/blood-banks/` |
| US-28 Manage Users | Create, edit, activate / deactivate users | `us28_manage_users.py` | `/manage/users/` |
| US-29 Assign Roles | Change roles; protects the last administrator | `us29_assign_roles.py` | `/manage/roles/` |
| US-30 View Overall Inventory | Totals across all banks, group x bank grid | `us30_view_overall_inventory.py` | `/inventory/overall/` |
| US-31 Generate Reports | Donors, donations, inventory, availability, requests; CSV download | `us31_generate_reports.py` | `/reports/` |
| US-32 Search and Filter Records | Donors / donations / requests by ID, group, status, location, dates | `us32_search_and_filter_records.py` | `/records/` |
| US-33 View System Activities | Audit log of logins, registrations, donations, requests, admin actions | `us33_view_system_activities.py` | `/manage/activity/` |

## Functional requirements coverage (SRS)

| FR | Requirement | Covered by |
|---|---|---|
| FR-01 | Register users | US-01 |
| FR-02 | Login, clear error on invalid credentials | US-02, US-03 |
| FR-03 | Staff register donors | US-05 |
| FR-04 | Add, update, search, view donors | US-05, 06, 07, 08 |
| FR-05 | Record donations | US-11, 12, 13 |
| FR-06 | Add, update, deactivate blood banks | US-27 |
| FR-07 | Manage inventory by group and bank | US-14, 15, 30, 34 |
| FR-08 | Automatic inventory update on donation and issue | US-11/13 (add), US-16/22 (issue) |
| FR-09 | Search availability by group, location, quantity | US-17 |
| FR-10 | Submit blood requests | US-18 |
| FR-11 | View and update request status | US-19, 20, 21, 22 |
| FR-12 | Low-stock alert | US-23 |
| FR-13 | Notifications (new request, status change, low stock, availability) | US-23, 24, 25, 26 |
| FR-14 | Reports | US-31 |
| FR-15 | Search and filter records | US-32 (and US-08, US-12, US-19) |
| FR-16 | Role-based permissions | US-04, US-29 (enforced on every page) |

## Known gaps (not implemented yet)

* E-mail verification link after registration and the "accept terms" checkbox (test case 1-010 / 1-001).
* Notifications are in-app only; no e-mail or SMS delivery.
* Non-functional items that need deployment work: scheduled backups (NFR-09), HTTPS, load/performance testing (NFR-01).
* Staff are not restricted to one blood bank; any staff member can manage every bank's stock.

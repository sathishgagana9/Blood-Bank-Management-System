"""Shared GUI layout used by every user story: page frame, navigation bar, form rendering, home page."""
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template import engines

PAGE_START = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Blood Bank Management System</title>
<style>
 body{font-family:system-ui,sans-serif;margin:0;background:#f6f6f8;color:#222}
 nav{background:#9b1c1c;padding:10px 20px;display:flex;flex-wrap:wrap;gap:14px;align-items:center}
 nav a,nav button{color:#fff;text-decoration:none;background:none;border:0;font:inherit;cursor:pointer}
 nav .spacer{flex:1}
 main{max-width:960px;margin:24px auto;padding:0 16px}
 .card{background:#fff;border-radius:8px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.12)}
 .narrow{max-width:560px;margin:auto}
 table{width:100%;border-collapse:collapse;margin-top:12px}
 th,td{text-align:left;padding:8px;border-bottom:1px solid #e3e3e8}
 th{background:#f0f0f4}
 label{display:block;margin-top:12px;font-weight:600}
 input,select,textarea{width:100%;padding:8px;box-sizing:border-box;margin-top:4px}
 .btn{display:inline-block;margin-top:16px;padding:8px 16px;background:#9b1c1c;color:#fff;border:0;border-radius:6px;text-decoration:none;cursor:pointer;width:auto}
 .btn.secondary{background:#555}
 .messages{list-style:none;padding:0}
 .messages li{padding:10px 14px;border-radius:6px;margin-bottom:8px;background:#e8f0fe}
 .messages .success{background:#e3f6e8}.messages .error{background:#fde8e8}
 .errorlist{color:#b00020;padding-left:18px;margin:4px 0}
 .helptext{color:#666;font-size:.85em}
 form.inline{display:inline}
 .filters{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;align-items:end}
</style></head><body>
<nav>
 <a href="{% url 'home' %}"><strong>Blood Bank</strong></a>
 {% if user.is_authenticated %}
  {% if user.is_blood_bank_staff %}
   <a href="{% url 'us06_view_donor' %}">Donors</a>
   <a href="{% url 'us12_view_donation_records' %}">Donations</a>
   <a href="{% url 'us19_view_blood_requests' %}">Requests</a>
   <a href="{% url 'us14_view_blood_inventory' %}">Inventory</a>
   <a href="{% url 'us15_update_blood_inventory' %}">Update Stock</a>
   <a href="{% url 'us30_view_overall_inventory' %}">Overall</a>
   <a href="{% url 'us23_low_stock_alert' %}">Low Stock</a>
   <a href="{% url 'us31_generate_reports' %}">Reports</a>
   <a href="{% url 'us32_search_and_filter_records' %}">Records</a>
  {% else %}
   <a href="{% url 'us09_view_my_donation_history' %}">My Donations</a>
   <a href="{% url 'us14_view_blood_inventory' %}">Inventory</a>
   <a href="{% url 'us17_search_blood_availability' %}">Find Blood</a>
   <a href="{% url 'us18_submit_blood_request' %}">Request Blood</a>
   <a href="{% url 'us19_view_blood_requests' %}">My Requests</a>
   <a href="{% url 'us26_availability_notification' %}">Availability Alerts</a>
  {% endif %}
  {% if user.is_administrator %}
   <a href="{% url 'us27_manage_blood_banks' %}">Blood Banks</a>
   <a href="{% url 'us28_manage_users' %}">Users</a>
   <a href="{% url 'us29_assign_roles' %}">Roles</a>
   <a href="{% url 'us33_view_system_activities' %}">Activity</a>
  {% endif %}
  <a href="{% url 'us24_view_notifications' %}">Notifications{% if unread_count %} ({{ unread_count }}){% endif %}</a>
  <span class="spacer"></span>
  <a href="{% url 'us10_update_personal_information' %}">{{ user.username }} ({{ user.get_role_display }})</a>
  <form class="inline" method="post" action="{% url 'us02_logout' %}">{% csrf_token %}<button type="submit">Logout</button></form>
 {% else %}
  <span class="spacer"></span>
  <a href="{% url 'us02_login' %}">Login</a>
  <a href="{% url 'us01_register_user' %}">Register</a>
 {% endif %}
</nav>
<main>
 {% if messages %}<ul class="messages">{% for message in messages %}<li class="{{ message.tags }}">{{ message }}</li>{% endfor %}</ul>{% endif %}
"""

PAGE_END = "</main></body></html>"

# Renders every field of `form` with its label, help text and errors.
FORM_FIELDS = """{{ form.non_field_errors }}
{% for field in form %}
 <label for="{{ field.id_for_label }}">{{ field.label }}</label>{{ field }}
 {% if field.help_text %}<div class="helptext">{{ field.help_text|safe }}</div>{% endif %}{{ field.errors }}
{% endfor %}"""


def render_page(request, body, context=None):
    """Wrap a story's GUI template (`body`) in the common page frame and render it."""
    context = dict(context or {})
    if request.user.is_authenticated:  # unread count shown next to "Notifications" (US-24)
        context["unread_count"] = request.user.notifications.filter(is_read=False).count()
    template = engines["django"].from_string(PAGE_START + body + PAGE_END)
    return HttpResponse(template.render(context, request))


HOME_TEMPLATE = """
<div class="card"><h2>Welcome, {{ user.get_full_name|default:user.username }}</h2>
<p>Signed in as <strong>{{ user.get_role_display }}</strong>.</p>
<ul>
{% if user.is_blood_bank_staff %}
 <li><a href="{% url 'us05_register_donor' %}">US-05 Register Donor</a></li>
 <li><a href="{% url 'us06_view_donor' %}">US-06 View Donors</a></li>
 <li><a href="{% url 'us08_search_donor' %}">US-08 Search Donor</a></li>
 <li><a href="{% url 'us11_record_blood_donation' %}">US-11 Record Blood Donation</a></li>
 <li><a href="{% url 'us12_view_donation_records' %}">US-12 View Donation Records</a></li>
 <li><a href="{% url 'us34_blood_component_tracking' %}">US-34 Blood Component Tracking</a></li>
 <li><a href="{% url 'us15_update_blood_inventory' %}">US-15 Update Blood Inventory</a></li>
 <li><a href="{% url 'us19_view_blood_requests' %}">US-19 View / Accept / Reject / Fulfill Blood Requests (US-20, 21, 22)</a></li>
 <li><a href="{% url 'us23_low_stock_alert' %}">US-23 Low Stock Alerts</a></li>
 <li><a href="{% url 'us30_view_overall_inventory' %}">US-30 View Overall Inventory</a></li>
 <li><a href="{% url 'us31_generate_reports' %}">US-31 Generate Reports</a></li>
 <li><a href="{% url 'us32_search_and_filter_records' %}">US-32 Search and Filter Records</a></li>
{% else %}
 <li><a href="{% url 'us18_submit_blood_request' %}">US-18 Submit Blood Request</a></li>
 <li><a href="{% url 'us19_view_blood_requests' %}">US-19 View My Blood Requests</a></li>
 <li><a href="{% url 'us26_availability_notification' %}">US-26 Availability Notifications</a></li>
 <li><a href="{% url 'us09_view_my_donation_history' %}">US-09 View My Donation History</a></li>
{% endif %}
 <li><a href="{% url 'us14_view_blood_inventory' %}">US-14 View Blood Inventory</a></li>
 <li><a href="{% url 'us17_search_blood_availability' %}">US-17 Search Blood Availability</a></li>
 <li><a href="{% url 'us24_view_notifications' %}">US-24 Notifications (US-25 status updates)</a></li>
 <li><a href="{% url 'us10_update_personal_information' %}">US-10 Update Personal Information</a></li>
{% if user.is_administrator %}
 <li><a href="{% url 'us04_user_roles' %}">US-04 Manage User Roles</a></li>
 <li><a href="{% url 'us27_manage_blood_banks' %}">US-27 Manage Blood Banks</a></li>
 <li><a href="{% url 'us28_manage_users' %}">US-28 Manage Users</a></li>
 <li><a href="{% url 'us29_assign_roles' %}">US-29 Assign Roles</a></li>
 <li><a href="{% url 'us33_view_system_activities' %}">US-33 View System Activities</a></li>
{% endif %}
</ul></div>"""



DONOR_HOME_TEMPLATE = """
<style>
body:has(.donor-dashboard){background:#f5f6fa;color:#17202b}
body:has(.donor-dashboard)>nav{display:none}
body:has(.donor-dashboard)>main{max-width:none;width:100%;margin:0;padding:0}
.donor-dashboard{min-height:100vh;background:#f7f8fb}
.donor-topbar{height:78px;background:linear-gradient(105deg,#bd1025,#790014);color:#fff;display:flex;align-items:center;justify-content:space-between;padding:0 28px;box-shadow:0 3px 14px #50000d25}
.donor-brand{display:flex;align-items:center;gap:14px;color:#fff;text-decoration:none;font-size:20px;font-weight:800;line-height:1.12;letter-spacing:-.3px}
.donor-brand svg{width:39px;height:45px;flex:none}
.donor-account{display:flex;align-items:center;gap:12px;color:#fff}
.donor-account .account-copy{font-size:13px;line-height:1.4;text-align:right}
.donor-account .account-copy strong{display:block;font-size:15px}
.donor-avatar{width:42px;height:42px;background:#fff;border-radius:50%;display:grid;place-items:center;color:#7b1230}
.donor-avatar svg{width:25px;height:25px}
.donor-logout{background:#ffffff18;border:1px solid #ffffff55;border-radius:9px;color:#fff;padding:9px 13px;font-weight:700;cursor:pointer}
.donor-logout:hover{background:#ffffff30}
.donor-shell{display:grid;grid-template-columns:310px minmax(0,1fr);min-height:calc(100vh - 78px)}
.donor-sidebar{background:#fff;border-right:1px solid #e8eaf0;padding:24px 14px;display:flex;flex-direction:column;gap:7px}
.donor-side-heading{padding:12px 13px 5px;color:#9399a5;font-size:11px;font-weight:800;letter-spacing:1.1px;text-transform:uppercase}
.donor-side-link{display:flex;align-items:center;gap:13px;padding:12px 13px;border-radius:11px;color:#202938;text-decoration:none;font-size:15px;font-weight:650;transition:background .18s,color .18s}
.donor-side-link:hover{background:#fff0f2;color:#a50d22}
.donor-side-link.active{background:linear-gradient(100deg,#c9162c,#a70c20);color:#fff;box-shadow:0 5px 12px #a70c2024}
.donor-side-icon{width:30px;height:30px;border-radius:9px;display:grid;place-items:center;background:#f4f5f8;color:#a90f25;flex:none}
.donor-side-link.active .donor-side-icon{background:#ffffff22;color:#fff}
.donor-side-icon svg{width:19px;height:19px;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.donor-content{min-width:0;padding:28px clamp(18px,2.2vw,36px) 42px}
.donor-welcome{position:relative;overflow:hidden;display:flex;align-items:center;justify-content:space-between;min-height:228px;padding:30px 36px;border:1px solid #f6d7dd;border-radius:18px;background:linear-gradient(105deg,#ffe5e9 0%,#fff1f3 58%,#fce5e9 100%);margin-bottom:24px}
.donor-welcome-copy{position:relative;z-index:1;max-width:610px}
.donor-welcome h1{font-size:clamp(27px,2.4vw,36px);line-height:1.15;margin:0 0 10px;color:#141923;letter-spacing:-.8px}
.donor-role{font-size:18px;color:#71404b;margin-bottom:12px}
.donor-role span{display:inline-block;padding:4px 12px;border-radius:999px;background:#f8c7d0;color:#9b1023;font-size:15px;font-weight:800}
.donor-welcome p{font-size:17px;line-height:1.55;color:#684451;margin:0;max-width:580px}
.donor-hero-art{width:min(38%,430px);min-width:220px;max-height:205px;opacity:.96}
.donor-section-title{display:flex;align-items:center;justify-content:space-between;margin:22px 0 13px}
.donor-section-title h2{font-size:25px;letter-spacing:-.5px;margin:0;color:#141923}
.donor-quick-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}
.donor-action{min-height:153px;padding:18px 20px 16px;border-radius:16px;text-decoration:none;color:#141923;display:flex;flex-direction:column;justify-content:space-between;border:1px solid transparent;transition:transform .18s,box-shadow .18s}
.donor-action:hover{transform:translateY(-3px);box-shadow:0 9px 22px #22222212;color:#141923}
.donor-action.red{background:linear-gradient(135deg,#ffe6eb,#ffeef1);border-color:#f8dce2}
.donor-action.blue{background:linear-gradient(135deg,#e4f0ff,#edf5ff);border-color:#d7e8ff}
.donor-action.green{background:linear-gradient(135deg,#e5f7ed,#effbf3);border-color:#d9f1e2}
.donor-action.purple{background:linear-gradient(135deg,#f1e9ff,#f7f1ff);border-color:#e9ddff}
.donor-action-icon{width:45px;height:45px;color:#a90d24}
.donor-action.blue .donor-action-icon{color:#1267bd}
.donor-action.green .donor-action-icon{color:#148447}
.donor-action.purple .donor-action-icon{color:#7734bd}
.donor-action-icon svg{width:100%;height:100%;stroke:currentColor;fill:none;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}
.donor-action-bottom{display:flex;align-items:center;justify-content:space-between;gap:8px}
.donor-action h3{font-size:17px;line-height:1.3;margin:0;max-width:190px;color:#121722}
.donor-arrow{height:36px;width:36px;border-radius:50%;background:#ffffffd9;display:grid;place-items:center;color:#ae1026;font-size:22px;flex:none}
.donor-action.blue .donor-arrow{color:#1267bd}.donor-action.green .donor-arrow{color:#148447}.donor-action.purple .donor-arrow{color:#7734bd}
.donor-mid-grid{display:grid;grid-template-columns:1.15fr 1fr;gap:18px;margin-top:20px}
.donor-panel{background:#fff;border:1px solid #e7e9ef;border-radius:17px;padding:19px 21px;box-shadow:0 3px 12px #1a26330a;min-width:0}
.donor-panel-heading{display:flex;align-items:center;gap:11px;margin-bottom:17px}
.donor-panel-heading svg{width:28px;height:28px;stroke:#a80d23;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;flex:none}
.donor-panel-heading h2{font-size:20px;margin:0;color:#151b26;letter-spacing:-.3px}
.donor-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr))}
.donor-stat{text-align:center;padding:2px 10px 3px;border-right:1px solid #d9dde6}
.donor-stat:last-child{border-right:0}
.donor-stat strong{display:block;font-size:37px;line-height:1.1;color:#b31025;margin-bottom:6px}
.donor-stat:nth-child(2) strong{color:#1476cf}.donor-stat:nth-child(3) strong{color:#198447}
.donor-stat span{font-size:14px;color:#283141;font-weight:600}
.donor-blood-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px 10px}
.donor-blood-item{display:flex;align-items:center;gap:9px;min-width:0}
.donor-blood-type{background:#ffe1e5;color:#a41024;border-radius:999px;padding:8px 11px;font-size:15px;font-weight:800;min-width:59px;text-align:center}
.donor-blood-qty{font-size:16px;font-weight:750;color:#141923}
.donor-lower-grid{display:grid;grid-template-columns:1.35fr 1fr;gap:18px;margin-top:20px}
.donor-notification-list{display:flex;flex-direction:column}
.donor-notification{display:flex;align-items:flex-start;gap:12px;padding:11px 0;border-top:1px solid #e6e8ee}
.donor-notification:first-child{border-top:0;padding-top:0}
.donor-notification-mark{width:37px;height:37px;border-radius:50%;display:grid;place-items:center;background:#e4f7ea;color:#13753d;flex:none}
.donor-notification-mark.info{background:#e4f1ff;color:#0873c8}
.donor-notification-mark svg{width:20px;height:20px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.donor-notification-text{font-size:14px;color:#1d2634;line-height:1.4}
.donor-notification-text small{display:block;color:#778092;margin-top:3px;font-size:12px}
.donor-view-all{margin-left:auto;color:#a70e23;text-decoration:none;font-size:14px;font-weight:750}
.donor-callout{position:relative;overflow:hidden;display:flex;align-items:center;justify-content:space-between;min-height:180px;padding:22px 25px;border-radius:17px;background:linear-gradient(110deg,#ffe5e9,#fff1f3);border:1px solid #f8dce2}
.donor-callout h2{font-size:27px;line-height:1.1;margin:0 0 15px;color:#a10d20;letter-spacing:-.5px}
.donor-callout h2 span{color:#151b26}
.donor-callout a{display:inline-flex;align-items:center;gap:12px;padding:10px 19px;border-radius:999px;background:#b70f25;color:#fff;text-decoration:none;font-size:14px;font-weight:750}
.donor-callout-art{width:42%;max-width:160px}
.donor-empty{padding:14px 0;color:#778092;font-size:14px}
@media(max-width:1180px){.donor-shell{grid-template-columns:260px minmax(0,1fr)}.donor-quick-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.donor-mid-grid,.donor-lower-grid{grid-template-columns:1fr}.donor-welcome{min-height:210px}}
@media(max-width:760px){.donor-topbar{height:auto;min-height:70px;padding:12px 16px}.donor-brand{font-size:16px}.donor-account .account-copy{display:none}.donor-shell{grid-template-columns:1fr}.donor-sidebar{border-right:0;border-bottom:1px solid #e8eaf0;display:flex;flex-direction:row;overflow-x:auto;padding:10px;gap:6px}.donor-side-heading{display:none}.donor-side-link{white-space:nowrap;padding:8px 10px;font-size:13px}.donor-side-icon{width:26px;height:26px}.donor-content{padding:17px 14px 30px}.donor-welcome{padding:22px;min-height:190px}.donor-welcome p{font-size:14px}.donor-role{font-size:15px}.donor-hero-art{min-width:120px;width:28%}.donor-section-title h2{font-size:21px}}
@media(max-width:480px){.donor-brand svg{width:31px;height:36px}.donor-brand{font-size:14px}.donor-avatar{width:34px;height:34px}.donor-logout{padding:7px 9px;font-size:12px}.donor-welcome{display:block;padding:20px}.donor-hero-art{display:none}.donor-welcome h1{font-size:26px}.donor-quick-grid{gap:10px}.donor-action{padding:14px;min-height:145px}.donor-action h3{font-size:14px}.donor-action-icon{width:36px;height:36px}.donor-arrow{width:30px;height:30px}.donor-panel{padding:16px 13px}.donor-panel-heading h2{font-size:17px}.donor-stat{padding:2px 5px}.donor-stat strong{font-size:29px}.donor-stat span{font-size:11px}.donor-blood-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:11px}.donor-blood-type{min-width:55px;padding:7px 8px}.donor-callout{padding:18px}.donor-callout h2{font-size:22px}}
</style>
<div class="donor-dashboard">
<header class="donor-topbar">
 <a class="donor-brand" href="{% url 'home' %}">
  <svg viewBox="0 0 48 56" aria-hidden="true"><path fill="white" d="M24 2C18 13 5 26 5 37a19 19 0 0 0 38 0C43 26 30 13 24 2z"/><path fill="#a90d24" d="M15 37c0 6 4 10 10 11-2 3-5 4-8 3-5-2-8-7-8-13 0-3 2-8 6-14-1 6 0 9 0 13z"/></svg>
  <span>Blood Bank<br>Management System</span>
 </a>
 <div class="donor-account">
  <div class="donor-avatar"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4" fill="#7b1230" opacity=".18"/><path d="M4 21c.8-4.2 3.5-6.2 8-6.2s7.2 2 8 6.2" fill="#7b1230" opacity=".18"/><circle cx="12" cy="8" r="4" fill="none" stroke="#7b1230" stroke-width="1.5"/><path d="M4 21c.8-4.2 3.5-6.2 8-6.2s7.2 2 8 6.2" fill="none" stroke="#7b1230" stroke-width="1.5"/></svg></div>
  <div class="account-copy"><strong>{{ user.get_full_name|default:user.username }}</strong>{{ user.get_role_display }}</div>
  <form method="post" action="{% url 'us02_logout' %}">{% csrf_token %}<button class="donor-logout" type="submit">Logout</button></form>
 </div>
</header>
<div class="donor-shell">
<aside class="donor-sidebar">
 <div class="donor-side-heading">Menu</div>
 <a class="donor-side-link active" href="{% url 'home' %}"><span class="donor-side-icon"><svg viewBox="0 0 24 24"><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/></svg></span>Dashboard</a>
 <a class="donor-side-link" href="{% url 'us18_submit_blood_request' %}"><span class="donor-side-icon"><svg viewBox="0 0 24 24"><path d="M12 2S5 10 5 15a7 7 0 0 0 14 0c0-5-7-13-7-13z"/><path d="M12 11v8m-4-4h8"/></svg></span>Submit Blood Request</a>
 <a class="donor-side-link" href="{% url 'us19_view_blood_requests' %}"><span class="donor-side-icon"><svg viewBox="0 0 24 24"><rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h4"/></svg></span>My Blood Requests</a>
 <a class="donor-side-link" href="{% url 'us26_availability_notification' %}"><span class="donor-side-icon"><svg viewBox="0 0 24 24"><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></svg></span>Availability Notifications</a>
 <a class="donor-side-link" href="{% url 'us09_view_my_donation_history' %}"><span class="donor-side-icon"><svg viewBox="0 0 24 24"><path d="M20.8 8.8c0 5.2-8.8 11-8.8 11S3.2 14 3.2 8.8A4.7 4.7 0 0 1 12 6.4a4.7 4.7 0 0 1 8.8 2.4z"/></svg></span>My Donation History</a>
 <a class="donor-side-link" href="{% url 'us14_view_blood_inventory' %}"><span class="donor-side-icon"><svg viewBox="0 0 24 24"><path d="m12 2 8 4.5v9L12 20l-8-4.5v-9zM12 2v9m8-4.5-8 4.5-8-4.5m8 4.5V20"/></svg></span>Blood Inventory</a>
 <a class="donor-side-link" href="{% url 'us17_search_blood_availability' %}"><span class="donor-side-icon"><svg viewBox="0 0 24 24"><circle cx="10.8" cy="10.8" r="7.2"/><path d="m16 16 5 5"/></svg></span>Search Blood Availability</a>
 <a class="donor-side-link" href="{% url 'us24_view_notifications' %}"><span class="donor-side-icon"><svg viewBox="0 0 24 24"><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></svg></span>Notifications{% if unread_count %} ({{ unread_count }}){% endif %}</a>
 <div class="donor-side-heading">Account</div>
 <a class="donor-side-link" href="{% url 'us10_update_personal_information' %}"><span class="donor-side-icon"><svg viewBox="0 0 24 24"><circle cx="9" cy="7" r="4"/><path d="M2 21c.8-4.5 3-6.5 7-6.5 2 0 3.6.5 4.8 1.6M15 19l6-6 2 2-6 6-3 1z"/></svg></span>Update Personal Info</a>
</aside>
<section class="donor-content">
<section class="donor-welcome">
 <div class="donor-welcome-copy">
  <h1>Welcome, {{ user.get_full_name|default:user.username }}</h1>
  <div class="donor-role">Signed in as <span>Donor</span></div>
  <p>Thank you for being a part of our life-saving community. You can submit blood requests, track your donations, and stay updated on blood availability here.</p>
 </div>
 <svg class="donor-hero-art" viewBox="0 0 430 210" role="img" aria-label="Blood donation illustration">
  <path d="M8 95h53l13-23 19 55 17-96 23 112 20-54 13 6h28M265 95h42l16-18 16 44 20-94 20 108 17-40 26 0" stroke="#e98d9b" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M215 18c-25 36-49 64-49 91a49 49 0 0 0 98 0c0-27-24-55-49-91z" fill="#c91d32"/>
  <path d="M215 38c-18 27-33 46-33 67a33 33 0 0 0 66 0c0-21-15-40-33-67z" fill="#ed3448"/>
  <path d="M215 82v43m-21-21h42" stroke="#fff" stroke-width="11" stroke-linecap="round"/>
  <path d="M158 207c-19-24-42-42-44-68-1-12 6-18 15-12l28 24-11-33c-3-10 8-16 16-8l30 37M272 207c19-24 42-42 44-68 1-12-6-18-15-12l-28 24 11-33c3-10-8-16-16-8l-30 37" fill="#f3a06e" stroke="#ee9869" stroke-width="3" stroke-linejoin="round"/>
  <path d="M185 157q30 21 60 0" stroke="#fff" stroke-width="5" fill="none" stroke-linecap="round" opacity=".85"/>
 </svg>
</section>
<div class="donor-section-title"><h2>Quick Actions</h2></div>
<section class="donor-quick-grid">
 <a class="donor-action red" href="{% url 'us18_submit_blood_request' %}"><div class="donor-action-icon"><svg viewBox="0 0 48 48"><path d="M24 4S8 22 8 31a16 16 0 0 0 32 0C40 22 24 4 24 4z"/><path d="M24 22v16m-8-8h16"/></svg></div><div class="donor-action-bottom"><h3>Submit<br>Blood Request</h3><span class="donor-arrow">→</span></div></a>
 <a class="donor-action blue" href="{% url 'us19_view_blood_requests' %}"><div class="donor-action-icon"><svg viewBox="0 0 48 48"><rect x="9" y="7" width="30" height="36" rx="4"/><path d="M18 5h12v7H18zM17 21h14M17 29h14M17 37h8"/></svg></div><div class="donor-action-bottom"><h3>View My<br>Blood Requests</h3><span class="donor-arrow">→</span></div></a>
 <a class="donor-action green" href="{% url 'us09_view_my_donation_history' %}"><div class="donor-action-icon"><svg viewBox="0 0 48 48"><path d="M10 13h28v29H10zM17 13V8h14v5M24 20s-7 7-7 11a7 7 0 0 0 14 0c0-4-7-11-7-11z"/></svg></div><div class="donor-action-bottom"><h3>View My<br>Donation History</h3><span class="donor-arrow">→</span></div></a>
 <a class="donor-action purple" href="{% url 'us10_update_personal_information' %}"><div class="donor-action-icon"><svg viewBox="0 0 48 48"><circle cx="19" cy="13" r="9"/><path d="M4 42c1-10 6-15 15-15 4 0 7 1 10 4M31 23l11-11 5 5-11 11-8 3z"/></svg></div><div class="donor-action-bottom"><h3>Update<br>Personal Information</h3><span class="donor-arrow">→</span></div></a>
</section>
<section class="donor-mid-grid">
 <div class="donor-panel">
  <div class="donor-panel-heading"><svg viewBox="0 0 28 28"><path d="M24 9c0 7-10 15-10 15S4 16 4 9a5.5 5.5 0 0 1 10-3 5.5 5.5 0 0 1 10 3z"/></svg><h2>Your Donation Summary</h2></div>
  <div class="donor-stats">
   <div class="donor-stat"><strong>{{ donation_total }}</strong><span>Total Donations</span></div>
   <div class="donor-stat"><strong>{{ pending_request_total }}</strong><span>Pending Requests</span></div>
   <div class="donor-stat"><strong>{{ completed_request_total }}</strong><span>Completed Requests</span></div>
  </div>
 </div>
 <div class="donor-panel">
  <div class="donor-panel-heading"><svg viewBox="0 0 28 28"><path d="m14 2 7 4v8l-7 4-7-4V6zM14 2v8m7-4-7 4-7-4m7 4v8m7-8 5 3v7l-5 3-5-3m5-7v7m5-4-5 4-5-4M2 17l5-3 5 3v7l-5 3-5-3z"/></svg><h2>Current Blood Availability</h2></div>
  <div class="donor-blood-grid">
   {% for item in inventory_by_group %}
    <div class="donor-blood-item"><span class="donor-blood-type">{{ item.blood_group }}</span><span class="donor-blood-qty">{{ item.quantity }}</span></div>
   {% endfor %}
  </div>
 </div>
</section>
<section class="donor-lower-grid">
 <div class="donor-panel">
  <div class="donor-panel-heading"><svg viewBox="0 0 28 28"><path d="M22 10a8 8 0 0 0-16 0c0 8-3 8-3 10h22c0-2-3-2-3-10M11 24h6"/></svg><h2>Recent Notifications</h2><a class="donor-view-all" href="{% url 'us24_view_notifications' %}">View All →</a></div>
  <div class="donor-notification-list">
   {% for item in recent_notifications %}
    <div class="donor-notification"><span class="donor-notification-mark {% if item.category == 'AVAILABILITY' %}info{% endif %}"><svg viewBox="0 0 24 24"><path d="M5 12l5 5L20 7"/></svg></span><div class="donor-notification-text">{{ item.message }}<small>{{ item.created_at|timesince }} ago</small></div></div>
   {% empty %}
    <div class="donor-empty">You do not have any notifications yet.</div>
   {% endfor %}
  </div>
 </div>
 <div class="donor-callout">
  <div><h2>Donate Blood,<br><span>Save Lives!</span></h2><a href="{% url 'us09_view_my_donation_history' %}">View Donation History <span>→</span></a></div>
  <svg class="donor-callout-art" viewBox="0 0 150 140" aria-hidden="true"><path d="M76 5C64 23 53 37 53 52a23 23 0 0 0 46 0C99 37 88 23 76 5z" fill="#cf172e"/><path d="M75 25v40m-20-20h40" stroke="#fff" stroke-width="6" stroke-linecap="round"/><path d="M30 113c17-20 40-28 60-23l35 9c10 3 14 13 5 18l-42 17c-17 7-38-2-58-7l-17-4c-10-2-13-5-8-10 6-5 15-4 25 0z" fill="#f0a078"/><path d="M76 2V0M111 15l7-7M40 15l-7-7" stroke="#c8172d" stroke-width="3" stroke-linecap="round"/></svg>
 </div>
</section>
</section>
</div>
</div>
"""


@login_required
def home(request):
    # The donor dashboard has its own presentation. Existing staff/admin pages and
    # all user-story views continue to use the original shared page frame.
    if request.user.role == request.user.ROLE_DONOR:
        from django.db.models import Sum
        from .models import BloodInventory, BloodRequest, Donation

        donor_donations = Donation.objects.filter(donor__user=request.user)
        requests = BloodRequest.objects.filter(requester=request.user)
        inventory_totals = {
            row["blood_group"]: row["quantity"]
            for row in BloodInventory.objects.values("blood_group").annotate(
                quantity=Sum("quantity")
            )
        }
        blood_groups = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")
        context = {
            "donation_total": donor_donations.count(),
            "pending_request_total": requests.filter(
                status=BloodRequest.STATUS_PENDING
            ).count(),
            "completed_request_total": requests.filter(
                status=BloodRequest.STATUS_FULFILLED
            ).count(),
            "inventory_by_group": [
                {"blood_group": group, "quantity": inventory_totals.get(group, 0)}
                for group in blood_groups
            ],
            "recent_notifications": request.user.notifications.all()[:2],
        }
        return render_page(request, DONOR_HOME_TEMPLATE, context)

    return render_page(request, HOME_TEMPLATE)

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


@login_required
def home(request):
    return render_page(request, HOME_TEMPLATE)

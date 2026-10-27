"""US-18 Submit Blood Request.

Tasks: blood request form (validation) -> view (generate unique request ID, save) -> GUI pages -> URLs.
"""
import uuid

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import path

from .common import FORM_FIELDS, render_page
from .models import BLOOD_GROUPS, BloodRequest


# ---- Form
class US18BloodRequestForm(forms.ModelForm):
    class Meta:
        model = BloodRequest
        fields = ("blood_group", "quantity", "location", "urgency", "contact")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("blood_group", "quantity", "location", "urgency", "contact"):
            self.fields[name].required = True
        self.fields["quantity"].help_text = "Quantity required (in ml or units, must be > 0)"
        self.fields["location"].widget.attrs["placeholder"] = "Hospital, Clinic, or City Location"
        self.fields["contact"].widget.attrs["placeholder"] = "Phone number for coordination"

    def clean_quantity(self):
        qty = self.cleaned_data.get("quantity")
        if qty is None or qty <= 0:
            raise forms.ValidationError("Quantity must be greater than 0.")
        return qty

    def clean_location(self):
        location = self.cleaned_data.get("location", "").strip()
        if not location:
            raise forms.ValidationError("Location is required.")
        return location

    def clean_contact(self):
        contact = self.cleaned_data.get("contact", "").strip()
        if not contact:
            raise forms.ValidationError("Contact information is required.")
        return contact


# ---- GUI
TEMPLATE_FORM = (
    """<div class="card narrow"><h2>US-18 Submit Blood Request</h2>
<p>Submit a request for required blood units. Please fill all fields accurately.</p>
<form method="post" novalidate>{% csrf_token %}"""
    + FORM_FIELDS
    + """<button class="btn" type="submit">Submit Request</button></form>
<p style="margin-top: 1rem;"><a href="{% url 'us18_my_requests' %}">View My Requests</a></p></div>"""
)

TEMPLATE_MY_REQUESTS = """<div class="card"><h2>My Blood Requests</h2>
<p>List of blood requests you have submitted and their current statuses.</p>
<table>
 <tr>
  <th>Request ID</th>
  <th>Blood Group</th>
  <th>Quantity</th>
  <th>Location</th>
  <th>Urgency</th>
  <th>Status</th>
  <th>Submitted Date</th>
 </tr>
 {% for req in requests %}
 <tr>
  <td><strong>{{ req.request_id }}</strong></td>
  <td><span class="badge">{{ req.blood_group }}</span></td>
  <td>{{ req.quantity }} ml</td>
  <td>{{ req.location }}</td>
  <td><span class="badge">{{ req.urgency }}</span></td>
  <td>{{ req.status }}</td>
  <td>{{ req.created_at|date:"Y-m-d H:i" }}</td>
 </tr>
 {% empty %}
 <tr><td colspan="7">No blood requests submitted yet.</td></tr>
 {% endfor %}
</table>
<p style="margin-top: 1.5rem;"><a class="btn" href="{% url 'us18_submit_blood_request' %}">Submit New Request</a></p>
</div>"""


# ---- Views
@login_required
def us18_submit_blood_request(request):
    form = US18BloodRequestForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            req = form.save(commit=False)
            req.user = request.user
            req.request_id = f"BR-{uuid.uuid4().hex[:6].upper()}"
            req.status = "Pending"
            req.save()
            messages.success(
                request,
                f"Blood request {req.request_id} submitted successfully with status Pending.",
            )
            return redirect("us18_my_requests")
        else:
            messages.error(request, "Please correct the errors below.")
    return render_page(request, TEMPLATE_FORM, {"form": form})


@login_required
def us18_my_requests(request):
    user_requests = BloodRequest.objects.filter(user=request.user).order_by("-created_at")
    return render_page(request, TEMPLATE_MY_REQUESTS, {"requests": user_requests})


URLS = [
    path("requests/submit/", us18_submit_blood_request, name="us18_submit_blood_request"),
    path("requests/my/", us18_my_requests, name="us18_my_requests"),
]

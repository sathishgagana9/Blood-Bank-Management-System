"""US-18 Submit Blood Request.

Tasks: request form (patient, bank, group, component, units, needed-by date; validated) -> view (save with
auto ID REQ-00001..., notify staff via US-24, log) -> GUI page -> URL.
"""
from django import forms
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import path
from django.utils import timezone

from .common import FORM_FIELDS, render_page
from .models import ActivityLog, BloodBank, BloodInventory, BloodRequest
from .us04_user_roles import ALL_ROLES, us04_role_required
from .us24_new_request_notification import us24_notify_new_request


# ---- Form
class US18SubmitRequestForm(forms.ModelForm):
    blood_bank = forms.ModelChoiceField(queryset=BloodBank.objects.filter(is_active=True))

    class Meta:
        model = BloodRequest
        fields = ("patient_name", "blood_bank", "blood_group", "component", "quantity", "urgency", "contact", "required_by", "notes")
        widgets = {
            "required_by": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_required_by(self):
        date = self.cleaned_data["required_by"]
        if date < timezone.localdate():
            raise forms.ValidationError("The required-by date cannot be in the past.")
        return date


# ---- GUI
TEMPLATE = (
    """<div class="card narrow"><h2>US-18 Submit Blood Request</h2>
<form method="post" novalidate>{% csrf_token %}"""
    + FORM_FIELDS
    + """<button class="btn" type="submit">Submit request</button>
<a class="btn secondary" href="{% url 'us17_search_blood_availability' %}">Check availability first</a></form></div>"""
)


# ---- View
@us04_role_required(*ALL_ROLES)
def us18_submit_blood_request(request):
    initial = {k: request.GET[k] for k in ("blood_bank", "blood_group", "component") if request.GET.get(k)}
    initial.setdefault("contact", request.user.phone)
    form = US18SubmitRequestForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        blood_request = form.save(commit=False)
        blood_request.requester = request.user
        blood_request.save()
        ActivityLog.record(request.user, "REQUEST_SUBMITTED", f"{blood_request.request_id}: {blood_request.quantity} x {blood_request.blood_group}")
        us24_notify_new_request(blood_request)
        stock = BloodInventory.objects.filter(
            blood_bank=blood_request.blood_bank, blood_group=blood_request.blood_group, component=blood_request.component
        ).first()
        messages.success(request, f"Blood request {blood_request.request_id} submitted. You will be notified of its status.")
        if not stock or stock.quantity < blood_request.quantity:
            messages.warning(request, "Note: this blood bank currently has less stock than you requested; staff will review it.")
        return redirect("us19_view_blood_requests")
    return render_page(request, TEMPLATE, {"form": form})


URLS = [path("requests/new/", us18_submit_blood_request, name="us18_submit_blood_request")]

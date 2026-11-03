"""US-27 Manage Blood Banks.

Tasks: blood-bank form -> views (list, add, edit, activate / deactivate; banks are never deleted because
donations and requests refer to them) -> GUI pages -> URLs. Administrator only.
"""
from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import path

from .common import FORM_FIELDS, render_page
from .models import ActivityLog, BloodBank
from .us04_user_roles import ADMIN_ROLES, us04_role_required


# ---- Form
class US27BloodBankForm(forms.ModelForm):
    class Meta:
        model = BloodBank
        fields = ("name", "location", "address", "contact", "is_active")
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}


# ---- GUI
LIST_TEMPLATE = """<div class="card"><h2>US-27 Manage Blood Banks</h2>
<a class="btn" href="{% url 'us27_add_blood_bank' %}">Add blood bank</a>
<table><tr><th>Name</th><th>Location</th><th>Contact</th><th>Status</th><th></th></tr>
{% for b in banks %}
<tr><td>{{ b.name }}</td><td>{{ b.location }}</td><td>{{ b.contact }}</td><td>{% if b.is_active %}Active{% else %}Inactive{% endif %}</td>
<td><a href="{% url 'us27_edit_blood_bank' b.pk %}">Edit</a>
<form class="inline" method="post" action="{% url 'us27_toggle_blood_bank' b.pk %}">{% csrf_token %}<button type="submit" style="cursor:pointer">{% if b.is_active %}Deactivate{% else %}Activate{% endif %}</button></form></td></tr>
{% empty %}<tr><td colspan="5">No blood banks yet.</td></tr>{% endfor %}
</table></div>"""

FORM_TEMPLATE = (
    """<div class="card narrow"><h2>US-27 {{ title }}</h2>
<form method="post" novalidate>{% csrf_token %}"""
    + FORM_FIELDS
    + """<button class="btn" type="submit">Save</button>
<a class="btn secondary" href="{% url 'us27_manage_blood_banks' %}">Cancel</a></form></div>"""
)


# ---- Views
@us04_role_required(*ADMIN_ROLES)
def us27_manage_blood_banks(request):
    return render_page(request, LIST_TEMPLATE, {"banks": BloodBank.objects.all()})


@us04_role_required(*ADMIN_ROLES)
def us27_add_blood_bank(request):
    form = US27BloodBankForm(request.POST or None, initial={"is_active": True})
    if request.method == "POST" and form.is_valid():
        bank = form.save()
        ActivityLog.record(request.user, "BLOOD_BANK_ADDED", bank.name)
        messages.success(request, f"Blood bank '{bank.name}' added.")
        return redirect("us27_manage_blood_banks")
    return render_page(request, FORM_TEMPLATE, {"form": form, "title": "Add Blood Bank"})


@us04_role_required(*ADMIN_ROLES)
def us27_edit_blood_bank(request, bank_pk):
    bank = get_object_or_404(BloodBank, pk=bank_pk)
    form = US27BloodBankForm(request.POST or None, instance=bank)
    if request.method == "POST" and form.is_valid():
        form.save()
        ActivityLog.record(request.user, "BLOOD_BANK_UPDATED", bank.name)
        messages.success(request, f"Blood bank '{bank.name}' updated.")
        return redirect("us27_manage_blood_banks")
    return render_page(request, FORM_TEMPLATE, {"form": form, "title": f"Edit {bank.name}"})


@us04_role_required(*ADMIN_ROLES)
def us27_toggle_blood_bank(request, bank_pk):
    bank = get_object_or_404(BloodBank, pk=bank_pk)
    if request.method == "POST":
        bank.is_active = not bank.is_active
        bank.save()
        ActivityLog.record(request.user, "BLOOD_BANK_ACTIVATED" if bank.is_active else "BLOOD_BANK_DEACTIVATED", bank.name)
        messages.success(request, f"'{bank.name}' is now {'active' if bank.is_active else 'inactive'}.")
    return redirect("us27_manage_blood_banks")


URLS = [
    path("manage/blood-banks/", us27_manage_blood_banks, name="us27_manage_blood_banks"),
    path("manage/blood-banks/add/", us27_add_blood_bank, name="us27_add_blood_bank"),
    path("manage/blood-banks/<int:bank_pk>/edit/", us27_edit_blood_bank, name="us27_edit_blood_bank"),
    path("manage/blood-banks/<int:bank_pk>/toggle/", us27_toggle_blood_bank, name="us27_toggle_blood_bank"),
]

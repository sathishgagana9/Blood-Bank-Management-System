"""US-10 Update Personal Information.

Tasks: profile form -> view (save, keep linked donor record consistent) -> GUI page -> URL.
"""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect
from django.urls import path

from .common import FORM_FIELDS, render_page
from .models import Donor, User


# ---- Form
class US10PersonalInformationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone", "address")
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True


# ---- GUI
TEMPLATE = (
    """<div class="card narrow"><h2>US-10 Update Personal Information</h2>
<form method="post" novalidate>{% csrf_token %}"""
    + FORM_FIELDS
    + """<button class="btn" type="submit">Save changes</button></form></div>"""
)


# ---- View
@login_required
def us10_update_personal_information(request):
    form = US10PersonalInformationForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
            donor = Donor.objects.filter(user=user).first()
            if donor:
                donor.name = user.get_full_name() or donor.name
                donor.contact = user.phone or donor.contact
                donor.address = user.address or donor.address
                donor.save()
        messages.success(request, "Your personal information has been updated.")
        return redirect("us10_update_personal_information")
    return render_page(request, TEMPLATE, {"form": form})


URLS = [path("profile/", us10_update_personal_information, name="us10_update_personal_information")]

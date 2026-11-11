"""US-05 Register Donor.

Tasks: donor form (also reused by US-07) -> view (create donor, auto ID DNR-0001...) -> GUI page -> URL.
"""
from django import forms
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import path

from .common import FORM_FIELDS, render_page
from .models import Donor, User
from .us04_user_roles import STAFF_ROLES, us04_role_required


# ---- Form (shared with US-07 Update Donor)
class US05DonorForm(forms.ModelForm):
    linked_username = forms.CharField(
        required=False,
        label="Linked user account (optional)",
        help_text="Username of a registered donor account, so the donor can see their own history (US-09).",
    )

    class Meta:
        model = Donor
        fields = ("name", "blood_group", "contact", "address")
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.user_id:
            self.fields["linked_username"].initial = self.instance.user.username

    def clean_linked_username(self):
        username = self.cleaned_data["linked_username"].strip()
        if not username:
            return None
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise forms.ValidationError("No user with that username exists.")
        if user.role != User.ROLE_DONOR:
            raise forms.ValidationError("Only donor-role accounts can be linked to a donor record.")
        other = Donor.objects.filter(user=user).exclude(pk=self.instance.pk).first()
        if other:
            raise forms.ValidationError(f"That account is already linked to {other.donor_id}.")
        return user

    def save(self, commit=True):
        donor = super().save(commit=False)
        donor.user = self.cleaned_data.get("linked_username")
        if commit:
            donor.save()
        return donor


# ---- GUI
TEMPLATE = (
    """<div class="card narrow"><h2>US-05 Register Donor</h2>
<form method="post" novalidate>{% csrf_token %}"""
    + FORM_FIELDS
    + """<button class="btn" type="submit">Register donor</button></form>
<p class="helptext">A unique donor ID (DNR-0001, ...) is generated automatically.</p></div>"""
)


# ---- View
@us04_role_required(*STAFF_ROLES)
def us05_register_donor(request):
    form = US05DonorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        donor = form.save()
        messages.success(request, f"Donor registered with ID {donor.donor_id}.")
        return redirect("us06_view_donor_detail", donor_pk=donor.pk)
    return render_page(request, TEMPLATE, {"form": form})


URLS = [path("donors/register/", us05_register_donor, name="us05_register_donor")]

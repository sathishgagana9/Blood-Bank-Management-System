
"""US-10 Update Personal Information.

Allows a logged-in user to update personal information.
Validates email and phone details and keeps linked donor information
consistent after a successful update.
"""

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect
from django.urls import path

from .common import FORM_FIELDS, render_page
from .models import Donor, User


# -------------------- FORM --------------------

class US10PersonalInformationForm(forms.ModelForm):
    """Form for updating a user's personal information."""

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone",
            "address",
        )
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Require all personal information fields.
        for field in self.fields.values():
            field.required = True

    def clean_email(self):
        """Check that the email is not used by another account."""
        email = self.cleaned_data["email"].strip().lower()

        existing_users = User.objects.filter(email__iexact=email)

        # Allow the current user to keep their existing email.
        if self.instance and self.instance.pk:
            existing_users = existing_users.exclude(
                pk=self.instance.pk
            )

        if existing_users.exists():
            raise forms.ValidationError(
                "An account with this email address already exists."
            )

        return email

    def clean_phone(self):
        """Validate the phone number format."""
        phone = self.cleaned_data["phone"].strip()

        # Allow digits, spaces, hyphens, and an optional leading '+'.
        digits_only = (
            phone.replace("+", "")
            .replace("-", "")
            .replace(" ", "")
        )

        if not digits_only.isdigit():
            raise forms.ValidationError(
                "Enter a valid phone number using digits, spaces, "
                "hyphens, and an optional leading plus sign."
            )

        if phone.count("+") > 1 or (
            "+" in phone and not phone.startswith("+")
        ):
            raise forms.ValidationError(
                "The plus sign is only allowed at the beginning "
                "of the phone number."
            )

        return phone


# -------------------- GUI --------------------

TEMPLATE = (
    """<div class="card narrow">
    <h2>US-10 Update Personal Information</h2>
    <form method="post" novalidate>
    {% csrf_token %}"""
    + FORM_FIELDS
    + """<button class="btn" type="submit">Save changes</button>
    </form>
    </div>"""
)


# -------------------- VIEW --------------------

@login_required
def us10_update_personal_information(request):
    """Display and process the personal information update form."""

    form = US10PersonalInformationForm(
        request.POST or None,
        instance=request.user,
    )

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            # Save the updated user information.
            user = form.save()

            # Update linked donor information, if a donor record exists.
            donor = Donor.objects.filter(user=user).first()

            if donor:
                donor.name = user.get_full_name() or donor.name
                donor.contact = user.phone or donor.contact
                donor.address = user.address or donor.address
                donor.save(
                    update_fields=["name", "contact", "address"]
                )

        messages.success(
            request,
            "Your personal information has been updated.",
        )

        return redirect("us10_update_personal_information")

    return render_page(
        request,
        TEMPLATE,
        {"form": form},
    )


# -------------------- URL --------------------

URLS = [
    path(
        "profile/",
        us10_update_personal_information,
        name="us10_update_personal_information",
    )
]

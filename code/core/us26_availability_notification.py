"""US-26 Availability Notification.

Tasks: subscription form (group, optional component / blood bank) -> automatic check after every stock change
(sends one notification when stock goes from 0 to available, then the subscription is closed) -> GUI page with
"my subscriptions" -> URLs.
"""
from django import forms
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse

from .common import FORM_FIELDS, render_page
from .models import AvailabilitySubscription, BloodBank, BloodInventory, Notification
from .us04_user_roles import ALL_ROLES, us04_role_required


# ---- Form
class US26SubscriptionForm(forms.ModelForm):
    blood_bank = forms.ModelChoiceField(queryset=BloodBank.objects.filter(is_active=True), required=False, empty_label="Any blood bank")

    class Meta:
        model = AvailabilitySubscription
        fields = ("blood_group", "component", "blood_bank")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["component"].choices = [("", "Any component")] + list(self.fields["component"].choices)[1:]


def us26_notify_subscribers(row, old_quantity):
    """Called after every stock change: stock just became available (0 -> more than 0)."""
    if not (old_quantity == 0 and row.quantity > 0):
        return
    subs = list(
        AvailabilitySubscription.objects.select_related("user")
        .filter(is_active=True, blood_group=row.blood_group)
        .filter(Q(component="") | Q(component=row.component))
        .filter(Q(blood_bank__isnull=True) | Q(blood_bank=row.blood_bank))
    )
    for sub in subs:
        Notification.send(
            [sub.user], "AVAILABILITY",
            f"{row.blood_group} {row.get_component_display()} is now available at {row.blood_bank} ({row.quantity} unit(s)).",
            link=reverse("us17_search_blood_availability"),
        )
    AvailabilitySubscription.objects.filter(pk__in=[s.pk for s in subs]).update(is_active=False)


# ---- GUI
TEMPLATE = (
    """<div class="card narrow"><h2>US-26 Availability Notifications</h2>
<p>Get a notification as soon as the blood you need is back in stock.</p>
<form method="post" novalidate>{% csrf_token %}"""
    + FORM_FIELDS
    + """<button class="btn" type="submit">Notify me</button></form></div>
<div class="card" style="margin-top:16px"><h3>My subscriptions</h3>
<table><tr><th>Blood group</th><th>Component</th><th>Blood bank</th><th>Status</th><th></th></tr>
{% for s in subscriptions %}
<tr><td>{{ s.blood_group }}</td><td>{{ s.get_component_display|default:"Any" }}</td><td>{{ s.blood_bank|default:"Any" }}</td>
<td>{% if s.is_active %}Waiting{% else %}Notified{% endif %}</td>
<td><form class="inline" method="post" action="{% url 'us26_cancel_subscription' s.pk %}">{% csrf_token %}<button class="btn secondary" style="margin:0" type="submit">Remove</button></form></td></tr>
{% empty %}<tr><td colspan="5">No subscriptions yet.</td></tr>{% endfor %}
</table></div>"""
)


# ---- Views
@us04_role_required(*ALL_ROLES)
def us26_availability_notification(request):
    initial = {k: request.GET[k] for k in ("blood_group", "component") if request.GET.get(k)}
    form = US26SubscriptionForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        sub = form.save(commit=False)
        sub.user = request.user
        sub.save()
        in_stock = BloodInventory.objects.filter(quantity__gt=0, blood_group=sub.blood_group, blood_bank__is_active=True)
        if sub.component:
            in_stock = in_stock.filter(component=sub.component)
        if sub.blood_bank:
            in_stock = in_stock.filter(blood_bank=sub.blood_bank)
        if in_stock.exists():
            messages.info(request, "This blood is already available right now - see Find Blood (US-17). You will also be told when it next returns to stock.")
        else:
            messages.success(request, "You will be notified when this blood becomes available.")
        return redirect("us26_availability_notification")
    subscriptions = AvailabilitySubscription.objects.filter(user=request.user).select_related("blood_bank")
    return render_page(request, TEMPLATE, {"form": form, "subscriptions": subscriptions})


@us04_role_required(*ALL_ROLES)
def us26_cancel_subscription(request, sub_pk):
    sub = get_object_or_404(AvailabilitySubscription, pk=sub_pk, user=request.user)
    if request.method == "POST":
        sub.delete()
        messages.success(request, "Subscription removed.")
    return redirect("us26_availability_notification")


URLS = [
    path("alerts/availability/", us26_availability_notification, name="us26_availability_notification"),
    path("alerts/availability/<int:sub_pk>/remove/", us26_cancel_subscription, name="us26_cancel_subscription"),
]

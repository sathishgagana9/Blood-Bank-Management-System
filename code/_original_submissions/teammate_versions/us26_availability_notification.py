"""US-26 Availability Notification.

Tasks: subscription form (blood group, component, blood bank) -> view (list/create/delete subscriptions)
-> inventory hook trigger (when stock is added or updated from 0 to positive, notify subscribed users)
-> GUI page -> URL.
"""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import path

from .common import FORM_FIELDS, render_page
from .models import (
    BLOOD_GROUPS,
    AvailabilitySubscription,
    BloodBank,
    Donation,
    Notification,
)


# ---- Form
class US26SubscriptionForm(forms.ModelForm):
    blood_bank = forms.ModelChoiceField(
        queryset=BloodBank.objects.filter(is_active=True),
        required=False,
        empty_label="Any Blood Bank / Location",
    )
    component = forms.ChoiceField(
        choices=[("", "Any Component")] + Donation.COMPONENT_CHOICES,
        required=False,
    )

    class Meta:
        model = AvailabilitySubscription
        fields = ("blood_group", "component", "blood_bank")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["blood_group"].required = True


# ---- GUI
TEMPLATE = """<div class="card">
<h2>US-26 Blood Availability Notifications</h2>
<p>Subscribe to receive notifications when required blood groups become available in inventory.</p>

<div class="card narrow" style="margin: 1.5rem 0; background: #fafafa;">
 <h3>Create New Availability Subscription</h3>
 <form method="post" novalidate>{% csrf_token %}
 """ + FORM_FIELDS + """
  <button class="btn" type="submit">Subscribe for Alerts</button>
 </form>
</div>

<h3>My Active Subscriptions</h3>
<table>
 <tr>
  <th>Blood Group</th>
  <th>Component</th>
  <th>Blood Bank</th>
  <th>Created Date</th>
  <th>Status</th>
  <th>Action</th>
 </tr>
 {% for sub in subscriptions %}
 <tr>
  <td><span class="badge">{{ sub.blood_group }}</span></td>
  <td>{{ sub.get_component_display|default:"Any Component" }}</td>
  <td>{{ sub.blood_bank.name|default:"Any Blood Bank" }}</td>
  <td>{{ sub.created_at|date:"Y-m-d H:i" }}</td>
  <td>
   {% if sub.is_active %}
    <span class="badge" style="background:#e3f6e8;color:#1e7e34;">Active (Listening)</span>
   {% else %}
    <span class="badge" style="background:#f0f0f4;color:#666;">Notified / Fulfilled</span>
   {% endif %}
  </td>
  <td>
   <form class="inline" method="post" action="{% url 'us26_delete_subscription' sub.pk %}">{% csrf_token %}
    <button class="btn secondary" style="background:#b91c1c;margin:0;padding:4px 10px;font-size:0.85em;" type="submit">Remove</button>
   </form>
  </td>
 </tr>
 {% empty %}
 <tr><td colspan="6">You have no active availability subscriptions. Create one above to receive alerts.</td></tr>
 {% endfor %}
</table>

<div style="margin-top: 1.5rem;">
 <a class="btn secondary" href="{% url 'home' %}">Return Home</a>
 <a class="btn" style="margin-left:0.5rem;" href="{% url 'us17_search_blood_availability' %}">Check Current Blood Availability</a>
</div>
</div>"""


# ---- Logic / Trigger Function
def trigger_availability_notifications(inventory_row):
    """Notify relevant subscribed users when blood availability increases.

    Acceptance criteria:
    - Availability changes can trigger notifications.
    - Relevant users receive the notification.
    - Notification contains relevant availability information.
    """
    if inventory_row.quantity <= 0:
        return 0

    # Find active subscriptions matching the blood group, component (or Any), and blood bank (or Any)
    subs = AvailabilitySubscription.objects.filter(
        is_active=True,
        blood_group=inventory_row.blood_group,
    ).select_related("user", "blood_bank")

    notified_count = 0
    for sub in subs:
        if sub.component and sub.component != inventory_row.component:
            continue
        if sub.blood_bank and sub.blood_bank != inventory_row.blood_bank:
            continue

        message = (
            f"Blood availability update: {inventory_row.blood_group} "
            f"({inventory_row.get_component_display()}) is now available at {inventory_row.blood_bank.name} "
            f"({inventory_row.quantity} unit(s) in stock)."
        )

        Notification.objects.create(
            user=sub.user,
            category="AVAILABILITY",
            message=message,
            link="/availability/",
        )
        # Deactivate subscription after notifying so user is not spammed
        sub.is_active = False
        sub.save(update_fields=["is_active"])
        notified_count += 1

    return notified_count


# ---- Views
@login_required
def us26_availability_notification(request):
    """View and manage availability alert subscriptions."""
    form = US26SubscriptionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        subscription = form.save(commit=False)
        subscription.user = request.user
        subscription.is_active = True
        subscription.save()

        messages.success(
            request,
            f"Subscribed for {subscription.blood_group} availability alerts. "
            f"You will receive an in-app notification when matching blood becomes available.",
        )
        return redirect("us26_availability_notification")

    subscriptions = AvailabilitySubscription.objects.filter(user=request.user).order_by("-created_at")
    return render_page(request, TEMPLATE, {"form": form, "subscriptions": subscriptions})


@login_required
def us26_delete_subscription(request, subscription_pk):
    """Delete / remove an existing subscription."""
    sub = get_object_or_404(AvailabilitySubscription, pk=subscription_pk, user=request.user)
    if request.method == "POST":
        sub.delete()
        messages.success(request, "Availability alert subscription removed.")
    return redirect("us26_availability_notification")


URLS = [
    path("availability/alerts/", us26_availability_notification, name="us26_availability_notification"),
    path("availability/alerts/<int:subscription_pk>/delete/", us26_delete_subscription, name="us26_delete_subscription"),
]

"""US-09 View Donation History.

Tasks: view donor donation history -> display previous donations & summary -> GUI page -> URL.
"""
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect
from django.urls import path

from .common import render_page
from .models import Donation, Donor

# ---- GUI
TEMPLATE = """<div class="card">
<h2>US-09 My Donation History</h2>
<p>Track your previous blood donations and personal donation history.</p>

{% if donor %}
<div class="donor-details" style="display:flex;gap:2rem;flex-wrap:wrap;background:#f8fafc;padding:1rem;border-radius:6px;margin:1rem 0;">
 <div><strong>Donor ID:</strong> {{ donor.donor_id }}</div>
 <div><strong>Name:</strong> {{ donor.name }}</div>
 <div><strong>Blood Group:</strong> <span class="badge">{{ donor.blood_group }}</span></div>
 <div><strong>Total Donations:</strong> {{ total_donations }}</div>
 <div><strong>Total Volume Donated:</strong> {{ total_volume|default:0 }} ml</div>
</div>

<table>
 <tr>
  <th>Donation ID</th>
  <th>Date</th>
  <th>Blood Group</th>
  <th>Quantity</th>
  <th>Blood Bank / Center</th>
  <th>Status</th>
 </tr>
 {% for don in donations %}
 <tr>
  <td><strong>{{ don.donation_id }}</strong></td>
  <td>{{ don.date }}</td>
  <td><span class="badge">{{ don.blood_group }}</span></td>
  <td>{{ don.quantity }} ml</td>
  <td>{{ don.blood_bank }}</td>
  <td>{{ don.status }}</td>
 </tr>
 {% empty %}
 <tr><td colspan="6">No previous blood donations recorded for your profile.</td></tr>
 {% endfor %}
</table>
{% else %}
<div class="alert alert-info" style="margin-top:1rem;">
 <p>No donor profile is currently linked to your user account (<strong>{{ request.user.username }}</strong>).</p>
 <p>If you are a registered blood donor, please contact staff to associate your donor record.</p>
</div>
{% endif %}
<p style="margin-top:1.5rem;"><a class="btn" href="{% url 'home' %}">Return Home</a></p>
</div>"""


# ---- Views
@login_required
def us09_view_donation_history(request):
    donor = Donor.objects.filter(user=request.user).first()
    if not donor and getattr(request.user, "email", None):
        donor = Donor.objects.filter(email__iexact=request.user.email).first()

    donations = []
    total_donations = 0
    total_volume = 0

    if donor:
        donations = Donation.objects.filter(donor=donor).order_by("-date")
        total_donations = donations.count()
        total_volume = donations.aggregate(Sum("quantity"))["quantity__sum"] or 0

    return render_page(
        request,
        TEMPLATE,
        {
            "donor": donor,
            "donations": donations,
            "total_donations": total_donations,
            "total_volume": total_volume,
        },
    )


URLS = [
    path("donations/history/", us09_view_donation_history, name="us09_view_donation_history"),
]

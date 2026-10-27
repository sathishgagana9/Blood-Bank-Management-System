"""Shared presentation helpers for Blood Bank Management System user stories."""
from django.http import HttpResponse
from django.template import Context, Template

FORM_FIELDS = """{% for field in form %}
<div class="form-group" style="margin-bottom: 1rem;">
    {{ field.label_tag }}
    {{ field }}
    {% if field.errors %}<div class="error" style="color: #b91c1c; font-size: 0.875rem; margin-top: 0.25rem;">{{ field.errors.0 }}</div>{% endif %}
</div>
{% endfor %}"""

BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blood Bank Management System</title>
    <style>
        :root {
            --primary: #c0392b;
            --primary-dark: #962d22;
            --bg: #f8f9fa;
            --card-bg: #ffffff;
            --text: #2c3e50;
            --border: #e2e8f0;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; }
        body { background: var(--bg); color: var(--text); line-height: 1.6; }
        header { background: var(--primary); color: white; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }
        header h1 { font-size: 1.3rem; }
        header nav { display: flex; align-items: center; gap: 1rem; }
        header nav a { color: white; text-decoration: none; font-weight: 500; font-size: 0.95rem; }
        header nav a:hover { text-decoration: underline; }
        main { max-width: 1000px; margin: 2rem auto; padding: 0 1rem; }
        .card { background: var(--card-bg); border-radius: 8px; padding: 2rem; box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 2rem; }
        .card.narrow { max-width: 480px; margin: 2rem auto; }
        h2 { margin-bottom: 1.2rem; color: var(--primary-dark); font-size: 1.5rem; }
        h3 { margin: 1.5rem 0 0.8rem; font-size: 1.2rem; }
        table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
        th, td { text-align: left; padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); font-size: 0.95rem; }
        th { background: #f1f5f9; color: #475569; }
        .btn { background: var(--primary); color: white; border: none; padding: 0.5rem 1.2rem; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; font-size: 0.95rem; }
        .btn:hover { background: var(--primary-dark); }
        .badge { background: #e0f2fe; color: #0369a1; padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: 600; font-size: 0.85rem; }
        .filters { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; align-items: flex-end; }
        .filters > div { display: flex; flex-direction: column; gap: 0.3rem; }
        input[type="text"], input[type="password"], input[type="email"], select, textarea {
            width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 0.95rem;
        }
        .alert { padding: 0.8rem 1.2rem; border-radius: 4px; margin-bottom: 1rem; font-size: 0.95rem; }
        .alert-success { background: #dcfce7; color: #15803d; }
        .alert-error, .alert-danger { background: #fee2e2; color: #b91c1c; }
        .alert-info { background: #e0f2fe; color: #0369a1; }
        .donor-details p { margin-bottom: 0.5rem; }
    </style>
</head>
<body>
    <header>
        <h1>Blood Bank Management System</h1>
        <nav>
            <a href="/">Home</a>
            {% if request.user.is_authenticated %}
                <a href="/donors/">View Donors</a>
                <a href="/donors/search/">Search Donors</a>
                {% if request.user.role == 'admin' or request.user.is_superuser %}
                    <a href="/admin/roles/">Manage Roles</a>
                {% endif %}
                <form action="/logout/" method="post" style="display:inline; margin-left: 1rem;">
                    {% csrf_token %}
                    <button type="submit" style="background:none;border:none;color:white;cursor:pointer;font-weight:500;font-size:0.95rem;">Log out</button>
                </form>
            {% else %}
                <a href="/login/">Log in</a>
                <a href="/register/">Register</a>
            {% endif %}
        </nav>
    </header>
    <main>
        {% if messages %}
            {% for message in messages %}
                <div class="alert alert-{{ message.tags }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
        {{ content|safe }}
    </main>
</body>
</html>"""


def render_page(request, template_str, context=None, status=200):
    """Render a user story template inside the shared application layout."""
    ctx = context or {}
    ctx["request"] = request
    inner = Template(template_str).render(Context(ctx))
    layout_ctx = {
        "request": request,
        "content": inner,
        "messages": getattr(request, "_messages", []),
    }
    html = Template(BASE_TEMPLATE).render(Context(layout_ctx))
    return HttpResponse(html, status=status)

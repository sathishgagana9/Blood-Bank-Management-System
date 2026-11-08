from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        from . import us33_view_system_activities  # noqa: F401  (connects the activity-log signals, US-33)

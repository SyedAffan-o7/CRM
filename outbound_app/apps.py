from django.apps import AppConfig


class OutboundAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'outbound_app'
    verbose_name = 'Outbound'

    def ready(self):
        # Import signal handlers
        try:
            from . import signals  # noqa: F401
        except Exception:
            # Avoid import-time crashes; signals should not break startup
            pass

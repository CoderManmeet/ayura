from django.apps import AppConfig


class SupportConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "support"
    verbose_name = "Customer support"

    def ready(self):
        # Registering the email jobs is a side effect of importing the module (@job).
        from support import emails  # noqa: F401

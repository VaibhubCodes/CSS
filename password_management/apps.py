from django.apps import AppConfig


class PasswordManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "password_management"
    verbose_name = "Password Management"

    def ready(self):
        # Import signal handlers
        import password_management.views

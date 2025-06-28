from django.apps import AppConfig

class StorageManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'storage_management'

    def ready(self):
        import storage_management.models  # This imports the signals
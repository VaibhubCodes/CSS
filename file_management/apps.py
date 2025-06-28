from django.apps import AppConfig


class FileManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'file_management'
    
    def ready(self):
        from . import signals
        from .utils import create_default_categories
        import threading
        threading.Timer(5, create_default_categories).start()


from django.core.management.base import BaseCommand
from file_management.services import ExpiryManagementService

class Command(BaseCommand):
    help = 'Check and move expired items to EXPIRED_DOCS category'

    def handle(self, *args, **options):
        service = ExpiryManagementService()
        service.check_and_move_expired_items()
        self.stdout.write(self.style.SUCCESS('Successfully checked for expired items'))
from django.core.management.base import BaseCommand
from file_management.utils import create_default_categories

class Command(BaseCommand):
    help = 'Creates default file categories'

    def handle(self, *args, **options):
        create_default_categories()
        self.stdout.write(self.style.SUCCESS('Successfully created default categories'))
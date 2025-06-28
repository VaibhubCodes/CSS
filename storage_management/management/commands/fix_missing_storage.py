from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from storage_management.models import UserStorage

class Command(BaseCommand):
    help = 'Fix missing UserStorage records for existing users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('Checking for users without UserStorage records...'))
        
        users_without_storage = []
        for user in User.objects.all():
            try:
                UserStorage.objects.get(user=user)
                self.stdout.write(f'✅ {user.email} has storage record')
            except UserStorage.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'❌ {user.email} MISSING storage record'))
                users_without_storage.append(user)

        if not users_without_storage:
            self.stdout.write(self.style.SUCCESS('\n✅ All users have storage records'))
            return

        self.stdout.write(f'\nFound {len(users_without_storage)} users without storage records')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
            for user in users_without_storage:
                self.stdout.write(f'Would create storage record for {user.email}')
        else:
            created_count = 0
            for user in users_without_storage:
                storage, created = UserStorage.objects.get_or_create(
                    user=user,
                    defaults={
                        'storage_used': 0,
                        'storage_limit': 5368709120  # 5GB default
                    }
                )
                if created:
                    # Update storage limit based on subscription if available
                    try:
                        storage.update_from_subscription()
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f'Could not update subscription info for {user.email}: {e}')
                        )
                    
                    self.stdout.write(f'✅ Created storage record for {user.email}')
                    created_count += 1
                else:
                    self.stdout.write(f'⚠️  Storage record already exists for {user.email}')

            self.stdout.write(
                self.style.SUCCESS(f'\n✅ Successfully created {created_count} storage records')
            ) 
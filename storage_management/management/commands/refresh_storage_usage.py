from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from storage_management.models import UserStorage
from storage_management.utils import S3StorageManager

class Command(BaseCommand):
    help = 'Refresh storage usage for all users from S3'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Refresh storage for specific user (email)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        dry_run = options['dry_run']
        specific_user = options['user']
        
        if specific_user:
            try:
                users = [User.objects.get(email=specific_user)]
                self.stdout.write(f'Refreshing storage for user: {specific_user}')
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User {specific_user} not found'))
                return
        else:
            users = User.objects.all()
            self.stdout.write(f'Refreshing storage for all {users.count()} users...')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        updated_count = 0
        error_count = 0
        
        for user in users:
            try:
                # Ensure user has a storage record
                storage, created = UserStorage.objects.get_or_create(
                    user=user,
                    defaults={
                        'storage_used': 0,
                        'storage_limit': 5368709120  # 5GB default
                    }
                )
                
                if created:
                    self.stdout.write(f'Created missing storage record for {user.email}')
                
                # Get current usage from database
                old_usage = storage.storage_used
                
                # Calculate actual usage from S3
                storage_manager = S3StorageManager(user)
                
                if dry_run:
                    # Just show what would happen
                    try:
                        storage_info = storage_manager.get_user_storage_info()
                        new_usage = storage_info['used']
                        self.stdout.write(
                            f'📊 {user.email}: {old_usage} bytes → {new_usage} bytes '
                            f'(Δ {new_usage - old_usage:+d} bytes)'
                        )
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'❌ {user.email}: Error calculating - {e}'))
                        error_count += 1
                else:
                    # Actually update the storage
                    storage_info = storage_manager.get_user_storage_info()
                    new_usage = storage_info['used']
                    
                    self.stdout.write(
                        f'✅ {user.email}: {old_usage} bytes → {new_usage} bytes '
                        f'(Δ {new_usage - old_usage:+d} bytes)'
                    )
                    updated_count += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ {user.email}: {e}'))
                error_count += 1
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'\n✅ Successfully updated {updated_count} users')
            )
        
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(f'⚠️  {error_count} errors encountered')
            ) 
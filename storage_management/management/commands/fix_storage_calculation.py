# management/commands/fix_storage_calculation.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from storage_management.models import UserStorage
from storage_management.utils import S3StorageManager
from file_management.models import UserFile
from django.db import models
class Command(BaseCommand):
    help = 'Fix storage calculation issues and clean up phantom usage'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Fix storage for specific user ID',
        )
        parser.add_argument(
            '--clean-orphans',
            action='store_true',
            help='Clean up orphaned S3 files',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        dry_run = options['dry_run']
        clean_orphans = options['clean_orphans']
        user_id = options['user_id']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                users = [user]
                self.stdout.write(f'Fixing storage for user: {user.email}')
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User with ID {user_id} not found'))
                return
        else:
            users = User.objects.all()
            self.stdout.write(f'Fixing storage for all {users.count()} users...')
        
        fixed_count = 0
        error_count = 0
        total_phantom_usage = 0
        
        for user in users:
            try:
                # Get current storage record
                storage, created = UserStorage.objects.get_or_create(
                    user=user,
                    defaults={'storage_used': 0, 'storage_limit': 5368709120}
                )
                
                old_usage = storage.storage_used
                
                # Calculate accurate storage
                storage_manager = S3StorageManager(user)
                
                # Get database file count and size
                user_files = UserFile.objects.filter(user=user)
                db_file_count = user_files.count()
                db_total_size = user_files.aggregate(
                    total=models.Sum('file_size')
                )['total'] or 0
                
                if dry_run:
                    # Just show what would happen
                    storage_info = storage_manager.get_user_storage_info()
                    new_usage = storage_info['used']
                    phantom_usage = old_usage - new_usage
                    
                    self.stdout.write(
                        f'👤 {user.email}:'
                    )
                    self.stdout.write(
                        f'   📊 Current: {self.format_size(old_usage)} | '
                        f'Correct: {self.format_size(new_usage)} | '
                        f'DB Files: {db_file_count} ({self.format_size(db_total_size)})'
                    )
                    
                    if phantom_usage > 1024:  # > 1KB
                        self.stdout.write(
                            self.style.WARNING(f'   👻 Phantom usage: {self.format_size(phantom_usage)}')
                        )
                        total_phantom_usage += phantom_usage
                    
                    if clean_orphans:
                        orphan_info = storage_manager.clean_orphaned_files(dry_run=True)
                        if orphan_info.get('total_size', 0) > 0:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'   🗑️  Orphaned files: {len(orphan_info["orphaned_files"])} '
                                    f'({self.format_size(orphan_info["total_size"])})'
                                )
                            )
                else:
                    # Actually fix the storage
                    storage_info = storage_manager.get_user_storage_info()
                    new_usage = storage_info['used']
                    phantom_usage = old_usage - new_usage
                    
                    self.stdout.write(
                        f'✅ {user.email}: {self.format_size(old_usage)} → {self.format_size(new_usage)} '
                        f'(Files: {db_file_count})'
                    )
                    
                    if phantom_usage > 1024:
                        self.stdout.write(
                            self.style.SUCCESS(f'   🔧 Fixed phantom usage: {self.format_size(phantom_usage)}')
                        )
                        total_phantom_usage += phantom_usage
                    
                    if clean_orphans and not dry_run:
                        orphan_info = storage_manager.clean_orphaned_files(dry_run=False)
                        if orphan_info.get('total_size', 0) > 0:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'   🗑️  Cleaned orphaned files: {len(orphan_info["orphaned_files"])} '
                                    f'({self.format_size(orphan_info["total_size"])})'
                                )
                            )
                    
                    fixed_count += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ {user.email}: {e}'))
                error_count += 1
        
        # Summary
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'\n✅ Successfully fixed {fixed_count} users')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'\n📊 Would fix {len(users)} users')
            )
        
        if total_phantom_usage > 0:
            self.stdout.write(
                self.style.SUCCESS(f'👻 Total phantom usage {"would be" if dry_run else ""} recovered: {self.format_size(total_phantom_usage)}')
            )
        
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(f'⚠️  {error_count} errors encountered')
            )

    def format_size(self, size_in_bytes):
        """Format bytes to human readable size"""
        if size_in_bytes == 0:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_in_bytes < 1024:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024
        return f"{size_in_bytes:.2f} TB"
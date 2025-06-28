from django.core.management.base import BaseCommand
from file_management.models import UserFile
from storage_management.utils import S3StorageManager
import boto3
from django.conf import settings

class Command(BaseCommand):
    help = 'Diagnose S3 file storage issues'

    def add_arguments(self, parser):
        parser.add_argument('--file-id', type=int, help='Specific file ID to diagnose')
        parser.add_argument('--user-id', type=int, help='Specific user ID to check')
        parser.add_argument('--fix-keys', action='store_true', help='Attempt to fix incorrect S3 keys')

    def handle(self, *args, **options):
        if options['file_id']:
            self.diagnose_file(options['file_id'], options['fix_keys'])
        elif options['user_id']:
            self.diagnose_user_files(options['user_id'], options['fix_keys'])
        else:
            self.diagnose_all_files(options['fix_keys'])

    def diagnose_file(self, file_id, fix_keys=False):
        try:
            file = UserFile.objects.get(id=file_id)
            self.stdout.write(f"\n=== Diagnosing File {file_id} ===")
            self.stdout.write(f"Original filename: {file.original_filename}")
            self.stdout.write(f"File field: {file.file.name if file.file else 'None'}")
            self.stdout.write(f"S3 key: {file.s3_key}")
            
            storage_manager = S3StorageManager(file.user)
            
            # Check current S3 key
            if file.s3_key:
                exists = storage_manager.file_exists(file.s3_key)
                self.stdout.write(f"S3 key exists: {exists}")
            
            # Try to find the file with different keys
            possible_keys = [
                file.s3_key,
                file.file.name if file.file else None,
                f"uploads/{file.original_filename}",
                f"user_{file.user.id}/{file.original_filename}",
                file.original_filename
            ]
            
            working_key = None
            self.stdout.write(f"\nTrying different S3 keys:")
            for key in possible_keys:
                if key:
                    exists = storage_manager.file_exists(key)
                    self.stdout.write(f"  {key}: {'✓' if exists else '✗'}")
                    if exists and not working_key:
                        working_key = key
            
            if working_key and working_key != file.s3_key and fix_keys:
                self.stdout.write(f"\nFixing S3 key: {file.s3_key} → {working_key}")
                file.s3_key = working_key
                file.save(update_fields=['s3_key'])
                self.stdout.write("✓ S3 key updated")
            
        except UserFile.DoesNotExist:
            self.stdout.write(f"File {file_id} not found")
        except Exception as e:
            self.stdout.write(f"Error diagnosing file {file_id}: {str(e)}")

    def diagnose_user_files(self, user_id, fix_keys=False):
        files = UserFile.objects.filter(user_id=user_id)
        self.stdout.write(f"\n=== Diagnosing {files.count()} files for user {user_id} ===")
        
        for file in files:
            self.diagnose_file(file.id, fix_keys)

    def diagnose_all_files(self, fix_keys=False):
        files = UserFile.objects.all()
        self.stdout.write(f"\n=== Diagnosing {files.count()} total files ===")
        
        issues_found = 0
        for file in files:
            try:
                storage_manager = S3StorageManager(file.user)
                if file.s3_key and not storage_manager.file_exists(file.s3_key):
                    issues_found += 1
                    self.stdout.write(f"Issue: File {file.id} - S3 key not found: {file.s3_key}")
                    
                    if fix_keys:
                        self.diagnose_file(file.id, True)
                        
            except Exception as e:
                self.stdout.write(f"Error checking file {file.id}: {str(e)}")
        
        self.stdout.write(f"\nFound {issues_found} files with S3 issues")
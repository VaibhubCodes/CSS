import boto3
from django.db import models
from django.conf import settings
from .models import UserStorage
from django.utils import timezone
from storage_management.models import AdminAccessLog 
import logging
logger = logging.getLogger(__name__)
def log_admin_access(user, file_key):
    """Log when admin accesses files through AWS console"""
    if settings.AWS_LOGGING:
        admin_log = AdminAccessLog.objects.create(
            admin_user=user,
            accessed_file=file_key,
            access_time=timezone.now()
        )
        return admin_log

class S3StorageManager:
    def __init__(self, user):
        self.user = user
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        self.user_prefix = f"user_{user.id}/"

    def get_user_storage_info(self):
        """Get current storage usage for user"""
        try:
            # Method 1: Calculate from database records (primary source)
            db_total_size = self._calculate_db_storage()
            
            # Method 2: Calculate from S3 (verification)
            s3_total_size = self._calculate_s3_storage()
            
            # Method 3: Cross-validation and cleanup
            validated_size = self._validate_and_cleanup_storage(db_total_size, s3_total_size)
            
            # Update storage usage in database
            storage, created = UserStorage.objects.get_or_create(
                user=self.user,
                defaults={
                    'storage_used': 0,
                    'storage_limit': 5368709120  # 5GB default
                }
            )
            
            if created:
                logger.info(f"[S3StorageManager] Created UserStorage for user {self.user.email} (ID: {self.user.id})")
                # Update storage limit based on subscription if available
                try:
                    storage.update_from_subscription()
                except Exception as e:
                    logger.warning(f"[S3StorageManager] Could not update subscription for {self.user.email}: {e}")
            
            # Only update if there's a significant change (avoid constant updates)
            if abs(storage.storage_used - validated_size) > 1024:  # 1KB threshold
                storage.storage_used = validated_size
                storage.save(update_fields=['storage_used'])
                logger.info(f"[S3StorageManager] Updated storage for user {self.user.email}: {validated_size} bytes")
            
            return {
                'used': validated_size,
                'limit': storage.storage_limit,
                'available': storage.get_available_storage(),
                'percentage_used': storage.get_usage_percentage(),
                'db_size': db_total_size,
                's3_size': s3_total_size,
                'validation_method': 'database_primary'
            }
            
        except Exception as e:
            logger.error(f"[S3StorageManager] Error getting storage info for user {self.user.id}: {str(e)}")
            raise Exception(f"Error getting storage info: {str(e)}")

    def _calculate_db_storage(self):
        """Calculate storage from database UserFile records"""
        try:
            from file_management.models import UserFile
            total_size = UserFile.objects.filter(
                user=self.user
            ).aggregate(
                total=models.Sum('file_size')
            )['total'] or 0
            
            logger.debug(f"[DB Storage] User {self.user.id} has {total_size} bytes from database")
            return total_size
            
        except Exception as e:
            logger.error(f"[DB Storage] Error calculating database storage for user {self.user.id}: {e}")
            return 0

    def _calculate_s3_storage(self):
        """Calculate storage from S3 with filtering"""
        try:
            from file_management.models import UserFile
            
            # Get valid S3 keys from database
            valid_s3_keys = set(
                UserFile.objects.filter(user=self.user)
                .exclude(s3_key__isnull=True)
                .exclude(s3_key__exact='')
                .values_list('s3_key', flat=True)
            )
            
            # Also include file.name as potential S3 key
            valid_file_names = set(
                UserFile.objects.filter(user=self.user)
                .exclude(file__isnull=True)
                .exclude(file__exact='')
                .values_list('file', flat=True)
            )
            
            all_valid_keys = valid_s3_keys.union(valid_file_names)
            
            if not all_valid_keys:
                logger.debug(f"[S3 Storage] User {self.user.id} has no valid S3 keys")
                return 0
            
            # Calculate size only for valid files
            paginator = self.s3_client.get_paginator('list_objects_v2')
            total_size = 0
            found_files = 0
            orphaned_files = []
            
            for page in paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=self.user_prefix
            ):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        s3_key = obj['Key']
                        file_size = obj['Size']
                        
                        # Check if this S3 key corresponds to a valid database record
                        if s3_key in all_valid_keys or any(key in s3_key for key in all_valid_keys):
                            total_size += file_size
                            found_files += 1
                        else:
                            # Potential orphaned file
                            orphaned_files.append({
                                'key': s3_key,
                                'size': file_size,
                                'last_modified': obj.get('LastModified')
                            })
            
            logger.debug(f"[S3 Storage] User {self.user.id}: {total_size} bytes from {found_files} valid files")
            
            if orphaned_files:
                logger.warning(f"[S3 Storage] User {self.user.id} has {len(orphaned_files)} orphaned files")
                for orphan in orphaned_files[:5]:  # Log first 5
                    logger.warning(f"  Orphaned: {orphan['key']} ({orphan['size']} bytes)")
            
            return total_size
            
        except Exception as e:
            logger.error(f"[S3 Storage] Error calculating S3 storage for user {self.user.id}: {e}")
            return 0

    def _validate_and_cleanup_storage(self, db_size, s3_size):
        """Cross-validate and determine accurate storage size"""
        
        # If no files in database, storage should be 0
        if db_size == 0:
            logger.info(f"[Storage Validation] User {self.user.id} has no database files, setting storage to 0")
            return 0
        
        # If database and S3 sizes match closely (within 10%), use database size
        if db_size > 0 and s3_size > 0:
            size_diff = abs(db_size - s3_size)
            percentage_diff = (size_diff / max(db_size, s3_size)) * 100
            
            if percentage_diff <= 10:  # Within 10% tolerance
                logger.debug(f"[Storage Validation] Sizes match closely: DB={db_size}, S3={s3_size}")
                return db_size
            else:
                logger.warning(f"[Storage Validation] Size mismatch: DB={db_size}, S3={s3_size} ({percentage_diff:.1f}% diff)")
        
        # If S3 shows files but database doesn't, investigate
        if db_size == 0 and s3_size > 0:
            logger.warning(f"[Storage Validation] Orphaned S3 files detected for user {self.user.id}: {s3_size} bytes")
            # Optionally trigger cleanup
            self._schedule_orphan_cleanup()
            return 0  # Trust database as source of truth
        
        # If database shows files but S3 doesn't, files may be missing
        if db_size > 0 and s3_size == 0:
            logger.error(f"[Storage Validation] Missing S3 files for user {self.user.id}: DB shows {db_size} bytes")
            return db_size  # Trust database, files may be in different location
        
        # Default: use database size as source of truth
        return db_size

    def get_file_url(self, s3_key, expiry=3600, response_content_disposition=None):
        """
        Generate a presigned URL for accessing an S3 object.

        Args:
            s3_key (str): The full S3 key (path) of the object within the bucket
                        (e.g., 'user_1/documents/report.pdf').
            expiry (int): Duration in seconds for which the URL should be valid.
                            Defaults to 3600 seconds (1 hour).
            response_content_disposition (str, optional): Sets the Content-Disposition header
                        for the response. Useful for forcing download with a specific filename
                        (e.g., 'attachment; filename="your_filename.pdf"'). Defaults to None.


        Returns:
            str or None: The presigned URL if successful, None otherwise.
        """
        # Ensure the S3 client was initialized correctly
        if not self.s3_client or not self.bucket_name:
            logger.error(f"S3 client or bucket name not initialized for user {self.user.id}. Cannot generate URL for key '{s3_key}'.")
            return None

        # Validate the s3_key format (optional but good practice)
        if not s3_key or not isinstance(s3_key, str):
            logger.error(f"Invalid S3 key provided for URL generation: {s3_key}")
            return None
        # You might add more specific checks, e.g., ensuring it contains the user prefix if required by policy
        # if not s3_key.startswith(self.user_prefix):
        #     logger.warning(f"S3 key '{s3_key}' might not be within the expected user prefix '{self.user_prefix}'.")

        try:
            logger.debug(f"Generating presigned URL for user {self.user.id}, key: '{s3_key}', expiry: {expiry} seconds.")

            # Prepare parameters for generate_presigned_url
            params = {
                'Bucket': self.bucket_name,
                'Key': s3_key
            }

            # Add Content-Disposition if requested (for download links)
            if response_content_disposition:
                params['ResponseContentDisposition'] = response_content_disposition
                logger.debug(f"Setting ResponseContentDisposition: {response_content_disposition}")


            # Generate the presigned URL for a GET request
            url = self.s3_client.generate_presigned_url(
                ClientMethod='get_object',
                Params=params,
                ExpiresIn=expiry # Pass the expiry duration here
            )

            logger.info(f"Successfully generated presigned URL for key '{s3_key}' (expires in {expiry}s).")
            logger.debug(f"Generated URL (first 100 chars): {url[:100]}...") # Log part of URL for verification
            return url

        except Exception as e:
            # Catch potential errors from boto3 (e.g., credentials error, bucket not found, key not found (less likely for get_object URL generation))
            logger.exception(f"Error generating presigned URL for user {self.user.id}, key '{s3_key}': {str(e)}")
            return None

    # def get_user_files(self):
    #     """List all files in user's S3 directory"""
    #     try:
    #         response = self.s3_client.list_objects_v2(
    #             Bucket=self.bucket_name,
    #             Prefix=self.user_prefix
    #         )
    #         return response.get('Contents', [])
    #     except Exception as e:
    #         raise Exception(f"Error listing user files: {str(e)}")

    def get_user_files(self):
        """List all files in user's S3 directory with database correlation"""
        try:
            from file_management.models import UserFile
            
            # Get database files
            db_files = {
                uf.s3_key or uf.file.name: uf 
                for uf in UserFile.objects.filter(user=self.user) 
                if uf.s3_key or uf.file.name
            }
            
            # Get S3 files
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.user_prefix
            )
            
            s3_objects = response.get('Contents', [])
            
            # Correlate S3 and database files
            correlated_files = []
            orphaned_files = []
            
            for obj in s3_objects:
                s3_key = obj['Key']
                if s3_key in db_files:
                    correlated_files.append({
                        's3_object': obj,
                        'db_file': db_files[s3_key],
                        'status': 'matched'
                    })
                else:
                    orphaned_files.append({
                        's3_object': obj,
                        'status': 'orphaned'
                    })
            
            return {
                'correlated_files': correlated_files,
                'orphaned_files': orphaned_files,
                'total_s3_objects': len(s3_objects),
                'total_db_files': len(db_files)
            }
            
        except Exception as e:
            logger.error(f"Error listing user files for user {self.user.id}: {str(e)}")
            return {'error': str(e)}

    def check_storage_limit(self, file_size):
        """Check if uploading file would exceed storage limit"""
        try:
            storage, created = UserStorage.objects.get_or_create(
                user=self.user,
                defaults={'storage_used': 0, 'storage_limit': 5368709120}
            )
            
            return (storage.storage_used + file_size) <= storage.storage_limit
            
        except Exception as e:
            logger.error(f"Error checking storage limit for user {self.user.id}: {e}")
            return False

    # def upload_file(self, file_obj, file_name):
    #     """Upload file to user's S3 directory"""
    #     if hasattr(file_obj, 'size'):
    #         file_size = file_obj.size
    #     else:
    #         file_obj.seek(0, 2)  # Seek to end
    #         file_size = file_obj.tell()
    #         file_obj.seek(0)  # Seek back to start
            
    #     if not self.check_storage_limit(file_size):
    #         raise Exception("Storage limit would be exceeded")

    #     try:
    #         # Generate S3 key with user prefix
    #         s3_key = f"{self.user_prefix}{file_name}"
            
    #         # Upload file
    #         self.s3_client.upload_fileobj(
    #             file_obj,
    #             self.bucket_name,
    #             s3_key
    #         )
            
    #         # Update storage usage
    #         storage = UserStorage.objects.get(user=self.user)
    #         storage.storage_used += file_size
    #         storage.save()
            
    #         return s3_key
    #     except Exception as e:
    #         raise Exception(f"Error uploading file: {str(e)}")

    def upload_file(self, file_obj, file_name):
        """Upload file with accurate size tracking"""
        try:
            # Get file size before upload
            if hasattr(file_obj, 'size'):
                file_size = file_obj.size
            else:
                file_obj.seek(0, 2)  # Seek to end
                file_size = file_obj.tell()
                file_obj.seek(0)  # Seek back to start
            
            # Check storage limit
            if not self.check_storage_limit(file_size):
                raise Exception("Storage limit would be exceeded")

            s3_key = f"{self.user_prefix}{file_name}"
            
            # Upload with metadata
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ACL': 'private',
                    'Metadata': {
                        'user_id': str(self.user.id),
                        'upload_date': timezone.now().isoformat(),
                        'original_filename': file_name,
                        'file_size': str(file_size)
                    }
                }
            )
            
            # Update storage usage accurately
            storage, created = UserStorage.objects.get_or_create(
                user=self.user,
                defaults={'storage_used': 0, 'storage_limit': 5368709120}
            )
            
            storage.storage_used += file_size
            storage.save(update_fields=['storage_used'])
            
            logger.info(f"[Upload] User {self.user.id} uploaded {file_name} ({file_size} bytes)")
            
            return s3_key
            
        except Exception as e:
            logger.error(f"Upload error for user {self.user.id}: {str(e)}")
            raise Exception(f"Error uploading file: {str(e)}")


    # def delete_file(self, file_name):
    #     """Delete file from user's S3 directory"""
    #     try:
    #         # Get file size before deletion
    #         response = self.s3_client.head_object(
    #             Bucket=self.bucket_name,
    #             Key=f"{self.user_prefix}{file_name}"
    #         )
    #         file_size = response['ContentLength']
            
    #         # Delete file
    #         self.s3_client.delete_object(
    #             Bucket=self.bucket_name,
    #             Key=f"{self.user_prefix}{file_name}"
    #         )
            
    #         # Update storage usage
    #         storage = UserStorage.objects.get(user=self.user)
    #         storage.storage_used = max(0, storage.storage_used - file_size)
    #         storage.save()
            
    #         return True
    #     except Exception as e:
    #         raise Exception(f"Error deleting file: {str(e)}")
        
    # def delete_file(self, file_name):
    #     """Delete file from user's S3 directory"""
    #     try:
    #         s3_key = f"{self.user_prefix}{file_name}"
            
    #         # Verify file belongs to user
    #         try:
    #             response = self.s3_client.head_object(
    #                 Bucket=self.bucket_name,
    #                 Key=s3_key
    #             )
    #             if response['Metadata'].get('user_id') != str(self.user.id):
    #                 raise Exception("Unauthorized access to file")
                
    #             file_size = response['ContentLength']
    #         except self.s3_client.exceptions.ClientError:
    #             raise Exception("File not found")

    #         # Delete file
    #         self.s3_client.delete_object(
    #             Bucket=self.bucket_name,
    #             Key=s3_key
    #         )
            
    #         # Update storage usage
    #         storage = UserStorage.objects.get(user=self.user)
    #         storage.storage_used = max(0, storage.storage_used - file_size)
    #         storage.save()
            
    #         return True
    #     except Exception as e:
    #         raise Exception(f"Error deleting file: {str(e)}")
        
    def generate_download_url(self, s3_key, expires_in=3600):
        """
        Generate a download URL for a file in S3
        
        Args:
            s3_key (str): The S3 key of the file
            expires_in (int): Number of seconds until the URL expires
            
        Returns:
            str: The download URL
        """
        try:
            params = {
                'Bucket': self.bucket_name,
                'Key': s3_key,
                'ResponseContentDisposition': f'attachment; filename="{s3_key.split("/")[-1]}"'
            }
            
            url = self.s3_client.generate_presigned_url(
                ClientMethod='get_object',
                Params=params,
                ExpiresIn=expires_in
            )
            
            return url
        except Exception as e:
            logger.exception(f"Error generating download URL for {s3_key}: {str(e)}")
            raise Exception(f"Could not generate URL: {str(e)}")

    def file_exists(self, s3_key):
        """Check if a file exists in S3"""
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except self.s3_client.exceptions.NoSuchKey:
            return False
        except Exception as e:
            print(f"Error checking if file exists in S3: {str(e)}")
            return False
    
    def delete_file(self, s3_key):
        """Delete file with accurate size tracking"""
        try:
            # Get file size before deletion for storage update
            file_size = 0
            try:
                response = self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
                file_size = response['ContentLength']
            except self.s3_client.exceptions.NoSuchKey:
                logger.warning(f"[Delete] File not found in S3: {s3_key}")
                return True  # Consider it successful if file doesn't exist
            
            # Delete the file
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            # Update storage usage
            if file_size > 0:
                storage, created = UserStorage.objects.get_or_create(
                    user=self.user,
                    defaults={'storage_used': 0, 'storage_limit': 5368709120}
                )
                
                storage.storage_used = max(0, storage.storage_used - file_size)
                storage.save(update_fields=['storage_used'])
                
                logger.info(f"[Delete] User {self.user.id} deleted file {s3_key} ({file_size} bytes)")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file from S3: {str(e)}")
            raise Exception(f"Error deleting file: {str(e)}")

    
    def list_user_files_with_details(self):
        """List all files for user with details for debugging"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.user_prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                    })
            
            return files
        except Exception as e:
            print(f"Error listing user files: {str(e)}")
            return []

    def clean_orphaned_files(self, dry_run=True):
        """Clean up orphaned S3 files for this user"""
        try:
            from file_management.models import UserFile
            
            # Get valid S3 keys from database
            valid_keys = set()
            for user_file in UserFile.objects.filter(user=self.user):
                if user_file.s3_key:
                    valid_keys.add(user_file.s3_key)
                if user_file.file and user_file.file.name:
                    valid_keys.add(user_file.file.name)
            
            # List all S3 objects in user prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            orphaned_files = []
            total_orphaned_size = 0
            
            for page in paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=self.user_prefix
            ):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        s3_key = obj['Key']
                        if s3_key not in valid_keys and not any(key in s3_key for key in valid_keys):
                            orphaned_files.append({
                                'key': s3_key,
                                'size': obj['Size'],
                                'last_modified': obj['LastModified']
                            })
                            total_orphaned_size += obj['Size']
            
            logger.info(f"[Orphan Cleanup] Found {len(orphaned_files)} orphaned files ({total_orphaned_size} bytes)")
            
            if not dry_run and orphaned_files:
                # Actually delete the orphaned files
                deleted_count = 0
                for orphan in orphaned_files:
                    try:
                        self.s3_client.delete_object(
                            Bucket=self.bucket_name,
                            Key=orphan['key']
                        )
                        deleted_count += 1
                        logger.info(f"[Orphan Cleanup] Deleted: {orphan['key']}")
                    except Exception as e:
                        logger.error(f"[Orphan Cleanup] Failed to delete {orphan['key']}: {e}")
                
                logger.info(f"[Orphan Cleanup] Deleted {deleted_count}/{len(orphaned_files)} orphaned files")
            
            return {
                'orphaned_files': orphaned_files,
                'total_size': total_orphaned_size,
                'deleted': not dry_run
            }
            
        except Exception as e:
            logger.error(f"[Orphan Cleanup] Error cleaning orphaned files for user {self.user.id}: {e}")
            return {'error': str(e)}
        


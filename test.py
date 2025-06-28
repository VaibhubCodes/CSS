from file_management.models import UserFile
import boto3
from django.conf import settings

# Check the last few uploaded files
recent_files = UserFile.objects.order_by('-id')[:5]

print("=== Recent Files Debug ===")
for file in recent_files:
    print(f"\nFile ID: {file.id}")
    print(f"Original filename: {file.original_filename}")
    print(f"File field: {file.file.name}")
    print(f"S3 key: {file.s3_key}")
    print(f"File type: {file.file_type}")
    print(f"User: {file.user}")

# Test S3 client connection
print("\n=== Testing S3 Connection ===")
try:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )
    
    # List some objects in bucket
    response = s3_client.list_objects_v2(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        MaxKeys=10
    )
    
    print(f"S3 Connection successful!")
    print(f"Bucket: {settings.AWS_STORAGE_BUCKET_NAME}")
    print(f"Objects found: {response.get('KeyCount', 0)}")
    
    if 'Contents' in response:
        print("Sample objects:")
        for obj in response['Contents'][:5]:
            print(f"  - {obj['Key']} (Size: {obj['Size']} bytes)")
            
except Exception as e:
    print(f"S3 Connection error: {str(e)}")
from django.http import JsonResponse
from .utils import S3StorageManager
from django.contrib.auth.decorators import login_required
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from .models import UserStorage, AdminAccessLog
from .serializers import (
    StorageInfoSerializer, StorageAnalyticsSerializer,
    AdminAccessLogSerializer, StorageOptimizationSerializer
)

from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncMonth
from file_management.models import UserFile, FileCategory
# @login_required
# def get_storage_info(request):
#     try:
#         storage_manager = S3StorageManager(request.user)
#         storage_info = storage_manager.get_user_storage_info()
        
#         # Convert bytes to more readable format
#         def format_size(size):
#             for unit in ['B', 'KB', 'MB', 'GB']:
#                 if size < 1024:
#                     return f"{size:.2f} {unit}"
#                 size /= 1024
#             return f"{size:.2f} TB"
        
#         return JsonResponse({
#             'used': format_size(storage_info['used']),
#             'limit': format_size(storage_info['limit']),
#             'available': format_size(storage_info['available']),
#             'percentage_used': f"{storage_info['percentage_used']:.2f}%",
#             'raw': {
#                 'used': storage_info['used'],
#                 'limit': storage_info['limit'],
#                 'available': storage_info['available']
#             }
#         })
#     except Exception as e:
#         return JsonResponse({
#             'error': str(e)
#         }, status=500)
    


class StorageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = StorageInfoSerializer

    def get_queryset(self):
        return UserStorage.objects.filter(user=self.request.user)

    def get_object(self):
        storage = self.get_queryset().first()
        if not storage:
            # Create missing storage record
            storage, created = UserStorage.objects.get_or_create(
                user=self.request.user,
                defaults={
                    'storage_used': 0,
                    'storage_limit': 5368709120  # 5GB default
                }
            )
            if created:
                print(f"[StorageViewSet] Created missing UserStorage for user {self.request.user.email}")
                # Update storage limit based on subscription if available
                try:
                    storage.update_from_subscription()
                except Exception as e:
                    print(f"[StorageViewSet] Could not update subscription for {self.request.user.email}: {e}")
        return storage

    def list(self, request):
        storage = self.get_object()
        if not storage:
            return Response({'error': 'Storage not found'}, 
                        status=status.HTTP_404_NOT_FOUND)
        
        # Update storage limit from subscription if needed
        storage.update_from_subscription()
        
        # Get accurate storage info
        storage_manager = S3StorageManager(request.user)
        try:
            storage_info = storage_manager.get_user_storage_info()
        except Exception as e:
            print(f"Error getting storage info for user {request.user.id}: {e}")
            storage_info = {
                'used': storage.storage_used,
                'limit': storage.storage_limit,
                'available': storage.get_available_storage(),
                'percentage_used': storage.get_usage_percentage(),
                'error': 'Could not validate with S3'
            }
        
        serializer = self.get_serializer(storage)
        data = serializer.data
        
        # Add validation info
        data['validation'] = {
            'db_size': storage_info.get('db_size', 0),
            's3_size': storage_info.get('s3_size', 0),
            'validated_size': storage_info.get('used', 0),
            'method': storage_info.get('validation_method', 'database_primary')
        }
        
        # Add subscription info for frontend
        try:
            from payments.utils import get_user_subscription_info
            subscription_info = get_user_subscription_info(request.user)
            data['subscription_info'] = subscription_info
        except ImportError:
            data['subscription_info'] = {'is_sparkle': False}
        
        return Response(data)

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """
        Enhanced analytics with sparkle-specific features
        """
        user = self.request.user
        
        # Get subscription info for sparkle features
        try:
            from payments.utils import get_user_subscription_info
            subscription_info = get_user_subscription_info(user)
            is_sparkle = subscription_info.get('is_sparkle', False)
        except ImportError:
            is_sparkle = False
        
        # 1. Storage Overview
        try:
            storage = UserStorage.objects.get(user=user)
        except UserStorage.DoesNotExist:
            # Create missing storage record
            storage, created = UserStorage.objects.get_or_create(
                user=user,
                defaults={
                    'storage_used': 0,
                    'storage_limit': 5368709120  # 5GB default
                }
            )
            if created:
                print(f"[StorageViewSet.analytics] Created missing UserStorage for user {user.email}")
        
        storage.update_from_subscription()  # Ensure up-to-date limits
        
        storage_overview = {
            'used': storage.storage_used,
            'limit': storage.storage_limit,
            'percentage_used': storage.get_usage_percentage(),
            'percentage_left': 100 - storage.get_usage_percentage(),
            'is_sparkle': is_sparkle
        }

        # 2. Storage Breakdown by Category
        category_usage = UserFile.objects.filter(user=user)\
            .values('category__name')\
            .annotate(total_size=Sum('file_size'))\
            .order_by('-total_size')

        storage_breakdown = [
            {'category': item['category__name'] or 'Uncategorized', 'size': item['total_size']}
            for item in category_usage
        ]

        # 3. Enhanced Monthly Trends (more detailed for sparkle users)
        months_back = 12 if is_sparkle else 6
        start_date = timezone.now() - timedelta(days=months_back*30)
        
        monthly_data = UserFile.objects.filter(user=user, upload_date__gte=start_date)\
            .annotate(month=TruncMonth('upload_date'))\
            .values('month', 'category__name')\
            .annotate(count=Count('id'), total_size=Sum('file_size'))\
            .order_by('month')

        # Process trends data
        trends = {}
        for item in monthly_data:
            category = item['category__name'] or 'Uncategorized'
            if category not in trends:
                trends[category] = []
            
            trends[category].append({
                'month': item['month'].strftime('%Y-%m-%d'),
                'month_short': item['month'].strftime('%b'),
                'count': item['count'],
                'size': item['total_size'] if is_sparkle else None  # Size data only for sparkle
            })

        # 4. Sparkle-exclusive analytics
        sparkle_analytics = {}
        if is_sparkle:
            # File type distribution
            file_types = UserFile.objects.filter(user=user)\
                .values('file_type')\
                .annotate(count=Count('id'), total_size=Sum('file_size'))\
                .order_by('-total_size')[:10]
            
            sparkle_analytics = {
                'file_types': list(file_types),
                'total_files': UserFile.objects.filter(user=user).count(),
                'average_file_size': UserFile.objects.filter(user=user).aggregate(
                    avg_size= Avg('file_size')
                )['avg_size'] or 0,
            }

        response_data = {
            'storage_overview': storage_overview,
            'storage_breakdown': storage_breakdown,
            'monthly_trends': trends,
            'is_sparkle': is_sparkle,
            'sparkle_analytics': sparkle_analytics if is_sparkle else None
        }

        return Response(response_data)

    @action(detail=False, methods=['get'])
    def optimization(self, request):
        """
        Enhanced storage optimization with sparkle-specific features
        """
        try:
            from payments.utils import get_user_subscription_info
            subscription_info = get_user_subscription_info(request.user)
            is_sparkle = subscription_info.get('is_sparkle', False)
        except ImportError:
            is_sparkle = False

        files = UserFile.objects.filter(user=request.user)
        
        # Basic optimization (all users)
        large_files = files.filter(
            file_size__gt=100*1024*1024  # >100MB
        ).values('id', 'original_filename', 'file_size')
        
        # Enhanced optimization for sparkle users
        if is_sparkle:
            # More detailed duplicate detection
            duplicates = files.values(
                'file_size', 'file_type', 'file_hash'  # Assuming you have file_hash
            ).annotate(
                count=Count('id')
            ).filter(count__gt=1)
            
            # Detailed old files analysis
            six_months_ago = timezone.now() - timedelta(days=180)
            one_year_ago = timezone.now() - timedelta(days=365)
            
            old_files = {
                'six_months': files.filter(upload_date__lt=six_months_ago).count(),
                'one_year': files.filter(upload_date__lt=one_year_ago).count(),
                'details': files.filter(upload_date__lt=six_months_ago).values(
                    'id', 'original_filename', 'upload_date', 'file_size'
                )[:50]  # Limit for performance
            }
            
            recommendations = [
                'Consider compressing large files to save space',
                'Remove duplicate files to optimize storage',
                'Archive old files to external storage',
                'Use appropriate file formats for your content',
                'Regularly review and clean up unused files',
                'Consider upgrading storage if consistently near limit'
            ]
        else:
            # Basic duplicate detection
            duplicates = files.values(
                'file_size', 'file_type'
            ).annotate(
                count=Count('id')
            ).filter(count__gt=1)
            
            six_months_ago = timezone.now() - timedelta(days=180)
            old_files = files.filter(upload_date__lt=six_months_ago).values(
                'id', 'original_filename', 'upload_date'
            )[:10]  # Limited for basic users
            
            recommendations = [
                'Consider upgrading to Sparkle plan for advanced optimization',
                'Remove large files you no longer need',
                'Delete duplicate files'
            ]
        
        # Calculate potential savings
        potential_savings = sum(f['file_size'] for f in large_files)
        if duplicates:
            duplicate_savings = sum(
                d['file_size'] * (d['count'] - 1) 
                for d in duplicates if d['file_size']
            )
            potential_savings += duplicate_savings
        
        data = {
            'large_files': list(large_files),
            'duplicate_files': list(duplicates),
            'old_files': old_files,
            'potential_savings': potential_savings,
            'recommendations': recommendations,
            'is_sparkle': is_sparkle
        }
        
        serializer = StorageOptimizationSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def recalculate(self, request):
        """Manually recalculate storage usage"""
        try:
            storage_manager = S3StorageManager(request.user)
            storage_info = storage_manager.get_user_storage_info()
            
            return Response({
                'success': True,
                'message': 'Storage recalculated successfully',
                'storage_info': storage_info
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def clean_orphans(self, request):
        """Clean orphaned S3 files"""
        try:
            storage_manager = S3StorageManager(request.user)
            dry_run = request.data.get('dry_run', True)
            
            orphan_info = storage_manager.clean_orphaned_files(dry_run=dry_run)
            
            return Response({
                'success': True,
                'orphan_info': orphan_info,
                'dry_run': dry_run
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminAccessLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = AdminAccessLogSerializer
    queryset = AdminAccessLog.objects.all()

    def get_queryset(self):
        queryset = AdminAccessLog.objects.all()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(
                access_time__range=[start_date, end_date]
            )
        
        # Filter by admin user
        admin_user = self.request.query_params.get('admin_user')
        if admin_user:
            queryset = queryset.filter(admin_user__username=admin_user)
        
        # Filter by access type
        access_type = self.request.query_params.get('access_type')
        if access_type:
            queryset = queryset.filter(access_type=access_type)
        
        return queryset.order_by('-access_time')
    

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_storage_info(request):
    try:
        storage_manager = S3StorageManager(request.user)
        storage_info = storage_manager.get_user_storage_info()
        
        # Convert bytes to more readable format
        def format_size(size):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    return f"{size:.2f} {unit}"
                size /= 1024
            return f"{size:.2f} TB"
        
        return Response({
            'used': format_size(storage_info['used']),
            'limit': format_size(storage_info['limit']),
            'available': format_size(storage_info['available']),
            'percentage_used': f"{storage_info['percentage_used']:.2f}%",
            'raw': {
                'used': storage_info['used'],
                'limit': storage_info['limit'],
                'available': storage_info['available'],
                'percentage_used': storage_info['percentage_used']
            }
        })
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

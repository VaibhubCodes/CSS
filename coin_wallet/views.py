from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import CoinWallet, CoinTransaction
from .serializers import (
    CoinWalletSerializer, CoinTransactionSerializer, CoinBalanceSerializer,
    CoinRedemptionSerializer, CoinEarningEstimateSerializer
)
from storage_management.models import UserStorage
from file_management.models import UserFile
import math
import logging
from django.db import models

logger = logging.getLogger(__name__)

# --- API Views ---

class CoinWalletViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for wallet information and transaction history"""
    permission_classes = [IsAuthenticated]
    serializer_class = CoinWalletSerializer
    
    def get_queryset(self):
        return CoinWallet.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Get the current user's wallet or create one if it doesn't exist"""
        wallet, created = CoinWallet.objects.get_or_create(user=self.request.user)
        return wallet
    
    def list(self, request):
        """Return the user's wallet info"""
        wallet = self.get_object()
        serializer = self.get_serializer(wallet)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def balance(self, request):
        """Simple endpoint to fetch just the coin balance"""
        wallet = self.get_object()
        serializer = CoinBalanceSerializer({'balance': wallet.balance})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def transactions(self, request):
        """Get transaction history"""
        wallet = self.get_object()
        transactions = CoinTransaction.objects.filter(wallet=wallet)
        
        # Optional filtering
        transaction_type = request.query_params.get('type')
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)
            
        # Pagination - simple implementation
        page_size = int(request.query_params.get('page_size', 20))
        page = int(request.query_params.get('page', 1))
        start = (page - 1) * page_size
        end = page * page_size
        
        transactions_page = transactions[start:end]
        serializer = CoinTransactionSerializer(transactions_page, many=True)
        
        return Response({
            'results': serializer.data,
            'count': transactions.count(),
            'page': page,
            'page_size': page_size
        })
    
    @action(detail=False, methods=['post'])
    def redeem(self, request):
        """Redeem coins for benefits"""
        wallet = self.get_object()
        serializer = CoinRedemptionSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        amount = serializer.validated_data['amount']
        redemption_type = serializer.validated_data['redemption_type']
        
        # Check if user has enough coins
        if wallet.balance < amount:
            return Response(
                {'error': 'Insufficient coins. You need more coins for this redemption.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process redemption based on type
        with transaction.atomic():
            if redemption_type == 'storage':
                # Increase storage by 1GB per 10 coins
                storage_increase_bytes = (amount // 10) * (1024 * 1024 * 1024)  # 1GB in bytes
                
                if storage_increase_bytes <= 0:
                    return Response(
                        {'error': 'You need at least 10 coins to increase storage.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Update user's storage limit
                user_storage = UserStorage.objects.get(user=request.user)
                user_storage.storage_limit += storage_increase_bytes
                user_storage.save()
                
                # Deduct coins
                success = wallet.use_coins(
                    amount=amount,
                    transaction_type='redemption',
                    source=f'Storage increase: {storage_increase_bytes/(1024*1024*1024):.2f} GB'
                )
                
                if not success:
                    raise Exception("Failed to deduct coins from wallet")
                
                return Response({
                    'success': True,
                    'message': f'Successfully increased storage by {storage_increase_bytes/(1024*1024*1024):.2f} GB',
                    'coins_used': amount,
                    'remaining_balance': wallet.balance
                })
                
            elif redemption_type == 'premium':
                # Implement premium feature redemption here
                # This is a placeholder - actual implementation would depend on your premium features
                success = wallet.use_coins(
                    amount=amount,
                    transaction_type='redemption',
                    source=f'Premium features: {amount} coins'
                )
                
                if not success:
                    raise Exception("Failed to deduct coins from wallet")
                
                return Response({
                    'success': True,
                    'message': f'Successfully redeemed {amount} coins for premium features',
                    'coins_used': amount,
                    'remaining_balance': wallet.balance
                })
            
            return Response(
                {'error': 'Invalid redemption type'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def estimate(self, request):
        """Estimate coins to be earned for a file upload"""
        serializer = CoinEarningEstimateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Return the estimated coins
        return Response(serializer.data)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def award_coins_for_file(request, file_id):
    """Award coins for a specific file upload"""
    try:
        # Verify the file belongs to the user
        user_file = UserFile.objects.get(id=file_id, user=request.user)
        
        # Calculate coins (1 coin per MB)
        file_size_mb = math.ceil(user_file.file_size / (1024 * 1024))
        if file_size_mb < 1:
            file_size_mb = 1  # Minimum 1 coin per file
        
        # Get or create the user's wallet
        wallet, created = CoinWallet.objects.get_or_create(user=request.user)
        
        # Check if coins were already awarded for this file
        existing_transaction = CoinTransaction.objects.filter(
            wallet=wallet,
            transaction_type='upload',
            related_file=user_file
        ).first()
        
        if existing_transaction:
            return Response({
                'success': False,
                'message': 'Coins were already awarded for this file',
                'coins_awarded': existing_transaction.amount,
                'current_balance': wallet.balance
            })
        
        # Award coins
        wallet.add_coins(
            amount=file_size_mb,
            transaction_type='upload',
            source=f'File upload: {user_file.original_filename}'
        )
        
        # Update the transaction with the related file
        transaction = CoinTransaction.objects.filter(
            wallet=wallet,
            transaction_type='upload'
        ).latest('created_at')
        transaction.related_file = user_file
        transaction.save()
        
        return Response({
            'success': True,
            'message': f'Successfully awarded {file_size_mb} coins for file upload',
            'coins_awarded': file_size_mb,
            'current_balance': wallet.balance
        })
        
    except UserFile.DoesNotExist:
        return Response(
            {'error': 'File not found or does not belong to the user'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.exception(f"Error awarding coins for file {file_id}: {str(e)}")
        return Response(
            {'error': 'An error occurred while awarding coins'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mobile_wallet_info(request):
    """Mobile-friendly API endpoint for React Native integration"""
    try:
        # Get or create user's wallet
        wallet, created = CoinWallet.objects.get_or_create(user=request.user)
        
        # Get transaction stats
        earned = CoinTransaction.objects.filter(wallet=wallet, amount__gt=0).aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        
        spent = CoinTransaction.objects.filter(wallet=wallet, amount__lt=0).aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        
        # Get recent transactions (limited to 5)
        recent_transactions = CoinTransaction.objects.filter(wallet=wallet).order_by('-created_at')[:5]
        
        # Format response
        response_data = {
            'success': True,
            'data': {
                'balance': wallet.balance,
                'stats': {
                    'earned': earned,
                    'spent': abs(spent) if spent else 0,
                },
                'recent_transactions': [
                    {
                        'id': t.id,
                        'amount': t.amount,
                        'transaction_type': t.get_transaction_type_display(),
                        'created_at': t.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'source': t.source
                    } for t in recent_transactions
                ]
            }
        }
        
        return Response(response_data)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- Template Views ---

def coin_wallet_dashboard(request):
    """Web template view for coin wallet dashboard"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Get or create user's wallet
    wallet, created = CoinWallet.objects.get_or_create(user=request.user)
    
    # Get recent transactions
    transactions = CoinTransaction.objects.filter(wallet=wallet).order_by('-created_at')[:10]
    
    # Stats
    earnings = CoinTransaction.objects.filter(wallet=wallet, amount__gt=0).values('transaction_type')\
        .annotate(total=models.Sum('amount'))
    
    redemptions = CoinTransaction.objects.filter(wallet=wallet, amount__lt=0).values('transaction_type')\
        .annotate(total=models.Sum('amount'))
    
    context = {
        'wallet': wallet,
        'transactions': transactions,
        'earnings': earnings,
        'redemptions': redemptions
    }
    
    return render(request, 'coin_wallet/dashboard.html', context)

def redeem_coins(request):
    """Web template view for coin redemption page"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Get user's wallet
    wallet, created = CoinWallet.objects.get_or_create(user=request.user)
    
    # Handle redemption submission
    if request.method == 'POST':
        redemption_type = request.POST.get('redemption_type')
        amount = int(request.POST.get('amount', 0))
        
        # Simple validation
        if amount <= 0:
            return render(request, 'coin_wallet/redeem.html', {
                'wallet': wallet,
                'error': 'Amount must be positive'
            })
        
        if wallet.balance < amount:
            return render(request, 'coin_wallet/redeem.html', {
                'wallet': wallet,
                'error': 'Insufficient balance'
            })
        
        # Process redemption
        success = False
        message = ''
        
        if redemption_type == 'storage':
            # Increase storage by 1GB per 10 coins
            storage_increase_bytes = (amount // 10) * (1024 * 1024 * 1024)
            
            if storage_increase_bytes <= 0:
                return render(request, 'coin_wallet/redeem.html', {
                    'wallet': wallet,
                    'error': 'You need at least 10 coins to increase storage'
                })
            
            # Update user's storage limit
            user_storage = UserStorage.objects.get(user=request.user)
            user_storage.storage_limit += storage_increase_bytes
            user_storage.save()
            
            # Deduct coins
            success = wallet.use_coins(
                amount=amount,
                transaction_type='redemption',
                source=f'Storage increase: {storage_increase_bytes/(1024*1024*1024):.2f} GB'
            )
            
            message = f'Successfully increased storage by {storage_increase_bytes/(1024*1024*1024):.2f} GB'
        
        elif redemption_type == 'premium':
            # Placeholder for premium feature redemption
            success = wallet.use_coins(
                amount=amount,
                transaction_type='redemption',
                source=f'Premium features: {amount} coins'
            )
            
            message = f'Successfully redeemed {amount} coins for premium features'
        
        if success:
            return render(request, 'coin_wallet/redeem.html', {
                'wallet': wallet,
                'success': True,
                'message': message
            })
        else:
            return render(request, 'coin_wallet/redeem.html', {
                'wallet': wallet,
                'error': 'Redemption failed'
            })
    
    return render(request, 'coin_wallet/redeem.html', {'wallet': wallet})

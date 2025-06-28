import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from .models import SubscriptionPlan, Subscription, PaymentTransaction
from .serializers import (
    SubscriptionPlanSerializer, SubscriptionSerializer,
    PaymentTransactionSerializer, RazorpayOrderSerializer,
    PaymentVerificationSerializer
)
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils.decorators import method_decorator
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def get_subscription_plans(request):
    """Display all active subscription plans"""
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('sort_order', 'price')
    return render(request, 'plans/subscription_plans.html', {'plans': plans})

def create_subscription(request, plan_code):
    """Create subscription using plan_code instead of plan_type"""
    if not request.user.is_authenticated:
        return redirect('login')

    plan = get_object_or_404(SubscriptionPlan, plan_code=plan_code, is_active=True)
    amount = plan.price_paise  # Already in paise

    # Create Razorpay Order
    order_data = {
        'amount': amount,
        'currency': 'INR',
        'receipt': f'order_rcptid_{datetime.now().timestamp()}',
        'notes': {
            'plan_code': plan_code,
            'user_email': request.user.email,
            'plan_name': plan.name
        }
    }

    order = client.order.create(data=order_data)

    # Create subscription record
    subscription = Subscription.objects.create(
        user=request.user,
        plan=plan,
        razorpay_order_id=order['id'],
        status='pending',
        paid_amount=plan.price
    )

    # Create payment transaction record
    PaymentTransaction.objects.create(
        subscription=subscription,
        amount=plan.price,
        status='pending'
    )

    context = {
        'order_id': order['id'],
        'amount': amount,
        'currency': 'INR',
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'user_email': request.user.email,
        'plan_type': plan.name,
        'callback_url': request.build_absolute_uri(reverse('payment_callback'))
    }

    return render(request, 'plans/checkout.html', context)


@csrf_exempt
def payment_callback(request):
    """Handle payment callback and activate subscription"""
    if request.method == "POST":
        payment_id = request.POST.get('razorpay_payment_id', '')
        order_id = request.POST.get('razorpay_order_id', '')
        signature = request.POST.get('razorpay_signature', '')

        try:
            # Verify payment signature
            client.utility.verify_payment_signature({
                'razorpay_payment_id': payment_id,
                'razorpay_order_id': order_id,
                'razorpay_signature': signature
            })

            # Update subscription and payment status
            subscription = Subscription.objects.get(razorpay_order_id=order_id)
            subscription.razorpay_payment_id = payment_id
            subscription.razorpay_signature = signature
            subscription.status = 'active'
            subscription.activated_at = timezone.now()
            subscription.valid_till = timezone.now() + timedelta(days=subscription.plan.duration_days)
            subscription.save()

            # Update user's storage limit based on new plan
            from storage_management.models import UserStorage
            user_storage, created = UserStorage.objects.get_or_create(user=subscription.user)
            user_storage.storage_limit = subscription.plan.storage_bytes
            user_storage.save()

            # Update payment transaction
            transaction = PaymentTransaction.objects.get(subscription=subscription)
            transaction.status = 'completed'
            transaction.save()

            return JsonResponse({'status': 'success'})

        except Exception as e:
            return JsonResponse({'status': 'failed', 'error': str(e)})

    return JsonResponse({'status': 'invalid request'})




class SubscriptionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SubscriptionSerializer

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def plans(self, request):
        """Get all available subscription plans"""
        plans = SubscriptionPlan.objects.filter(is_active=True).order_by('sort_order', 'price')
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current active subscription"""
        subscription = Subscription.objects.filter(
            user=request.user,
            status='active'
        ).first()
        if subscription:
            serializer = self.get_serializer(subscription)
            return Response(serializer.data)
        return Response({'message': 'No active subscription'}, 
                       status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def create_order(self, request):
        """Create Razorpay order for subscription"""
        plan_id = request.data.get('plan_id')
        if not plan_id:
            return Response({'error': 'Plan ID is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)

        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({'error': 'Invalid or inactive plan'}, 
                          status=status.HTTP_400_BAD_REQUEST)

        # Create Razorpay Order
        order_data = {
            'amount': plan.price_paise,
            'currency': 'INR',
            'receipt': f'order_rcptid_{timezone.now().timestamp()}',
            'notes': {
                'plan_code': plan.plan_code,
                'user_email': request.user.email,
                'plan_name': plan.name
            }
        }

        try:
            order = client.order.create(data=order_data)

            # Create subscription record
            subscription = Subscription.objects.create(
                user=request.user,
                plan=plan,
                razorpay_order_id=order['id'],
                status='pending',
                paid_amount=plan.price
            )

            # Create payment transaction record
            PaymentTransaction.objects.create(
                subscription=subscription,
                amount=plan.price,
                status='pending'
            )

            response_data = {
                'order_id': order['id'],
                'amount': order['amount'],
                'currency': order['currency'],
                'subscription_id': subscription.id
            }
            serializer = RazorpayOrderSerializer(response_data)
            return Response(serializer.data)

        except Exception as e:
            return Response({'error': str(e)}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    serializer = PaymentVerificationSerializer(data=request.data)
    if serializer.is_valid():
        try:
            # Verify payment signature
            params_dict = {
                'razorpay_payment_id': serializer.validated_data['razorpay_payment_id'],
                'razorpay_order_id': serializer.validated_data['razorpay_order_id'],
                'razorpay_signature': serializer.validated_data['razorpay_signature']
            }
            client.utility.verify_payment_signature(params_dict)

            # Update subscription and payment status
            subscription = Subscription.objects.get(
                razorpay_order_id=serializer.validated_data['razorpay_order_id']
            )
            subscription.razorpay_payment_id = serializer.validated_data['razorpay_payment_id']
            subscription.razorpay_signature = serializer.validated_data['razorpay_signature']
            subscription.status = 'active'
            subscription.valid_till = timezone.now() + timedelta(days=30)
            subscription.save()

            # Update payment transaction
            transaction = PaymentTransaction.objects.get(subscription=subscription)
            transaction.status = 'completed'
            transaction.save()

            return Response({
                'message': 'Payment verified successfully',
                'subscription': SubscriptionSerializer(subscription).data
            })

        except Exception as e:
            return Response({'error': str(e)}, 
                          status=status.HTTP_400_BAD_REQUEST)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PaymentTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentTransactionSerializer

    def get_queryset(self):
        return PaymentTransaction.objects.filter(
            subscription__user=self.request.user
        )
    


@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mobile_subscription_plans(request):
    """Mobile API endpoint for subscription plans"""
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('sort_order', 'price')
    serializer = SubscriptionPlanSerializer(plans, many=True)
    return Response(serializer.data)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_create_subscription(request):
    """Mobile API endpoint for creating subscriptions"""
    plan_id = request.data.get('plan_id')
    
    if not plan_id:
        return Response({
            'success': False,
            'error': 'Plan ID is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
    except SubscriptionPlan.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Invalid or inactive plan'
        }, status=status.HTTP_400_BAD_REQUEST)

    amount = plan.price_paise

    # Create Razorpay Order
    order_data = {
        'amount': amount,
        'currency': 'INR',
        'receipt': f'order_rcptid_{datetime.now().timestamp()}',
        'notes': {
            'plan_code': plan.plan_code,
            'user_email': request.user.email,
            'plan_name': plan.name
        }
    }

    try:
        order = client.order.create(data=order_data)
        
        # Create subscription record
        subscription = Subscription.objects.create(
            user=request.user,
            plan=plan,
            razorpay_order_id=order['id'],
            status='pending',
            paid_amount=plan.price
        )

        # Create payment transaction record
        PaymentTransaction.objects.create(
            subscription=subscription,
            amount=plan.price,
            status='pending'
        )

        return Response({
            'success': True,
            'order_id': order['id'],
            'amount': amount,
            'currency': 'INR',
            'key_id': settings.RAZORPAY_KEY_ID,
            'subscription_id': subscription.id,
            'plan_name': plan.name,
            'is_sparkle': plan.is_sparkle
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
from rest_framework.permissions import IsAdminUser


class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for subscription plans - read-only for regular users
    Admins can manage plans through Django admin
    """
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return SubscriptionPlan.objects.all()
        return SubscriptionPlan.objects.filter(is_active=True)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get only active plans for public consumption"""
        plans = SubscriptionPlan.objects.filter(is_active=True).order_by('sort_order', 'price')
        serializer = self.get_serializer(plans, many=True)
        return Response(serializer.data)

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_subscription_info(request):
    """
    Get comprehensive subscription information for the authenticated user
    Including sparkle status for frontend conditional rendering
    """
    from .utils import get_user_subscription_info, check_subscription_validity
    
    # Check if subscription is still valid
    check_subscription_validity(request.user)
    
    # Get subscription info
    subscription_info = get_user_subscription_info(request.user)
    
    return Response(subscription_info)




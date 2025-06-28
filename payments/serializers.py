from rest_framework import serializers
from .models import SubscriptionPlan, Subscription, PaymentTransaction

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    storage_bytes = serializers.ReadOnlyField()
    price_paise = serializers.ReadOnlyField()
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'plan_code', 'description', 'price', 
            'storage_gb', 'storage_bytes', 'is_sparkle', 'features',
            'duration_days', 'price_paise'
        ]

class SubscriptionSerializer(serializers.ModelSerializer):
    plan_details = SubscriptionPlanSerializer(source='plan', read_only=True)
    is_sparkle_subscription = serializers.ReadOnlyField()
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'plan', 'plan_details', 'status', 'created_at', 
            'activated_at', 'valid_till', 'paid_amount', 'is_sparkle_subscription'
        ]
        read_only_fields = ['status', 'activated_at', 'valid_till']

class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = ['id', 'amount', 'currency', 'status', 'created_at']
        read_only_fields = ['status', 'created_at']

class RazorpayOrderSerializer(serializers.Serializer):
    order_id = serializers.CharField()
    amount = serializers.IntegerField()
    currency = serializers.CharField()
    subscription_id = serializers.IntegerField()

class PaymentVerificationSerializer(serializers.Serializer):
    razorpay_payment_id = serializers.CharField()
    razorpay_order_id = serializers.CharField()
    razorpay_signature = serializers.CharField()

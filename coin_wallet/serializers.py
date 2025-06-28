from rest_framework import serializers
from .models import CoinWallet, CoinTransaction

class CoinWalletSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = CoinWallet
        fields = ['id', 'user', 'user_email', 'balance', 'created_at', 'updated_at']
        read_only_fields = ['user', 'balance', 'created_at', 'updated_at']

class CoinTransactionSerializer(serializers.ModelSerializer):
    wallet_user = serializers.EmailField(source='wallet.user.email', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    
    class Meta:
        model = CoinTransaction
        fields = [
            'id', 'wallet', 'wallet_user', 'amount', 'transaction_type',
            'transaction_type_display', 'source', 'related_file',
            'created_at', 'running_balance', 'notes'
        ]
        read_only_fields = ['wallet', 'created_at', 'running_balance']

class CoinBalanceSerializer(serializers.Serializer):
    """Simple serializer to show just the coin balance"""
    balance = serializers.IntegerField(read_only=True)
    
class CoinRedemptionSerializer(serializers.Serializer):
    """Serializer for coin redemption requests"""
    amount = serializers.IntegerField(min_value=1)
    redemption_type = serializers.ChoiceField(choices=[
        ('storage', 'Increase Storage'),
        ('premium', 'Premium Features')
    ])
    
class CoinEarningEstimateSerializer(serializers.Serializer):
    """Serializer to estimate coin earnings for a file upload"""
    file_size_bytes = serializers.IntegerField(min_value=1)
    estimated_coins = serializers.SerializerMethodField()
    
    def get_estimated_coins(self, obj):
        # Convert bytes to MB and round up to the nearest integer
        file_size_mb = obj['file_size_bytes'] / (1024 * 1024)
        return int(file_size_mb) + (1 if file_size_mb > int(file_size_mb) else 0) 
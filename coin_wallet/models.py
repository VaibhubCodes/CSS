from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from file_management.models import UserFile

class CoinWallet(models.Model):
    """Main wallet model to track available coins for each user"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    balance = models.IntegerField(default=0)  # Integer value, 1 coin per MB
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.email}'s Coin Wallet: {self.balance} coins"

    def add_coins(self, amount, transaction_type, source=None):
        """Add coins to wallet and create a transaction record"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        self.balance += amount
        self.save()
        
        # Create transaction record
        CoinTransaction.objects.create(
            wallet=self,
            amount=amount,
            transaction_type=transaction_type,
            source=source,
            running_balance=self.balance
        )
        return True
        
    def use_coins(self, amount, transaction_type, source=None):
        """Use (deduct) coins from wallet and create a transaction record"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
            
        if self.balance < amount:
            return False  # Insufficient balance
            
        self.balance -= amount
        self.save()
        
        # Create transaction record with negative amount
        CoinTransaction.objects.create(
            wallet=self,
            amount=-amount,  # Store as negative to indicate deduction
            transaction_type=transaction_type,
            source=source,
            running_balance=self.balance
        )
        return True

    class Meta:
        verbose_name = "Coin Wallet"
        verbose_name_plural = "Coin Wallets"


class CoinTransaction(models.Model):
    """Records all coin transactions: earnings, redemptions, etc."""
    TRANSACTION_TYPES = (
        ('upload', 'File Upload Reward'),
        ('referral', 'Referral Bonus'),
        ('admin', 'Admin Adjustment'),
        ('redemption', 'Coin Redemption'),
        ('purchase', 'Storage Purchase'),
        ('other', 'Other')
    )
    
    wallet = models.ForeignKey(CoinWallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.IntegerField()  # Positive for additions, negative for deductions
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    source = models.CharField(max_length=255, blank=True, null=True)  # File ID, transaction reference, etc.
    related_file = models.ForeignKey(UserFile, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    running_balance = models.IntegerField()  # Wallet balance after this transaction
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        if self.amount > 0:
            return f"+{self.amount} coins: {self.get_transaction_type_display()}"
        else:
            return f"{self.amount} coins: {self.get_transaction_type_display()}"
            
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Coin Transaction"
        verbose_name_plural = "Coin Transactions"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_coin_wallet(sender, instance, created, **kwargs):
    """Create a coin wallet for each new user"""
    if created:
        CoinWallet.objects.get_or_create(user=instance)

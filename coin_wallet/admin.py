
from django.contrib import admin
from .models import CoinWallet, CoinTransaction

class CoinTransactionInline(admin.TabularInline):
    model = CoinTransaction
    extra = 0
    readonly_fields = ('amount', 'transaction_type', 'source', 'related_file', 'created_at', 'running_balance', 'notes')
    fields = ('created_at', 'transaction_type', 'amount', 'running_balance', 'source')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(CoinWallet)
class CoinWalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'updated_at')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('user', 'balance', 'created_at', 'updated_at')
    inlines = [CoinTransactionInline]

@admin.register(CoinTransaction)
class CoinTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'amount', 'transaction_type', 'source', 'created_at', 'running_balance')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('wallet__user__email', 'source', 'notes')
    date_hierarchy = 'created_at'
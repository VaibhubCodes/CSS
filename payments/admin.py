from django.contrib import admin
from django.utils.html import format_html
from django.db import models
from django.forms import widgets
from .models import SubscriptionPlan, Subscription, PaymentTransaction

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    """
    Comprehensive admin interface for managing subscription plans
    """
    list_display = (
        'name', 'plan_code', 'formatted_price', 'storage_display', 
        'is_sparkle', 'is_active', 'sort_order', 'updated_at'
    )
    list_filter = ('is_active', 'is_sparkle', 'created_at')
    search_fields = ('name', 'plan_code', 'description')
    list_editable = ('is_active', 'sort_order')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'plan_code', 'description')
        }),
        ('Pricing & Storage', {
            'fields': ('price', 'storage_gb', 'duration_days')
        }),
        ('Features', {
            'fields': ('is_sparkle', 'features'),
            'description': 'Configure plan features and capabilities'
        }),
        ('Settings', {
            'fields': ('is_active', 'sort_order'),
            'classes': ('collapse',)
        })
    )
    
    # Custom form widget for features JSON field
    formfield_overrides = {
        models.JSONField: {'widget': widgets.Textarea(attrs={'rows': 4, 'cols': 60})},
    }
    
    def formatted_price(self, obj):
        return f"₹{obj.price}"
    formatted_price.short_description = 'Price'
    formatted_price.admin_order_field = 'price'
    
    def storage_display(self, obj):
        return f"{obj.storage_gb} GB"
    storage_display.short_description = 'Storage'
    storage_display.admin_order_field = 'storage_gb'
    
    def save_model(self, request, obj, form, change):
        # Auto-generate plan_code if not provided
        if not obj.plan_code:
            obj.plan_code = obj.name.lower().replace(' ', '_')
        super().save_model(request, obj, form, change)

class PaymentTransactionInline(admin.TabularInline):
    model = PaymentTransaction
    extra = 0
    readonly_fields = ('amount', 'currency', 'status', 'created_at')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """
    Enhanced subscription admin with plan management
    """
    list_display = (
        'user', 'plan_name', 'plan_sparkle_status', 'status', 
        'formatted_amount', 'created_at', 'valid_till'
    )
    list_filter = ('status', 'plan__is_sparkle', 'plan__name', 'created_at')
    search_fields = ('user__email', 'user__username', 'plan__name')
    readonly_fields = (
        'razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 
        'created_at', 'activated_at'
    )
    raw_id_fields = ('user',)
    
    fieldsets = (
        ('Subscription Details', {
            'fields': ('user', 'plan', 'status', 'paid_amount')
        }),
        ('Payment Information', {
            'fields': (
                'razorpay_order_id', 'razorpay_payment_id', 
                'razorpay_signature'
            ),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('created_at', 'activated_at', 'valid_till'),
            'classes': ('collapse',)
        }),
        ('Legacy', {
            'fields': ('legacy_plan',),
            'classes': ('collapse',),
            'description': 'For backward compatibility with old system'
        })
    )
    
    inlines = [PaymentTransactionInline]
    
    def plan_name(self, obj):
        return obj.plan.name if obj.plan else obj.legacy_plan
    plan_name.short_description = 'Plan'
    plan_name.admin_order_field = 'plan__name'
    
    def plan_sparkle_status(self, obj):
        if obj.plan:
            if obj.plan.is_sparkle:
                return format_html(
                    '<span style="color: #28a745; font-weight: bold;">✨ Sparkle</span>'
                )
            else:
                return format_html(
                    '<span style="color: #6c757d;">Basic</span>'
                )
        return 'Legacy'
    plan_sparkle_status.short_description = 'Plan Type'
    
    def formatted_amount(self, obj):
        return f"₹{obj.paid_amount}"
    formatted_amount.short_description = 'Amount Paid'
    formatted_amount.admin_order_field = 'paid_amount'

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('subscription__user__email', 'subscription__plan__name')
    readonly_fields = ('created_at',)
from django.contrib import admin
from .models import Brand, Coupon

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'brand', 'discount_type', 'discount_value', 'valid_till']
    list_filter = ['brand', 'discount_type', 'valid_till']
    search_fields = ['code']

# serializers.py

from rest_framework import serializers
from .models import Brand, Coupon

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name', 'logo']


class CouponSerializer(serializers.ModelSerializer):
    # read‐only nested brand for responses
    brand = BrandSerializer(read_only=True)
    # write‐only primary key field for creating/updating
    brand_id = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(),
        write_only=True,
        source='brand'
    )
    display_discount = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = [
            'id',
            'code',
            'brand',       # nested brand data in the response
            'brand_id',    # you POST this as the brand's ID
            'discount_type',
            'discount_value',
            'valid_till',
            'display_discount',
        ]

    def get_display_discount(self, obj):
        return obj.display_discount()

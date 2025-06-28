from django.db import models

class Brand(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='brand_logos/')

    def __str__(self):
        return self.name

class Coupon(models.Model):
    DISCOUNT_TYPES = (
        ('amount', 'Amount (₹)'),
        ('percentage', 'Percentage (%)'),
    )

    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='coupons')
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    valid_till = models.DateField()

    def __str__(self):
        return f"{self.code} - {self.brand.name}"

    def display_discount(self):
        if self.discount_type == 'amount':
            return f"₹{self.discount_value}"
        return f"{self.discount_value}%"

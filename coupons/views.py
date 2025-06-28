from rest_framework import viewsets
from .models import Brand, Coupon
from .serializers import BrandSerializer, CouponSerializer
from rest_framework.permissions import IsAuthenticatedOrReadOnly

class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class CouponViewSet(viewsets.ModelViewSet):
    queryset = Coupon.objects.select_related('brand').all()
    serializer_class = CouponSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

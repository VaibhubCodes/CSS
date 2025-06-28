from rest_framework.routers import DefaultRouter
from .views import BrandViewSet, CouponViewSet

router = DefaultRouter()
router.register(r'brands', BrandViewSet)
router.register(r'coupons', CouponViewSet)

urlpatterns = router.urls

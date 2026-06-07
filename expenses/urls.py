from rest_framework import routers
from .views import (
    ExpenseViewSet,
    CategoryViewSet,
    UserProfileViewSet,
    TelegramUserViewSet,
    RegularPaymentsViewSet,
)

router = routers.DefaultRouter()
router.register("expenses", ExpenseViewSet, basename="expense")
router.register("categories", CategoryViewSet)
router.register("user-profile", UserProfileViewSet, basename="user-profile")
router.register("telegram-user", TelegramUserViewSet, basename="telegram-user")
router.register("regular-payments", RegularPaymentsViewSet, basename="regular-payments")

urlpatterns = router.urls

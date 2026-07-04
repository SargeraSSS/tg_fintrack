from rest_framework import routers
from .views import (
    ExpenseViewSet,
    CategoryViewSet,
    UserProfileViewSet,
    TelegramUserViewSet,
    RegularPaymentsViewSet,
    IncomeViewSet,
)
from django.urls import path
from . import views

router = routers.DefaultRouter()
router.register("expenses", ExpenseViewSet, basename="expense")
router.register("income", IncomeViewSet, basename="income")
router.register("categories", CategoryViewSet)
router.register("user-profile", UserProfileViewSet, basename="user-profile")
router.register("telegram-user", TelegramUserViewSet, basename="telegram-user")
router.register("regular-payments", RegularPaymentsViewSet, basename="regular-payments")

urlpatterns = router.urls + [
    path("get-token/<int:telegram_id>/", views.get_token_by_telegram_id),
    path("stats/", views.get_monthly_stats),
    path("history/", views.get_history),
    path("set-currency/", views.set_currency),
    path("set-savings-goal/", views.set_savings_goal),
    path("get-profile/", views.get_profile),
    path("all-telegram-ids/", views.get_telegram_id),
    path("process-regular-payments/", views.regelar_payment_automization),
    path("notification-status/", views.notification_status),
]

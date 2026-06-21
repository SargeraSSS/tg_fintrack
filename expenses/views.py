from rest_framework import viewsets
from .models import Category, Expense, UserProfile, TelegramUser, RegularPayments
from .serializers import (
    CategorySerializer,
    ExpenseSerializer,
    UserProfileSerializer,
    TelegramUserSerializer,
    RegularPaymentsSerializer,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework.decorators import api_view
from datetime import datetime
from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser


# Categories are public - no auth requaied
# (so the bot can fetch category list for buttons)
class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()


# Expenses - each user sees only their own
class ExpenseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ExpenseSerializer

    # returns only expenses belonging to the current user
    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)

    # automatically assigns the current user on creation
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# User profile (currency, daily limit) - one per user
class UserProfileViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# Regular payments - each user manages their own
class RegularPaymentsViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RegularPaymentsSerializer

    def get_queryset(self):
        return RegularPayments.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# Links Telegram ID to a django user
class TelegramUserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TelegramUserSerializer

    def get_queryset(self):
        return TelegramUser.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # get telegram_id from validated data
        telegram_id = serializer.validated_data["telegram_id"]
        # create a Django user with username like tg_123456789
        user = User.objects.create_user(username=f"tg_{telegram_id}")
        # create an auth token for the new user
        token, _ = Token.objects.get_or_create(user=user)
        # save TelegramUser linked to the new Django user
        serializer.save(user=user)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        # find the newly created TelegramUser
        telegram_id = request.data.get("telegram_id")
        tg_user = TelegramUser.objects.get(telegram_id=telegram_id)
        # get the token and add it to the response
        token, _ = Token.objects.get_or_create(user=tg_user.user)
        response.data["token"] = token.key
        return response


from rest_framework.decorators import api_view


@api_view(["GET"])
@permission_classes([IsAdminUser])
def get_token_by_telegram_id(request, telegram_id):
    try:
        tg_user = TelegramUser.objects.get(telegram_id=telegram_id)
        token, _ = Token.objects.get_or_create(user=tg_user.user)
        return Response({"token": token.key})
    except TelegramUser.DoesNotExist:
        return Response({"error": "User not found"}, status=404)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def get_telegram_id(request):
    tg_user = TelegramUser.objects.all()
    ids = list(tg_user.values_list("telegram_id", flat=True))
    return Response(ids)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_monthly_stats(request):
    now = datetime.now()
    expenses = (
        Expense.objects.filter(
            user=request.user, date__month=now.month, date__year=now.year
        )
        .values("category__name")
        .annotate(total=Sum("amount"))
    )

    total = sum(item["total"] for item in expenses)

    return Response(
        {"month": now.strftime("%B %Y"), "categories": list(expenses), "total": total}
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_history(request):
    now = datetime.now()
    expenses = (
        Expense.objects.filter(
            user=request.user, date__month=now.month, date__year=now.year
        )
        .order_by("-date")
        .values("amount", "category__name", "date", "description")
    )
    return Response(list(expenses))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_currency(request):
    currency = request.data.get("currency")
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.currency = currency
    profile.save()
    return Response({"currency": currency})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return Response({"currency": profile.currency, "day_limit": profile.day_limit})

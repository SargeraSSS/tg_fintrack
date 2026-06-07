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

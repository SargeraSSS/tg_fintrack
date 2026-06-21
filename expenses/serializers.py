from rest_framework import serializers
from .models import Category, Expense, UserProfile, RegularPayments, TelegramUser


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        read_only_fields = ["user", "date"]
        fields = ["user", "date", "id", "amount", "category", "description"]


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        read_only_fields = ["user"]
        fields = ["user", "currency", "day_limit"]


class RegularPaymentsSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = RegularPayments
        read_only_fields = ["user"]
        fields = [
            "id",
            "amount",
            "name",
            "category",
            "payment_day",
            "user",
            "category_name",
        ]


class TelegramUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramUser
        read_only_fields = ["user"]
        fields = ["user", "telegram_id"]

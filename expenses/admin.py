from django.contrib import admin

from .models import Category, Expense, RegularPayments, TelegramUser, UserProfile

admin.site.register(Category)
admin.site.register(Expense)
admin.site.register(UserProfile)
admin.site.register(RegularPayments)
admin.site.register(TelegramUser)

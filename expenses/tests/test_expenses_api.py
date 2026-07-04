import pytest


@pytest.mark.django_db
def test_create_expense_requires_auth():
    """Without a token, you shouldn't be able to add an expense — should get a 401."""
    from rest_framework.test import APIClient

    client = APIClient()
    response = client.post("/api/expenses/", {"amount": 100, "category": 1})
    assert response.status_code == 401


@pytest.mark.django_db
def test_create_expense_authenticated(api_client):
    """A logged-in user should be able to add an expense and get a 201 back."""
    from expenses.models import Category

    category = Category.objects.create(name="Food")
    response = api_client.post(
        "/api/expenses/", {"amount": 100, "category": category.id}
    )
    assert response.status_code == 201


@pytest.mark.django_db
def test_user_cannot_see_other_users_expenses():
    """Users should only see their own expenses, never someone else's."""
    from django.contrib.auth.models import User
    from rest_framework.authtoken.models import Token
    from rest_framework.test import APIClient
    from expenses.models import Category, Expense

    user_a = User.objects.create_user(username="user_a", password="pass123")
    user_b = User.objects.create_user(username="user_b", password="pass123")
    token_a = Token.objects.create(user=user_a)
    token_b = Token.objects.create(user=user_b)

    category = Category.objects.create(name="Food")
    Expense.objects.create(user=user_a, amount=100, category=category)

    client_b = APIClient()
    client_b.credentials(HTTP_AUTHORIZATION=f"Token {token_b.key}")
    response = client_b.get("/api/expenses/")

    assert response.status_code == 200
    assert len(response.data) == 0

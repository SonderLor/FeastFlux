import uuid
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from users.models import User, UserProfile, VerificationToken
from users.forms import (
    CustomAuthenticationForm,
    CustomUserCreationForm,
    UserProfileForm,
    CustomPasswordResetForm,
    CustomSetPasswordForm,
    UserEditForm,
    StaffUserCreationForm,
)
from restaurants.models import Restaurant
from menu.models import Allergen

User = get_user_model()


class AuthenticationTestCase(TestCase):
    """Тесты авторизации пользователей."""

    def setUp(self):
        self.client = Client()
        self.customer = User.objects.create_user(
            username="testcustomer",
            email="customer@test.com",
            password="test123!",
            role=User.UserRole.CUSTOMER,
        )
        self.admin = User.objects.create_user(
            username="testadmin",
            email="admin@test.com",
            password="test123!",
            role=User.UserRole.ADMIN,
        )
        self.manager = User.objects.create_user(
            username="testmanager",
            email="manager@test.com",
            password="test123!",
            role=User.UserRole.MANAGER,
        )
        self.waiter = User.objects.create_user(
            username="testwaiter",
            email="waiter@test.com",
            password="test123!",
            role=User.UserRole.WAITER,
        )
        self.kitchen = User.objects.create_user(
            username="testkitchen",
            email="kitchen@test.com",
            password="test123!",
            role=User.UserRole.KITCHEN,
        )

        self.login_url = reverse("users:login")
        self.logout_url = reverse("users:logout")

    def test_login_page_loads_correctly(self):
        """Тест корректной загрузки страницы входа."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/login.html")
        self.assertIsInstance(response.context["form"], CustomAuthenticationForm)

    def test_login_with_valid_customer_credentials(self):
        """Тест входа с корректными учетными данными клиента."""
        response = self.client.post(
            self.login_url, {"username": "testcustomer", "password": "test123!"}
        )
        self.assertRedirects(response, reverse("users:customer_profile"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user, self.customer)

    def test_login_with_valid_admin_credentials(self):
        """Тест входа с корректными учетными данными администратора."""
        response = self.client.post(
            self.login_url, {"username": "testadmin", "password": "test123!"}
        )
        self.assertRedirects(response, reverse("analytics:dashboard"))

    def test_login_with_valid_manager_credentials(self):
        """Тест входа с корректными учетными данными менеджера."""
        response = self.client.post(
            self.login_url, {"username": "testmanager", "password": "test123!"}
        )
        self.assertRedirects(response, reverse("analytics:dashboard"))

    def test_login_with_valid_waiter_credentials(self):
        """Тест входа с корректными учетными данными официанта."""
        response = self.client.post(
            self.login_url, {"username": "testwaiter", "password": "test123!"}
        )
        self.assertRedirects(response, reverse("kitchen:waiter_dashboard"))

    def test_login_with_valid_kitchen_credentials(self):
        """Тест входа с корректными учетными данными сотрудника кухни."""
        response = self.client.post(
            self.login_url, {"username": "testkitchen", "password": "test123!"}
        )
        self.assertRedirects(response, reverse("kitchen:kitchen_dashboard"))

    def test_login_with_invalid_credentials(self):
        """Тест входа с некорректными учетными данными."""
        response = self.client.post(
            self.login_url, {"username": "testcustomer", "password": "wrongpassword"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/login.html")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_using_email(self):
        """Тест входа с использованием email вместо имени пользователя."""
        response = self.client.post(
            self.login_url, {"username": "customer@test.com", "password": "test123!"}
        )
        self.assertRedirects(response, reverse("users:customer_profile"))

    def test_authenticated_user_redirect_from_login(self):
        """Тест перенаправления авторизованного пользователя со страницы входа."""
        self.client.login(username="testcustomer", password="test123!")
        response = self.client.get(self.login_url)
        self.assertRedirects(response, reverse("users:customer_profile"))

    def test_logout(self):
        """Тест выхода из системы."""
        self.client.login(username="testcustomer", password="test123!")
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, self.login_url)

        response = self.client.get(reverse("users:customer_profile"))
        self.assertRedirects(response, f"{self.login_url}?next={reverse('users:customer_profile')}")


class RegistrationTestCase(TestCase):
    """Тесты регистрации новых пользователей."""

    def setUp(self):
        self.client = Client()
        self.register_url = reverse("users:register")
        self.allergen1 = Allergen.objects.create(name="Gluten")
        self.allergen2 = Allergen.objects.create(name="Lactose")

    @patch("users.views.create_verification_token")
    @patch("users.views.send_verification_email")
    def test_registration_page_loads_correctly(self, mock_send, mock_create):
        """Тест корректной загрузки страницы регистрации."""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/register.html")
        self.assertIsInstance(response.context["form"], CustomUserCreationForm)

    @patch("users.views.create_verification_token")
    @patch("users.views.send_verification_email")
    def test_registration_with_valid_data(self, mock_send, mock_create):
        """Тест регистрации с валидными данными."""
        mock_token = MagicMock()
        mock_create.return_value = mock_token

        response = self.client.post(
            self.register_url,
            {
                "username": "newuser",
                "email": "newuser@test.com",
                "first_name": "New",
                "last_name": "User",
                "phone_number": "1234567890",
                "password1": "complex_password123!",
                "password2": "complex_password123!",
                "terms_accepted": True,
            },
        )

        self.assertRedirects(response, reverse("users:login"))

        self.assertTrue(User.objects.filter(username="newuser").exists())
        user = User.objects.get(username="newuser")
        self.assertEqual(user.email, "newuser@test.com")
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "User")
        self.assertEqual(user.role, User.UserRole.CUSTOMER)

        self.assertTrue(hasattr(user, "profile"))
        self.assertEqual(user.profile.phone_number, "1234567890")

        mock_create.assert_called_once_with(user, "EMAIL_VERIFICATION")
        mock_send.assert_called_once_with(user, mock_token)

    @patch("users.views.create_verification_token")
    @patch("users.views.send_verification_email")
    def test_registration_with_invalid_data(self, mock_send, mock_create):
        """Тест регистрации с невалидными данными."""
        response = self.client.post(
            self.register_url,
            {
                "username": "",
                "email": "invalid-email",
                "first_name": "New",
                "last_name": "User",
                "phone_number": "1234567890",
                "password1": "simple",
                "password2": "different",
                "terms_accepted": False,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/register.html")

        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)
        self.assertIn("email", form.errors)
        self.assertIn("password2", form.errors)
        self.assertIn("terms_accepted", form.errors)

        self.assertFalse(User.objects.filter(username="").exists())

        mock_create.assert_not_called()
        mock_send.assert_not_called()

    def test_authenticated_user_redirect_from_register(self):
        """Тест перенаправления авторизованного пользователя со страницы регистрации."""
        user = User.objects.create_user(
            username="testuser", password="test123!", role=User.UserRole.CUSTOMER
        )
        self.client.login(username="testuser", password="test123!")

        response = self.client.get(self.register_url)
        self.assertRedirects(response, reverse("users:customer_profile"))


class EmailVerificationTestCase(TestCase):
    """Тесты верификации email."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="verifyuser",
            email="verify@test.com",
            password="test123!",
            role=User.UserRole.CUSTOMER,
            email_verified=False,
        )
        self.valid_token = VerificationToken.objects.create(
            user=self.user,
            token=str(uuid.uuid4()),
            expires_at=timezone.now() + timedelta(hours=24),
            token_type="EMAIL_VERIFICATION",
            is_used=False,
        )
        self.expired_token = VerificationToken.objects.create(
            user=self.user,
            token=str(uuid.uuid4()),
            expires_at=timezone.now() - timedelta(hours=1),
            token_type="EMAIL_VERIFICATION",
            is_used=False,
        )
        self.used_token = VerificationToken.objects.create(
            user=self.user,
            token=str(uuid.uuid4()),
            expires_at=timezone.now() + timedelta(hours=24),
            token_type="EMAIL_VERIFICATION",
            is_used=True,
        )

    def test_verify_email_with_valid_token(self):
        """Тест верификации email с валидным токеном."""
        url = reverse("users:verify_email", args=[self.valid_token.token])
        response = self.client.get(url)

        self.assertRedirects(response, reverse("users:login"))

        self.valid_token.refresh_from_db()
        self.assertTrue(self.valid_token.is_used)

        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)

    def test_verify_email_with_expired_token(self):
        """Тест верификации email с просроченным токеном."""
        url = reverse("users:verify_email", args=[self.expired_token.token])
        response = self.client.get(url)

        self.assertRedirects(response, reverse("users:login"))

        messages = list(response.wsgi_request._messages)
        self.assertIn("недействительна или истекла", str(messages[0]))

        self.expired_token.refresh_from_db()
        self.assertFalse(self.expired_token.is_used)

        self.user.refresh_from_db()
        self.assertFalse(self.user.email_verified)

    def test_verify_email_with_used_token(self):
        """Тест верификации email с уже использованным токеном."""
        url = reverse("users:verify_email", args=[self.used_token.token])
        response = self.client.get(url)

        self.assertRedirects(response, reverse("users:login"))

        messages = list(response.wsgi_request._messages)
        self.assertIn("недействительна или истекла", str(messages[0]))

        self.user.refresh_from_db()
        self.assertFalse(self.user.email_verified)

    def test_verify_email_with_nonexistent_token(self):
        """Тест верификации email с несуществующим токеном."""
        url = reverse("users:verify_email", args=["nonexistenttoken123"])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class PasswordResetTestCase(TestCase):
    """Тесты сброса пароля."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="resetuser",
            email="reset@test.com",
            password="oldpassword123!",
            role=User.UserRole.CUSTOMER,
        )
        self.reset_request_url = reverse("users:password_reset")

        self.valid_token = VerificationToken.objects.create(
            user=self.user,
            token=str(uuid.uuid4()),
            expires_at=timezone.now() + timedelta(hours=24),
            token_type="PASSWORD_RESET",
            is_used=False,
        )
        self.reset_confirm_url = reverse(
            "users:password_reset_confirm", args=[self.valid_token.token]
        )

    @patch("users.views.create_verification_token")
    @patch("django.core.mail.send_mail")
    def test_password_reset_request_page_loads(self, mock_send_mail, mock_create_token):
        """Тест корректной загрузки страницы запроса сброса пароля."""
        response = self.client.get(self.reset_request_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/password_reset.html")
        self.assertIsInstance(response.context["form"], CustomPasswordResetForm)

    @patch("users.views.create_verification_token")
    @patch("django.core.mail.send_mail")
    def test_password_reset_request_with_valid_email(self, mock_send_mail, mock_create_token):
        """Тест запроса сброса пароля с существующим email."""
        mock_token = MagicMock()
        mock_token.token = "valid-token"
        mock_token.expires_at = timezone.now() + timedelta(hours=24)
        mock_create_token.return_value = mock_token

        response = self.client.post(self.reset_request_url, {"email": "reset@test.com"})

        self.assertRedirects(response, reverse("users:login"))

        mock_create_token.assert_called_once_with(self.user, "PASSWORD_RESET")

        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args
        self.assertEqual(call_args[0][3], ["reset@test.com"])

    @patch("users.views.create_verification_token")
    @patch("django.core.mail.send_mail")
    def test_password_reset_request_with_nonexistent_email(self, mock_send_mail, mock_create_token):
        """Тест запроса сброса пароля с несуществующим email."""
        response = self.client.post(self.reset_request_url, {"email": "nonexistent@test.com"})

        self.assertRedirects(response, reverse("users:login"))

        mock_create_token.assert_not_called()
        mock_send_mail.assert_not_called()

    def test_password_reset_confirm_page_loads(self):
        """Тест корректной загрузки страницы подтверждения сброса пароля."""
        response = self.client.get(self.reset_confirm_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/password_reset_confirm.html")
        self.assertIsInstance(response.context["form"], CustomSetPasswordForm)

    def test_password_reset_confirm_with_valid_token_and_data(self):
        """Тест подтверждения сброса пароля с валидным токеном и данными."""
        response = self.client.post(
            self.reset_confirm_url,
            {"new_password1": "newpassword123!", "new_password2": "newpassword123!"},
        )

        self.assertRedirects(response, reverse("users:login"))

        self.valid_token.refresh_from_db()
        self.assertTrue(self.valid_token.is_used)

        self.assertTrue(self.client.login(username="resetuser", password="newpassword123!"))

    def test_password_reset_confirm_with_invalid_data(self):
        """Тест подтверждения сброса пароля с невалидными данными."""
        response = self.client.post(
            self.reset_confirm_url, {"new_password1": "short", "new_password2": "different"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/password_reset_confirm.html")

        form = response.context["form"]
        self.assertFalse(form.is_valid())

        self.valid_token.refresh_from_db()
        self.assertFalse(self.valid_token.is_used)

        self.assertFalse(self.client.login(username="resetuser", password="short"))
        self.assertTrue(self.client.login(username="resetuser", password="oldpassword123!"))


class UserProfileTestCase(TestCase):
    """Тесты профилей пользователей."""

    def setUp(self):
        self.client = Client()

        self.customer = User.objects.create_user(
            username="profilecustomer",
            email="profilecustomer@test.com",
            password="test123!",
            first_name="Test",
            last_name="Customer",
            role=User.UserRole.CUSTOMER,
        )

        self.staff = User.objects.create_user(
            username="profilestaff",
            email="profilestaff@test.com",
            password="test123!",
            first_name="Test",
            last_name="Staff",
            role=User.UserRole.WAITER,
        )

        self.allergen1 = Allergen.objects.create(name="Gluten")
        self.allergen2 = Allergen.objects.create(name="Lactose")

        self.customer_profile_url = reverse("users:customer_profile")
        self.staff_profile_url = reverse("users:staff_profile")

    def test_customer_profile_page_loads(self):
        """Тест корректной загрузки страницы профиля клиента."""
        self.client.login(username="profilecustomer", password="test123!")
        response = self.client.get(self.customer_profile_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/customer_profile.html")
        self.assertIsInstance(response.context["user_form"], UserEditForm)
        self.assertIsInstance(response.context["profile_form"], UserProfileForm)

    def test_staff_profile_page_loads(self):
        """Тест корректной загрузки страницы профиля сотрудника."""
        self.client.login(username="profilestaff", password="test123!")
        response = self.client.get(self.staff_profile_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/staff_profile.html")
        self.assertIsInstance(response.context["user_form"], UserEditForm)
        self.assertIsInstance(response.context["profile_form"], UserProfileForm)

    def test_customer_redirected_from_staff_profile(self):
        """Тест перенаправления клиента со страницы профиля сотрудника."""
        self.client.login(username="profilecustomer", password="test123!")
        response = self.client.get(self.staff_profile_url)

        self.assertRedirects(response, self.customer_profile_url)

    def test_staff_redirected_from_customer_profile(self):
        """Тест перенаправления сотрудника со страницы профиля клиента."""
        self.client.login(username="profilestaff", password="test123!")
        response = self.client.get(self.customer_profile_url)

        self.assertRedirects(response, self.staff_profile_url)

    def test_update_customer_profile(self):
        """Тест обновления профиля клиента."""
        self.client.login(username="profilecustomer", password="test123!")

        response = self.client.post(
            self.customer_profile_url,
            {
                "first_name": "Updated",
                "last_name": "Customer",
                "email": "updated.customer@test.com",
                "phone_number": "9876543210",
                "date_of_birth": "1990-01-01",
                "address": "Test Address",
                "bio": "Test Bio",
                "diet_vegetarian": True,
                "diet_vegan": False,
                "allergen_ids": [self.allergen1.id, self.allergen2.id],
            },
        )

        self.assertRedirects(response, self.customer_profile_url)

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.first_name, "Updated")
        self.assertEqual(self.customer.email, "updated.customer@test.com")

        self.customer.profile.refresh_from_db()
        self.assertEqual(self.customer.profile.phone_number, "9876543210")
        self.assertEqual(str(self.customer.profile.date_of_birth), "1990-01-01")
        self.assertEqual(self.customer.profile.address, "Test Address")
        self.assertEqual(self.customer.profile.bio, "Test Bio")

        self.assertTrue(self.customer.profile.dietary_preferences.get("vegetarian", False))
        self.assertFalse(self.customer.profile.dietary_preferences.get("vegan", True))

        self.assertEqual(len(self.customer.profile.allergens["ids"]), 2)
        self.assertIn(str(self.allergen1.id), self.customer.profile.allergens["ids"])
        self.assertIn(str(self.allergen2.id), self.customer.profile.allergens["ids"])

    def test_update_staff_profile(self):
        """Тест обновления профиля сотрудника."""
        self.client.login(username="profilestaff", password="test123!")

        response = self.client.post(
            self.staff_profile_url,
            {
                "first_name": "Updated",
                "last_name": "Staff",
                "email": "updated.staff@test.com",
                "phone_number": "9876543210",
                "date_of_birth": "1990-01-01",
                "bio": "Staff Bio",
            },
        )

        self.assertRedirects(response, self.staff_profile_url)

        self.staff.refresh_from_db()
        self.assertEqual(self.staff.first_name, "Updated")
        self.assertEqual(self.staff.email, "updated.staff@test.com")

        self.staff.profile.refresh_from_db()
        self.assertEqual(self.staff.profile.phone_number, "9876543210")
        self.assertEqual(str(self.staff.profile.date_of_birth), "1990-01-01")
        self.assertEqual(self.staff.profile.bio, "Staff Bio")

    def test_unauthorized_access_to_profiles(self):
        """Тест неавторизованного доступа к страницам профилей."""
        response = self.client.get(self.customer_profile_url)
        self.assertRedirects(response, f"{reverse('users:login')}?next={self.customer_profile_url}")

        response = self.client.get(self.staff_profile_url)
        self.assertRedirects(response, f"{reverse('users:login')}?next={self.staff_profile_url}")


class StaffManagementTestCase(TestCase):
    """Тесты управления персоналом."""

    def setUp(self):
        self.client = Client()

        self.restaurant = Restaurant.objects.create(
            name="Test Restaurant", address="Test Address", phone="123456789", is_active=True
        )

        self.admin = User.objects.create_user(
            username="staffadmin",
            email="staffadmin@test.com",
            password="test123!",
            role=User.UserRole.ADMIN,
        )

        self.manager = User.objects.create_user(
            username="staffmanager",
            email="staffmanager@test.com",
            password="test123!",
            role=User.UserRole.MANAGER,
            restaurant=self.restaurant,
        )

        self.waiter = User.objects.create_user(
            username="staffwaiter",
            email="staffwaiter@test.com",
            password="test123!",
            role=User.UserRole.WAITER,
            restaurant=self.restaurant,
        )

        self.customer = User.objects.create_user(
            username="staffcustomer",
            email="staffcustomer@test.com",
            password="test123!",
            role=User.UserRole.CUSTOMER,
        )

        self.staff_list_url = reverse("users:staff_list")
        self.staff_create_url = reverse("users:staff_create")
        self.waiter_edit_url = reverse("users:staff_edit", args=[self.waiter.id])
        self.waiter_deactivate_url = reverse("users:staff_deactivate", args=[self.waiter.id])

    def test_staff_list_page_loads_for_admin(self):
        """Тест загрузки страницы списка персонала для администратора."""
        self.client.login(username="staffadmin", password="test123!")
        response = self.client.get(self.staff_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/staff_list.html")

        self.assertContains(response, "staffadmin")
        self.assertContains(response, "staffmanager")
        self.assertContains(response, "staffwaiter")
        self.assertNotContains(response, "staffcustomer")

    def test_staff_list_page_loads_for_manager(self):
        """Тест загрузки страницы списка персонала для менеджера."""
        self.client.login(username="staffmanager", password="test123!")
        response = self.client.get(self.staff_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/staff_list.html")

    def test_staff_list_filtered_by_role(self):
        """Тест фильтрации списка персонала по роли."""
        self.client.login(username="staffadmin", password="test123!")
        response = self.client.get(f"{self.staff_list_url}?role=WAITER")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "staffwaiter")
        self.assertNotContains(response, "staffadmin")
        self.assertNotContains(response, "staffmanager")

    def test_staff_list_filtered_by_restaurant(self):
        """Тест фильтрации списка персонала по ресторану."""
        self.client.login(username="staffadmin", password="test123!")
        response = self.client.get(f"{self.staff_list_url}?restaurant={self.restaurant.id}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "staffmanager")
        self.assertContains(response, "staffwaiter")
        self.assertNotContains(response, "staffadmin")

    def test_staff_create_page_loads_for_admin(self):
        """Тест загрузки страницы создания сотрудника для администратора."""
        self.client.login(username="staffadmin", password="test123!")
        response = self.client.get(self.staff_create_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/staff_create.html")
        self.assertIsInstance(response.context["form"], StaffUserCreationForm)

    def test_staff_create_with_valid_data(self):
        """Тест создания сотрудника с валидными данными."""
        self.client.login(username="staffadmin", password="test123!")

        response = self.client.post(
            self.staff_create_url,
            {
                "username": "newwaiter",
                "email": "newwaiter@test.com",
                "first_name": "New",
                "last_name": "Waiter",
                "role": User.UserRole.WAITER,
                "restaurant": self.restaurant.id,
                "is_active_employee": True,
                "employee_id": "W-123",
                "phone_number": "1234567890",
                "hire_date": "2023-01-01",
                "password1": "complex_password123!",
                "password2": "complex_password123!",
            },
        )

        self.assertRedirects(response, self.staff_list_url)

        self.assertTrue(User.objects.filter(username="newwaiter").exists())
        user = User.objects.get(username="newwaiter")
        self.assertEqual(user.email, "newwaiter@test.com")
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "Waiter")
        self.assertEqual(user.role, User.UserRole.WAITER)
        self.assertEqual(user.restaurant, self.restaurant)
        self.assertEqual(user.employee_id, "W-123")
        self.assertTrue(user.is_active_employee)
        self.assertTrue(user.is_staff)

        self.assertEqual(user.profile.phone_number, "1234567890")
        self.assertEqual(str(user.profile.hire_date), "2023-01-01")

    def test_staff_create_with_invalid_data(self):
        """Тест создания сотрудника с невалидными данными."""
        self.client.login(username="staffadmin", password="test123!")

        response = self.client.post(
            self.staff_create_url,
            {
                "username": "",
                "email": "invalid-email",
                "first_name": "New",
                "last_name": "Waiter",
                "role": "INVALID_ROLE",
                "restaurant": 999,
                "password1": "short",
                "password2": "different",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/staff_create.html")

        form = response.context["form"]
        self.assertFalse(form.is_valid())

        self.assertFalse(User.objects.filter(first_name="New", last_name="Waiter").exists())

    def test_staff_edit_page_loads_for_admin(self):
        """Тест загрузки страницы редактирования сотрудника для администратора."""
        self.client.login(username="staffadmin", password="test123!")
        response = self.client.get(self.waiter_edit_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/staff_edit.html")
        self.assertIsInstance(response.context["user_form"], UserEditForm)
        self.assertIsInstance(response.context["profile_form"], UserProfileForm)

    def test_staff_edit_with_valid_data(self):
        """Тест редактирования сотрудника с валидными данными."""
        self.client.login(username="staffadmin", password="test123!")

        response = self.client.post(
            self.waiter_edit_url,
            {
                "first_name": "Updated",
                "last_name": "Waiter",
                "email": "updated.waiter@test.com",
                "role": User.UserRole.BARTENDER,
                "restaurant": self.restaurant.id,
                "is_active_employee": True,
                "employee_id": "B-123",
                "phone_number": "9876543210",
            },
        )

        self.assertRedirects(response, self.staff_list_url)

        self.waiter.refresh_from_db()
        self.assertEqual(self.waiter.first_name, "Updated")
        self.assertEqual(self.waiter.email, "updated.waiter@test.com")
        self.assertEqual(self.waiter.role, User.UserRole.BARTENDER)
        self.assertEqual(self.waiter.employee_id, "B-123")

        self.waiter.profile.refresh_from_db()
        self.assertEqual(self.waiter.profile.phone_number, "9876543210")

    def test_staff_deactivate(self):
        """Тест деактивации сотрудника."""
        self.client.login(username="staffadmin", password="test123!")

        response = self.client.post(self.waiter_deactivate_url)

        self.assertRedirects(response, self.staff_list_url)

        self.waiter.refresh_from_db()
        self.assertFalse(self.waiter.is_active)
        self.assertFalse(self.waiter.is_active_employee)

    def test_customer_cannot_be_edited_via_staff_interface(self):
        """Тест, что клиента нельзя редактировать через интерфейс сотрудников."""
        self.client.login(username="staffadmin", password="test123!")

        customer_edit_url = reverse("users:staff_edit", args=[self.customer.id])
        response = self.client.get(customer_edit_url)

        self.assertRedirects(response, self.staff_list_url)

        messages = list(response.wsgi_request._messages)
        self.assertIn("не можете редактировать клиентов", str(messages[0]))

    def test_cannot_deactivate_self(self):
        """Тест, что нельзя деактивировать собственный аккаунт."""
        self.client.login(username="staffadmin", password="test123!")

        admin_deactivate_url = reverse("users:staff_deactivate", args=[self.admin.id])
        response = self.client.post(admin_deactivate_url)

        self.assertRedirects(response, self.staff_list_url)

        messages = list(response.wsgi_request._messages)
        self.assertIn("не можете деактивировать свой собственный аккаунт", str(messages[0]))

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_unauthorized_access_denied(self):
        """Тест запрета доступа неавторизованным пользователям."""
        response = self.client.get(self.staff_list_url)
        self.assertRedirects(response, f"{reverse('users:login')}?next={self.staff_list_url}")

        response = self.client.get(self.staff_create_url)
        self.assertRedirects(response, f"{reverse('users:login')}?next={self.staff_create_url}")

        response = self.client.get(self.waiter_edit_url)
        self.assertRedirects(response, f"{reverse('users:login')}?next={self.waiter_edit_url}")

        response = self.client.post(self.waiter_deactivate_url)
        self.assertRedirects(
            response, f"{reverse('users:login')}?next={self.waiter_deactivate_url}"
        )

    def test_customer_access_denied(self):
        """Тест запрета доступа клиентам к управлению персоналом."""
        self.client.login(username="staffcustomer", password="test123!")

        response = self.client.get(self.staff_list_url)
        self.assertEqual(response.status_code, 403)

        response = self.client.get(self.staff_create_url)
        self.assertEqual(response.status_code, 403)

        response = self.client.get(self.waiter_edit_url)
        self.assertEqual(response.status_code, 403)

        response = self.client.post(self.waiter_deactivate_url)
        self.assertEqual(response.status_code, 403)


class UserModelTestCase(TestCase):
    """Тесты модели пользователя."""

    def setUp(self):
        self.restaurant = Restaurant.objects.create(
            name="Test Restaurant", address="Test Address", phone="123456789", is_active=True
        )

        self.admin = User.objects.create_user(
            username="modeladmin",
            email="modeladmin@test.com",
            password="test123!",
            role=User.UserRole.ADMIN,
        )

        self.manager = User.objects.create_user(
            username="modelmanager",
            email="modelmanager@test.com",
            password="test123!",
            role=User.UserRole.MANAGER,
            restaurant=self.restaurant,
        )

        self.waiter = User.objects.create_user(
            username="modelwaiter",
            email="modelwaiter@test.com",
            password="test123!",
            role=User.UserRole.WAITER,
            restaurant=self.restaurant,
        )

        self.kitchen = User.objects.create_user(
            username="modelkitchen",
            email="modelkitchen@test.com",
            password="test123!",
            role=User.UserRole.KITCHEN,
            restaurant=self.restaurant,
        )

        self.bartender = User.objects.create_user(
            username="modelbartender",
            email="modelbartender@test.com",
            password="test123!",
            role=User.UserRole.BARTENDER,
            restaurant=self.restaurant,
        )

        self.customer = User.objects.create_user(
            username="modelcustomer",
            email="modelcustomer@test.com",
            password="test123!",
            role=User.UserRole.CUSTOMER,
        )

    def test_user_role_methods(self):
        """Тест методов проверки ролей пользователя."""
        self.assertTrue(self.admin.is_admin())
        self.assertFalse(self.manager.is_admin())

        self.assertTrue(self.manager.is_manager())
        self.assertFalse(self.admin.is_manager())

        self.assertTrue(self.waiter.is_waiter())
        self.assertFalse(self.manager.is_waiter())

        self.assertTrue(self.kitchen.is_kitchen())
        self.assertFalse(self.waiter.is_kitchen())

        self.assertTrue(self.bartender.is_bartender())
        self.assertFalse(self.kitchen.is_bartender())

        self.assertTrue(self.customer.is_customer())
        self.assertFalse(self.admin.is_customer())

    def test_is_kitchen_staff_method(self):
        """Тест метода is_kitchen_staff."""
        self.assertTrue(self.kitchen.is_kitchen_staff())
        self.assertTrue(self.bartender.is_kitchen_staff())
        self.assertFalse(self.waiter.is_kitchen_staff())
        self.assertFalse(self.manager.is_kitchen_staff())
        self.assertFalse(self.admin.is_kitchen_staff())
        self.assertFalse(self.customer.is_kitchen_staff())

    def test_is_restaurant_staff_method(self):
        """Тест метода is_restaurant_staff."""
        self.assertTrue(self.admin.is_restaurant_staff())
        self.assertTrue(self.manager.is_restaurant_staff())
        self.assertTrue(self.waiter.is_restaurant_staff())
        self.assertTrue(self.kitchen.is_restaurant_staff())
        self.assertTrue(self.bartender.is_restaurant_staff())
        self.assertFalse(self.customer.is_restaurant_staff())

    def test_str_method(self):
        """Тест строкового представления пользователя."""
        self.admin.first_name = "Admin"
        self.admin.last_name = "User"
        self.admin.save()

        expected_str = "Admin User (Администратор)"
        self.assertEqual(str(self.admin), expected_str)

        expected_str = "modelcustomer (Клиент)"
        self.assertEqual(str(self.customer), expected_str)


class UserProfileModelTestCase(TestCase):
    """Тесты модели профиля пользователя."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="profileuser",
            email="profileuser@test.com",
            password="test123!",
            role=User.UserRole.CUSTOMER,
        )

        self.profile = self.user.profile

    def test_profile_autocreation(self):
        """Тест автоматического создания профиля при создании пользователя."""
        new_user = User.objects.create_user(
            username="newprofileuser", email="newprofileuser@test.com", password="test123!"
        )

        self.assertTrue(hasattr(new_user, "profile"))
        self.assertIsInstance(new_user.profile, UserProfile)

    def test_profile_update(self):
        """Тест обновления полей профиля."""
        self.profile.phone_number = "1234567890"
        self.profile.address = "Test Address"
        self.profile.bio = "Test Bio"
        self.profile.date_of_birth = timezone.now().date()
        self.profile.save()

        self.profile.refresh_from_db()

        self.assertEqual(self.profile.phone_number, "1234567890")
        self.assertEqual(self.profile.address, "Test Address")
        self.assertEqual(self.profile.bio, "Test Bio")
        self.assertEqual(self.profile.date_of_birth, timezone.now().date())

    def test_json_fields(self):
        """Тест работы с JSON-полями профиля."""
        diet_prefs = {"vegetarian": True, "vegan": False, "gluten_free": True}
        self.profile.dietary_preferences = diet_prefs

        allergens = {"ids": ["1", "2", "3"], "names": ["Gluten", "Lactose", "Nuts"]}
        self.profile.allergens = allergens

        self.profile.favorite_dishes = ["1", "2", "3"]

        self.profile.saved_delivery_addresses = [
            {"name": "Home", "address": "Home Address"},
            {"name": "Work", "address": "Work Address"},
        ]

        self.profile.notification_preferences = {"email": True, "sms": False, "push": True}

        self.profile.save()
        self.profile.refresh_from_db()

        self.assertEqual(self.profile.dietary_preferences, diet_prefs)
        self.assertEqual(self.profile.allergens, allergens)
        self.assertEqual(self.profile.favorite_dishes, ["1", "2", "3"])
        self.assertEqual(len(self.profile.saved_delivery_addresses), 2)
        self.assertEqual(self.profile.saved_delivery_addresses[0]["name"], "Home")
        self.assertEqual(self.profile.notification_preferences["email"], True)
        self.assertEqual(self.profile.notification_preferences["sms"], False)

    def test_loyalty_points(self):
        """Тест работы с баллами лояльности."""
        self.assertEqual(self.profile.loyalty_points, 0)

        self.profile.loyalty_points = 100
        self.profile.save()
        self.profile.refresh_from_db()

        self.assertEqual(self.profile.loyalty_points, 100)

    def test_str_method(self):
        """Тест строкового представления профиля."""
        expected_str = f"Профиль {self.user.username}"
        self.assertEqual(str(self.profile), expected_str)


class VerificationTokenTestCase(TestCase):
    """Тесты модели токена верификации."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="tokenuser", email="tokenuser@test.com", password="test123!"
        )

        self.valid_token = VerificationToken.objects.create(
            user=self.user,
            token=str(uuid.uuid4()),
            expires_at=timezone.now() + timedelta(hours=24),
            token_type="EMAIL_VERIFICATION",
            is_used=False,
        )

        self.expired_token = VerificationToken.objects.create(
            user=self.user,
            token=str(uuid.uuid4()),
            expires_at=timezone.now() - timedelta(hours=1),
            token_type="EMAIL_VERIFICATION",
            is_used=False,
        )

        self.used_token = VerificationToken.objects.create(
            user=self.user,
            token=str(uuid.uuid4()),
            expires_at=timezone.now() + timedelta(hours=24),
            token_type="PASSWORD_RESET",
            is_used=True,
        )

    def test_is_valid_method(self):
        """Тест метода is_valid для проверки действительности токена."""
        self.assertTrue(self.valid_token.is_valid())
        self.assertFalse(self.expired_token.is_valid())
        self.assertFalse(self.used_token.is_valid())

    def test_str_method(self):
        """Тест строкового представления токена."""
        expected_str = f"Токен EMAIL_VERIFICATION для {self.user.username}"
        self.assertEqual(str(self.valid_token), expected_str)

        expected_str = f"Токен PASSWORD_RESET для {self.user.username}"
        self.assertEqual(str(self.used_token), expected_str)

    def test_token_creation(self):
        """Тест создания токена через функцию helpers."""
        from users.views import create_verification_token

        token = create_verification_token(self.user, "PASSWORD_RESET")

        self.assertIsInstance(token, VerificationToken)
        self.assertEqual(token.user, self.user)
        self.assertEqual(token.token_type, "PASSWORD_RESET")
        self.assertFalse(token.is_used)

        time_diff = token.expires_at - timezone.now()
        self.assertGreater(time_diff.total_seconds(), 23 * 3600)
        self.assertLess(time_diff.total_seconds(), 25 * 3600)

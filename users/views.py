import uuid
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from orders.models import Order
from .models import User, VerificationToken
from .forms import (
    CustomAuthenticationForm,
    CustomUserCreationForm,
    UserProfileForm,
    CustomPasswordResetForm,
    CustomSetPasswordForm,
    UserEditForm,
    StaffUserCreationForm,
)


def login_view(request):
    """Представление для авторизации пользователей."""
    if request.user.is_authenticated:
        if request.user.is_customer():
            return redirect("users:customer_profile")
        else:
            return redirect("users:staff_profile")

    if request.method == "POST":
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)

                if user.is_customer():
                    return redirect("users:customer_profile")
                elif user.is_admin() or user.is_manager():
                    return redirect("analytics:dashboard")
                elif user.is_kitchen_staff():
                    return redirect("kitchen:kitchen_dashboard")
                # TODO Сделать дашборд для официантов
                elif user.is_waiter():
                    return redirect("waiter_dashboard")
                else:
                    return redirect("users:staff_profile")
            else:
                messages.error(request, _("Неверное имя пользователя или пароль"))
    else:
        form = CustomAuthenticationForm()

    return render(request, "users/login.html", {"form": form})


def logout_view(request):
    """Представление для выхода из системы."""
    logout(request)
    return redirect("users:login")


def register_view(request):
    """Представление для регистрации новых пользователей (клиентов)."""
    if request.user.is_authenticated:
        return redirect("users:customer_profile")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            token = create_verification_token(user, "EMAIL_VERIFICATION")
            send_verification_email(user, token)

            messages.success(
                request,
                _(
                    "Регистрация успешна! Мы отправили письмо с подтверждением на ваш email. "
                    "Пожалуйста, перейдите по ссылке в письме для активации аккаунта."
                ),
            )
            return redirect("users:login")
    else:
        form = CustomUserCreationForm()

    return render(request, "users/register.html", {"form": form})


def create_verification_token(user, token_type):
    """Создает токен верификации для пользователя."""
    token_value = str(uuid.uuid4())

    expires_at = timezone.now() + timedelta(hours=24)

    token = VerificationToken.objects.create(
        user=user, token=token_value, expires_at=expires_at, token_type=token_type
    )

    return token


def send_verification_email(user, token):
    """Отправляет письмо с подтверждением email."""
    verify_url = f"{settings.SITE_URL}{reverse('users:verify_email', args=[token.token])}"

    subject = _("Подтверждение email на FeastFlux")
    html_message = render_to_string(
        "users/emails/verify_email.html",
        {"user": user, "verify_url": verify_url, "expires_at": token.expires_at},
    )
    plain_message = strip_tags(html_message)

    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )


def verify_email_view(request, token):
    """Подтверждение email по токену."""
    verification_token = get_object_or_404(
        VerificationToken, token=token, token_type="EMAIL_VERIFICATION"
    )

    if not verification_token.is_valid():
        messages.error(request, _("Ссылка для подтверждения недействительна или истекла."))
        return redirect("users:login")

    verification_token.is_used = True
    verification_token.save()

    user = verification_token.user
    user.email_verified = True
    user.save()

    messages.success(request, _("Ваш email успешно подтвержден! Теперь вы можете войти в систему."))
    return redirect("users:login")


def password_reset_request(request):
    """Запрос на сброс пароля."""
    if request.method == "POST":
        form = CustomPasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]

            try:
                user = User.objects.get(email=email)

                token = create_verification_token(user, "PASSWORD_RESET")

                reset_url = f"{settings.SITE_URL}{reverse('users:password_reset_confirm', args=[token.token])}"

                subject = _("Сброс пароля на FeastFlux")
                html_message = render_to_string(
                    "users/emails/password_reset.html",
                    {"user": user, "reset_url": reset_url, "expires_at": token.expires_at},
                )
                plain_message = strip_tags(html_message)

                send_mail(
                    subject,
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    html_message=html_message,
                    fail_silently=False,
                )

                messages.success(
                    request,
                    _(
                        "Мы отправили инструкции по сбросу пароля на указанный email. "
                        "Пожалуйста, проверьте свою почту."
                    ),
                )
                return redirect("users:login")

            except User.DoesNotExist:
                messages.success(
                    request,
                    _(
                        "Если указанный email существует в нашей системе, "
                        "мы отправим на него инструкции по сбросу пароля."
                    ),
                )
                return redirect("users:login")
    else:
        form = CustomPasswordResetForm()

    return render(request, "users/password_reset.html", {"form": form})


def password_reset_confirm(request, token):
    """Подтверждение сброса пароля и установка нового."""
    verification_token = get_object_or_404(
        VerificationToken, token=token, token_type="PASSWORD_RESET"
    )

    if not verification_token.is_valid():
        messages.error(request, _("Ссылка для сброса пароля недействительна или истекла."))
        return redirect("users:login")

    user = verification_token.user

    if request.method == "POST":
        form = CustomSetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()

            verification_token.is_used = True
            verification_token.save()

            messages.success(
                request, _("Ваш пароль успешно изменен. Теперь вы можете войти в систему.")
            )
            return redirect("users:login")
    else:
        form = CustomSetPasswordForm(user)

    return render(request, "users/password_reset_confirm.html", {"form": form})


@login_required
def customer_profile_view(request):
    """Представление для профиля клиента."""
    user = request.user

    if not user.is_customer():
        return redirect("users:staff_profile")

    if request.method == "POST":
        user_form = UserEditForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, _("Профиль успешно обновлен!"))
            return redirect("users:customer_profile")
    else:
        user_form = UserEditForm(instance=user)
        profile_form = UserProfileForm(instance=user.profile)

    recent_orders = Order.objects.filter(customer=user)[:5]

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
        "recent_orders": recent_orders,
    }

    return render(request, "users/customer_profile.html", context)


@login_required
def staff_profile_view(request):
    """Представление для профиля сотрудника."""
    user = request.user

    if user.is_customer():
        return redirect("users:customer_profile")

    if request.method == "POST":
        user_form = UserEditForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, _("Профиль успешно обновлен!"))
            return redirect("users:staff_profile")
    else:
        user_form = UserEditForm(instance=user)
        profile_form = UserProfileForm(instance=user.profile)

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
    }

    return render(request, "users/staff_profile.html", context)


def is_admin_or_manager(user):
    """Проверяет, является ли пользователь администратором или менеджером."""
    return user.is_authenticated and (user.is_admin() or user.is_manager())


@login_required
@user_passes_test(is_admin_or_manager)
def staff_list_view(request):
    """Представление для списка сотрудников (для администраторов и менеджеров)."""
    role_filter = request.GET.get("role", "")
    restaurant_filter = request.GET.get("restaurant", "")

    staff_users = User.objects.exclude(role=User.UserRole.CUSTOMER)

    if role_filter:
        staff_users = staff_users.filter(role=role_filter)
    if restaurant_filter:
        staff_users = staff_users.filter(restaurant_id=restaurant_filter)

    from restaurants.models import Restaurant

    restaurants = Restaurant.objects.filter(is_active=True)

    context = {
        "staff_users": staff_users,
        "restaurants": restaurants,
        "role_choices": User.UserRole.choices,
        "selected_role": role_filter,
        "selected_restaurant": restaurant_filter,
    }

    return render(request, "users/staff_list.html", context)


@login_required
@user_passes_test(is_admin_or_manager)
def staff_create_view(request):
    """Представление для создания нового сотрудника."""
    if request.method == "POST":
        form = StaffUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, _("Сотрудник успешно создан!"))
            return redirect("users:staff_list")
    else:
        form = StaffUserCreationForm()

    return render(request, "users/staff_create.html", {"form": form})


@login_required
@user_passes_test(is_admin_or_manager)
def staff_edit_view(request, user_id):
    """Представление для редактирования сотрудника."""
    user_obj = get_object_or_404(User, id=user_id)

    if user_obj.is_customer():
        messages.error(request, _("Вы не можете редактировать клиентов через этот интерфейс."))
        return redirect("users:staff_list")

    if request.method == "POST":
        user_form = UserEditForm(request.POST, instance=user_obj)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=user_obj.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()

            user_obj.role = request.POST.get("role", user_obj.role)
            restaurant_id = request.POST.get("restaurant")

            from restaurants.models import Restaurant

            if restaurant_id:
                try:
                    user_obj.restaurant = Restaurant.objects.get(id=restaurant_id)
                except Restaurant.DoesNotExist:
                    user_obj.restaurant = None
            else:
                user_obj.restaurant = None

            user_obj.is_active_employee = "is_active_employee" in request.POST
            user_obj.employee_id = request.POST.get("employee_id", "")
            user_obj.save()

            messages.success(request, _("Сотрудник успешно обновлен!"))
            return redirect("users:staff_list")
    else:
        user_form = UserEditForm(instance=user_obj)
        profile_form = UserProfileForm(instance=user_obj.profile)

    from restaurants.models import Restaurant

    restaurants = Restaurant.objects.filter(is_active=True)

    context = {
        "user_obj": user_obj,
        "user_form": user_form,
        "profile_form": profile_form,
        "restaurants": restaurants,
        "role_choices": User.UserRole.choices,
    }

    return render(request, "users/staff_edit.html", context)


@login_required
@user_passes_test(is_admin_or_manager)
def staff_deactivate_view(request, user_id):
    """Представление для деактивации сотрудника."""
    user_obj = get_object_or_404(User, id=user_id)

    if user_obj.is_customer():
        messages.error(request, _("Вы не можете деактивировать клиентов через этот интерфейс."))
        return redirect("users:staff_list")

    if user_obj == request.user:
        messages.error(request, _("Вы не можете деактивировать свой собственный аккаунт."))
        return redirect("users:staff_list")

    user_obj.is_active = False
    user_obj.is_active_employee = False
    user_obj.save()

    messages.success(request, _("Сотрудник успешно деактивирован!"))
    return redirect("users:staff_list")

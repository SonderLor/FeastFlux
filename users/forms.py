from django import forms
from django.contrib.auth.forms import (
    UserCreationForm,
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
)
from django.utils.translation import gettext_lazy as _
from .models import User, UserProfile
from menu.models import Allergen


class CustomAuthenticationForm(AuthenticationForm):
    """Кастомная форма авторизации с улучшенным дизайном."""

    username = forms.CharField(
        label=_("Имя пользователя или Email"),
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Введите имя пользователя или email")}
        ),
    )
    password = forms.CharField(
        label=_("Пароль"),
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": _("Введите пароль")}
        ),
    )

    error_messages = {
        "invalid_login": _(
            "Пожалуйста, введите правильные имя пользователя и пароль. "
            "Оба поля могут быть чувствительны к регистру."
        ),
        "inactive": _("Этот аккаунт неактивен."),
    }


class CustomUserCreationForm(UserCreationForm):
    """Кастомная форма регистрации пользователя (клиента)."""

    email = forms.EmailField(
        label=_("Email"),
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": _("Введите email")}),
    )
    first_name = forms.CharField(
        label=_("Имя"),
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": _("Введите имя")}),
    )
    last_name = forms.CharField(
        label=_("Фамилия"),
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Введите фамилию")}
        ),
    )

    phone_number = forms.CharField(
        label=_("Телефон"),
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Введите телефон")}
        ),
    )

    password1 = forms.CharField(
        label=_("Пароль"),
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": _("Введите пароль")}
        ),
    )
    password2 = forms.CharField(
        label=_("Подтверждение пароля"),
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": _("Повторите пароль")}
        ),
    )

    terms_accepted = forms.BooleanField(
        label=_("Я согласен с условиями использования"),
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control", "placeholder": _("Введите имя пользователя")}
            ),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.role = User.UserRole.CUSTOMER

        if commit:
            user.save()

            user.profile.phone_number = self.cleaned_data["phone_number"]
            user.profile.save()

        return user


class UserProfileForm(forms.ModelForm):
    """Форма для редактирования профиля пользователя."""

    allergen_ids = forms.ModelMultipleChoiceField(
        queryset=Allergen.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label=_("Аллергены"),
    )

    class Meta:
        model = UserProfile
        fields = ("phone_number", "profile_picture", "date_of_birth", "address", "bio")
        widgets = {
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "date_of_birth": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "profile_picture": forms.FileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        diet_choices = [
            ("vegetarian", _("Вегетарианец")),
            ("vegan", _("Веган")),
            ("gluten_free", _("Без глютена")),
            ("lactose_free", _("Без лактозы")),
            ("no_nuts", _("Без орехов")),
            ("no_seafood", _("Без морепродуктов")),
        ]

        current_prefs = self.instance.dietary_preferences or {}

        for value, label in diet_choices:
            field_name = f"diet_{value}"
            self.fields[field_name] = forms.BooleanField(
                label=label, required=False, initial=current_prefs.get(value, False)
            )

        if self.instance.allergens:
            allergen_ids = self.instance.allergens.get("ids", [])
            self.initial["allergen_ids"] = allergen_ids

    def save(self, commit=True):
        profile = super().save(commit=False)

        dietary_preferences = {}
        for key, value in self.cleaned_data.items():
            if key.startswith("diet_") and value:
                pref_key = key[5:]  # remove 'diet_' prefix
                dietary_preferences[pref_key] = True

        profile.dietary_preferences = dietary_preferences

        allergen_objs = self.cleaned_data.get("allergen_ids", [])
        allergens = {
            "ids": [str(a.id) for a in allergen_objs],
            "names": [a.name for a in allergen_objs],
        }
        profile.allergens = allergens

        if commit:
            profile.save()
        return profile


class CustomPasswordResetForm(PasswordResetForm):
    """Кастомная форма сброса пароля с улучшенным дизайном."""

    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": _("Введите ваш email")}
        ),
    )


class CustomSetPasswordForm(SetPasswordForm):
    """Кастомная форма установки нового пароля с улучшенным дизайном."""

    new_password1 = forms.CharField(
        label=_("Новый пароль"),
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": _("Введите новый пароль")}
        ),
    )
    new_password2 = forms.CharField(
        label=_("Подтверждение пароля"),
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": _("Повторите новый пароль")}
        ),
    )


class UserEditForm(forms.ModelForm):
    """Форма для редактирования базовой информации пользователя."""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }


class StaffUserCreationForm(UserCreationForm):
    """Форма для создания сотрудника администратором или менеджером."""

    email = forms.EmailField(
        label=_("Email"), required=True, widget=forms.EmailInput(attrs={"class": "form-control"})
    )
    first_name = forms.CharField(
        label=_("Имя"), widget=forms.TextInput(attrs={"class": "form-control"})
    )
    last_name = forms.CharField(
        label=_("Фамилия"), widget=forms.TextInput(attrs={"class": "form-control"})
    )
    role = forms.ChoiceField(
        label=_("Роль"),
        choices=User.UserRole.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    restaurant = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label=_("Ресторан"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    is_active_employee = forms.BooleanField(
        label=_("Активный сотрудник"),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    employee_id = forms.CharField(
        label=_("ID сотрудника"),
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    phone_number = forms.CharField(
        label=_("Телефон"), required=False, widget=forms.TextInput(attrs={"class": "form-control"})
    )
    hire_date = forms.DateField(
        label=_("Дата найма"),
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "restaurant",
            "is_active_employee",
            "employee_id",
            "password1",
            "password2",
        )
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from restaurants.models import Restaurant

        self.fields["restaurant"].queryset = Restaurant.objects.filter(is_active=True)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.role = self.cleaned_data["role"]
        user.restaurant = self.cleaned_data["restaurant"]
        user.is_active_employee = self.cleaned_data["is_active_employee"]
        user.employee_id = self.cleaned_data["employee_id"]

        if user.is_restaurant_staff():
            user.is_staff = True

        if commit:
            user.save()

            user.profile.phone_number = self.cleaned_data["phone_number"]
            user.profile.hire_date = self.cleaned_data["hire_date"]
            user.profile.save()

        return user

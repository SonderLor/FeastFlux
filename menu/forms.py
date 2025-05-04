from django import forms
from django.utils.translation import gettext_lazy as _
from django.forms import inlineformset_factory

from .models import Category, MenuItem, Ingredient, Allergen, MenuItemIngredient, Modifier


class CategoryForm(forms.ModelForm):
    """Форма для создания/редактирования категории меню."""

    class Meta:
        model = Category
        fields = ["name", "description", "image", "parent", "order", "is_active", "restaurant"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "image": forms.FileInput(attrs={"class": "form-control"}),
            "parent": forms.Select(attrs={"class": "form-select"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "restaurant": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.restaurant:
            self.fields["parent"].queryset = Category.objects.filter(
                restaurant=self.instance.restaurant, parent__isnull=True
            ).exclude(pk=self.instance.pk)

        if user:
            from restaurants.models import Restaurant

            if user.is_admin():
                self.fields["restaurant"].queryset = Restaurant.objects.filter(is_active=True)
            elif user.is_manager():
                self.fields["restaurant"].queryset = user.managed_restaurants.filter(is_active=True)
            elif user.restaurant:
                self.fields["restaurant"].queryset = Restaurant.objects.filter(
                    id=user.restaurant.id
                )
                self.fields["restaurant"].initial = user.restaurant
                self.fields["restaurant"].widget.attrs["disabled"] = "disabled"
            else:
                self.fields["restaurant"].queryset = Restaurant.objects.none()


class IngredientForm(forms.ModelForm):
    """Форма для создания/редактирования ингредиента."""

    allergens = forms.ModelMultipleChoiceField(
        queryset=Allergen.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "list-unstyled"}),
        label=_("Аллергены"),
    )

    class Meta:
        model = Ingredient
        fields = [
            "name",
            "description",
            "image",
            "allergens",
            "calories_per_100g",
            "protein_per_100g",
            "fat_per_100g",
            "carbs_per_100g",
            "fiber_per_100g",
            "sugar_per_100g",
            "is_vegetarian",
            "is_vegan",
            "is_gluten_free",
            "restaurant",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "image": forms.FileInput(attrs={"class": "form-control"}),
            "calories_per_100g": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "protein_per_100g": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "fat_per_100g": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "carbs_per_100g": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "fiber_per_100g": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "sugar_per_100g": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "is_vegetarian": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_vegan": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_gluten_free": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "restaurant": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            from restaurants.models import Restaurant

            if user.is_admin():
                self.fields["restaurant"].queryset = Restaurant.objects.filter(is_active=True)
            elif user.is_manager():
                self.fields["restaurant"].queryset = user.managed_restaurants.filter(is_active=True)
            elif user.restaurant:
                self.fields["restaurant"].queryset = Restaurant.objects.filter(
                    id=user.restaurant.id
                )
                self.fields["restaurant"].initial = user.restaurant
                self.fields["restaurant"].widget.attrs["disabled"] = "disabled"
            else:
                self.fields["restaurant"].queryset = Restaurant.objects.none()


class MenuItemForm(forms.ModelForm):
    """Форма для создания/редактирования позиции меню."""

    class Meta:
        model = MenuItem
        fields = [
            "name",
            "description",
            "category",
            "price",
            "status",
            "image",
            "is_signature",
            "is_vegetarian",
            "is_vegan",
            "is_gluten_free",
            "is_lactose_free",
            "spicy_level",
            "serving_size",
            "preparation_time",
            "restaurant",
            "is_active",
            "order_in_category",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "image": forms.FileInput(attrs={"class": "form-control"}),
            "is_signature": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_vegetarian": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_vegan": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_gluten_free": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_lactose_free": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "spicy_level": forms.Select(attrs={"class": "form-select"}),
            "serving_size": forms.TextInput(attrs={"class": "form-control"}),
            "preparation_time": forms.NumberInput(attrs={"class": "form-control"}),
            "restaurant": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "order_in_category": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            from restaurants.models import Restaurant

            if user.is_admin():
                self.fields["restaurant"].queryset = Restaurant.objects.filter(is_active=True)
                if "restaurant" in self.data:
                    try:
                        restaurant_id = str(self.data.get("restaurant"))
                        self.fields["category"].queryset = Category.objects.filter(
                            restaurant_id=restaurant_id, is_active=True
                        )
                    except (ValueError, TypeError):
                        pass
                elif self.instance.pk:
                    self.fields["category"].queryset = Category.objects.filter(
                        restaurant=self.instance.restaurant, is_active=True
                    )
            elif user.is_manager():
                managed_restaurants = user.managed_restaurants.filter(is_active=True)
                self.fields["restaurant"].queryset = managed_restaurants

                if managed_restaurants.count() == 1:
                    self.fields["restaurant"].initial = managed_restaurants.first()

                if self.instance.pk:
                    self.fields["category"].queryset = Category.objects.filter(
                        restaurant=self.instance.restaurant, is_active=True
                    )
                elif "restaurant" in self.data:
                    try:
                        restaurant_id = str(self.data.get("restaurant"))
                        self.fields["category"].queryset = Category.objects.filter(
                            restaurant_id=restaurant_id, is_active=True
                        )
                    except (ValueError, TypeError):
                        pass
                else:
                    self.fields["category"].queryset = Category.objects.filter(
                        restaurant__in=managed_restaurants, is_active=True
                    )
            elif user.restaurant:
                self.fields["restaurant"].queryset = Restaurant.objects.filter(
                    id=user.restaurant.id
                )
                self.fields["restaurant"].initial = user.restaurant
                self.fields["restaurant"].widget.attrs["disabled"] = "disabled"
                self.fields["category"].queryset = Category.objects.filter(
                    restaurant=user.restaurant, is_active=True
                )
            else:
                self.fields["restaurant"].queryset = Restaurant.objects.none()
                self.fields["category"].queryset = Category.objects.none()


class MenuItemIngredientForm(forms.ModelForm):
    """Форма для добавления/редактирования ингредиента в блюде."""

    class Meta:
        model = MenuItemIngredient
        fields = ["ingredient", "amount_grams", "is_main", "is_visible", "notes", "order"]
        widgets = {
            "ingredient": forms.Select(attrs={"class": "form-select"}),
            "amount_grams": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "is_main": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_visible": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notes": forms.TextInput(attrs={"class": "form-control"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        menu_item = kwargs.pop("menu_item", None)
        super().__init__(*args, **kwargs)

        if menu_item and menu_item.restaurant:
            self.fields["ingredient"].queryset = Ingredient.objects.filter(
                restaurant=menu_item.restaurant
            )


MenuItemIngredientFormSet = inlineformset_factory(
    MenuItem,
    MenuItemIngredient,
    form=MenuItemIngredientForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class ModifierForm(forms.ModelForm):
    """Форма для создания/редактирования модификатора."""

    applicable_items = forms.ModelMultipleChoiceField(
        queryset=MenuItem.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "list-unstyled"}),
        label=_("Применимо к блюдам"),
    )

    class Meta:
        model = Modifier
        fields = [
            "name",
            "description",
            "modifier_type",
            "price_change",
            "applicable_items",
            "related_ingredient",
            "restaurant",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "modifier_type": forms.Select(attrs={"class": "form-select"}),
            "price_change": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "related_ingredient": forms.Select(attrs={"class": "form-select"}),
            "restaurant": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            from restaurants.models import Restaurant

            if user.is_admin():
                self.fields["restaurant"].queryset = Restaurant.objects.filter(is_active=True)
                if "restaurant" in self.data:
                    try:
                        restaurant_id = str(self.data.get("restaurant"))
                        self.fields["applicable_items"].queryset = MenuItem.objects.filter(
                            restaurant_id=restaurant_id, is_active=True
                        )
                        self.fields["related_ingredient"].queryset = Ingredient.objects.filter(
                            restaurant_id=restaurant_id
                        )
                    except (ValueError, TypeError):
                        pass
                elif self.instance.pk:
                    self.fields["applicable_items"].queryset = MenuItem.objects.filter(
                        restaurant=self.instance.restaurant, is_active=True
                    )
                    self.fields["related_ingredient"].queryset = Ingredient.objects.filter(
                        restaurant=self.instance.restaurant
                    )
            elif user.is_manager():
                managed_restaurants = user.managed_restaurants.filter(is_active=True)
                self.fields["restaurant"].queryset = managed_restaurants

                if managed_restaurants.count() == 1:
                    self.fields["restaurant"].initial = managed_restaurants.first()

                if self.instance.pk:
                    self.fields["applicable_items"].queryset = MenuItem.objects.filter(
                        restaurant=self.instance.restaurant, is_active=True
                    )
                    self.fields["related_ingredient"].queryset = Ingredient.objects.filter(
                        restaurant=self.instance.restaurant
                    )
                elif "restaurant" in self.data:
                    try:
                        restaurant_id = str(self.data.get("restaurant"))
                        self.fields["applicable_items"].queryset = MenuItem.objects.filter(
                            restaurant_id=restaurant_id, is_active=True
                        )
                        self.fields["related_ingredient"].queryset = Ingredient.objects.filter(
                            restaurant_id=restaurant_id
                        )
                    except (ValueError, TypeError):
                        pass
                else:
                    self.fields["applicable_items"].queryset = MenuItem.objects.filter(
                        restaurant__in=managed_restaurants, is_active=True
                    )
                    self.fields["related_ingredient"].queryset = Ingredient.objects.filter(
                        restaurant__in=managed_restaurants
                    )
            elif user.restaurant:
                self.fields["restaurant"].queryset = Restaurant.objects.filter(
                    id=user.restaurant.id
                )
                self.fields["restaurant"].initial = user.restaurant
                self.fields["restaurant"].widget.attrs["disabled"] = "disabled"
                self.fields["applicable_items"].queryset = MenuItem.objects.filter(
                    restaurant=user.restaurant, is_active=True
                )
                self.fields["related_ingredient"].queryset = Ingredient.objects.filter(
                    restaurant=user.restaurant
                )
            else:
                self.fields["restaurant"].queryset = Restaurant.objects.none()
                self.fields["applicable_items"].queryset = MenuItem.objects.none()
                self.fields["related_ingredient"].queryset = Ingredient.objects.none()


class MenuFilterForm(forms.Form):
    """Форма для фильтрации меню."""

    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label=_("Все категории"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Поиск по названию или описанию")}
        ),
    )

    is_vegetarian = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label=_("Вегетарианское"),
    )

    is_vegan = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label=_("Веганское"),
    )

    is_gluten_free = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label=_("Без глютена"),
    )

    is_lactose_free = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label=_("Без лактозы"),
    )

    max_price = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "10"}),
        label=_("Максимальная цена"),
    )

    spicy_level = forms.ChoiceField(
        choices=[("", _("Любой уровень остроты"))] + list(MenuItem.SpicyLevel.choices),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        label=_("Уровень остроты"),
    )

    def __init__(self, *args, **kwargs):
        restaurant = kwargs.pop("restaurant", None)
        super().__init__(*args, **kwargs)

        if restaurant:
            self.fields["category"].queryset = Category.objects.filter(
                restaurant=restaurant, is_active=True
            )

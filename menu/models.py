import uuid
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from restaurants.models import Restaurant


class Category(models.Model):
    """
    Категории блюд в меню (например, Супы, Салаты, Десерты и т.д.)
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('Уникальный идентификатор')
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_('Название категории')
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Описание')
    )
    image = models.ImageField(
        upload_to='menu_categories/',
        blank=True,
        null=True,
        verbose_name=_('Изображение')
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subcategories',
        verbose_name=_('Родительская категория')
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Порядок отображения')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Активна')
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='menu_categories',
        null=True,
        blank=True,
        verbose_name=_('Ресторан')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата создания')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Дата обновления')
    )

    class Meta:
        verbose_name = _('Категория меню')
        verbose_name_plural = _('Категории меню')
        ordering = ['order', 'name']
        unique_together = [['name', 'restaurant']]

    def __str__(self):
        if self.restaurant:
            return f"{self.name} ({self.restaurant.name})"
        return self.name

    def get_active_items_count(self):
        """Возвращает количество активных позиций в категории"""
        return self.menu_items.filter(is_active=True).count()


class Allergen(models.Model):
    """
    Модель для представления аллергенов (глютен, лактоза, орехи и т.д.)
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('Уникальный идентификатор')
    )
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Название аллергена')
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Описание')
    )
    icon = models.ImageField(
        upload_to='allergen_icons/',
        blank=True,
        null=True,
        verbose_name=_('Иконка')
    )
    severity_level = models.PositiveSmallIntegerField(
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        verbose_name=_('Уровень опасности'),
        help_text=_('От 1 (низкий) до 3 (высокий)')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата создания')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Дата обновления')
    )

    class Meta:
        verbose_name = _('Аллерген')
        verbose_name_plural = _('Аллергены')
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_menu_items_count(self):
        """Возвращает количество блюд, содержащих этот аллерген"""
        ingredient_ids = self.ingredients.values_list('id', flat=True)
        menu_items = set()
        for ing_id in ingredient_ids:
            for menu_item_ing in MenuItemIngredient.objects.filter(ingredient_id=ing_id):
                menu_items.add(menu_item_ing.menu_item_id)
        return len(menu_items)


class Ingredient(models.Model):
    """
    Модель для представления ингредиентов с их пищевой ценностью.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('Уникальный идентификатор')
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_('Название ингредиента')
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Описание')
    )
    image = models.ImageField(
        upload_to='ingredient_images/',
        blank=True,
        null=True,
        verbose_name=_('Изображение')
    )
    allergens = models.ManyToManyField(
        Allergen,
        blank=True,
        related_name='ingredients',
        verbose_name=_('Аллергены')
    )

    calories_per_100g = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name=_('Калории (на 100г)')
    )
    protein_per_100g = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name=_('Белки (на 100г)')
    )
    fat_per_100g = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name=_('Жиры (на 100г)')
    )
    carbs_per_100g = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name=_('Углеводы (на 100г)')
    )
    fiber_per_100g = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name=_('Клетчатка (на 100г)')
    )
    sugar_per_100g = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name=_('Сахара (на 100г)')
    )

    is_vegetarian = models.BooleanField(
        default=False,
        verbose_name=_('Вегетарианский')
    )
    is_vegan = models.BooleanField(
        default=False,
        verbose_name=_('Веганский')
    )
    is_gluten_free = models.BooleanField(
        default=False,
        verbose_name=_('Без глютена')
    )

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='ingredients',
        null=True,
        blank=True,
        verbose_name=_('Ресторан')
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_ingredients',
        verbose_name=_('Кто создал')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата создания')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Дата обновления')
    )

    class Meta:
        verbose_name = _('Ингредиент')
        verbose_name_plural = _('Ингредиенты')
        ordering = ['name']
        unique_together = [['name', 'restaurant']]

    def __str__(self):
        if self.restaurant:
            return f"{self.name} ({self.restaurant.name})"
        return self.name

    def get_allergens_list(self):
        """Возвращает список аллергенов ингредиента"""
        return list(self.allergens.values_list('name', flat=True))


class MenuItem(models.Model):
    """
    Модель для представления позиции меню (блюда или напитка).
    """

    class MenuItemStatus(models.TextChoices):
        AVAILABLE = 'AVAILABLE', _('Доступно')
        UNAVAILABLE = 'UNAVAILABLE', _('Недоступно')
        SEASONAL = 'SEASONAL', _('Сезонное')
        COMING_SOON = 'COMING_SOON', _('Скоро в меню')

    class SpicyLevel(models.IntegerChoices):
        NOT_SPICY = 0, _('Не острое')
        MILD = 1, _('Слабо острое')
        MEDIUM = 2, _('Средне острое')
        HOT = 3, _('Острое')
        VERY_HOT = 4, _('Очень острое')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('Уникальный идентификатор')
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_('Название блюда')
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Описание')
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='menu_items',
        verbose_name=_('Категория')
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Цена')
    )
    status = models.CharField(
        max_length=20,
        choices=MenuItemStatus.choices,
        default=MenuItemStatus.AVAILABLE,
        verbose_name=_('Статус')
    )

    ingredients = models.ManyToManyField(
        Ingredient,
        through='MenuItemIngredient',
        related_name='menu_items',
        verbose_name=_('Ингредиенты')
    )

    image = models.ImageField(
        upload_to='menu_items/',
        blank=True,
        null=True,
        verbose_name=_('Основное изображение')
    )
    additional_images = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('Дополнительные изображения'),
        help_text=_('JSON массив с URL изображений')
    )

    is_signature = models.BooleanField(
        default=False,
        verbose_name=_('Фирменное блюдо')
    )
    is_vegetarian = models.BooleanField(
        default=False,
        verbose_name=_('Вегетарианское')
    )
    is_vegan = models.BooleanField(
        default=False,
        verbose_name=_('Веганское')
    )
    is_gluten_free = models.BooleanField(
        default=False,
        verbose_name=_('Без глютена')
    )
    is_lactose_free = models.BooleanField(
        default=False,
        verbose_name=_('Без лактозы')
    )
    spicy_level = models.PositiveSmallIntegerField(
        choices=SpicyLevel.choices,
        default=SpicyLevel.NOT_SPICY,
        verbose_name=_('Уровень остроты')
    )

    serving_size = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_('Размер порции')
    )
    preparation_time = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name=_('Время приготовления (мин)')
    )

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name=_('Ресторан')
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Активно')
    )

    order_in_category = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Порядок в категории')
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_menu_items',
        verbose_name=_('Кто создал')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата создания')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Дата обновления')
    )

    class Meta:
        verbose_name = _('Позиция меню')
        verbose_name_plural = _('Позиции меню')
        ordering = ['category', 'order_in_category', 'name']
        unique_together = [['name', 'restaurant', 'category']]
        indexes = [
            models.Index(fields=['restaurant', 'category', 'is_active']),
            models.Index(fields=['is_vegetarian', 'is_vegan', 'is_gluten_free']),
        ]

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"

    def calculate_total_nutrition(self):
        """
        Рассчитывает общую пищевую ценность блюда на основе ингредиентов и их количества.
        """
        total_calories = Decimal('0')
        total_protein = Decimal('0')
        total_fat = Decimal('0')
        total_carbs = Decimal('0')
        total_fiber = Decimal('0')
        total_sugar = Decimal('0')

        for item_ingredient in self.menuitemingredient_set.all():
            weight_ratio = Decimal(item_ingredient.amount_grams) / Decimal(
                '100.0')

            total_calories += item_ingredient.ingredient.calories_per_100g * weight_ratio
            total_protein += item_ingredient.ingredient.protein_per_100g * weight_ratio
            total_fat += item_ingredient.ingredient.fat_per_100g * weight_ratio
            total_carbs += item_ingredient.ingredient.carbs_per_100g * weight_ratio
            total_fiber += item_ingredient.ingredient.fiber_per_100g * weight_ratio
            total_sugar += item_ingredient.ingredient.sugar_per_100g * weight_ratio

        return {
            'calories': round(total_calories, 2),
            'protein': round(total_protein, 2),
            'fat': round(total_fat, 2),
            'carbs': round(total_carbs, 2),
            'fiber': round(total_fiber, 2),
            'sugar': round(total_sugar, 2),
        }

    def get_allergens(self):
        """
        Возвращает список всех аллергенов, присутствующих в блюде.
        """
        allergens = set()
        for item_ingredient in self.menuitemingredient_set.select_related('ingredient').prefetch_related(
                'ingredient__allergens'):
            for allergen in item_ingredient.ingredient.allergens.all():
                allergens.add(allergen)
        return list(allergens)

    def update_dietary_flags(self):
        """
        Автоматически обновляет флаги диетических ограничений на основе ингредиентов.
        """
        ingredients = self.ingredients.all()
        if not ingredients.exists():
            return

        self.is_vegetarian = True
        self.is_vegan = True
        self.is_gluten_free = True
        self.is_lactose_free = True

        for ingredient in ingredients:
            if not ingredient.is_vegetarian:
                self.is_vegetarian = False
                self.is_vegan = False

            if self.is_vegan and not ingredient.is_vegan:
                self.is_vegan = False

            if self.is_gluten_free:
                allergens = ingredient.allergens.filter(name__icontains='глютен').exists()
                if allergens or not ingredient.is_gluten_free:
                    self.is_gluten_free = False

            if self.is_lactose_free:
                allergens = ingredient.allergens.filter(name__icontains='лактоза').exists()
                if allergens:
                    self.is_lactose_free = False

        self.save(update_fields=['is_vegetarian', 'is_vegan', 'is_gluten_free', 'is_lactose_free'])


class MenuItemIngredient(models.Model):
    """
    Промежуточная модель для связи между MenuItem и Ingredient
    с указанием количества ингредиента.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('Уникальный идентификатор')
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        verbose_name=_('Позиция меню')
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.PROTECT,
        verbose_name=_('Ингредиент')
    )
    amount_grams = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Количество (грамм)')
    )
    is_main = models.BooleanField(
        default=True,
        verbose_name=_('Основной ингредиент'),
        help_text=_('Указывает, является ли ингредиент основным в блюде')
    )
    is_visible = models.BooleanField(
        default=True,
        verbose_name=_('Отображать в меню'),
        help_text=_('Отображать ли ингредиент в описании блюда')
    )
    notes = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('Примечания')
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_('Порядок')
    )

    class Meta:
        verbose_name = _('Ингредиент в блюде')
        verbose_name_plural = _('Ингредиенты в блюдах')
        ordering = ['menu_item', 'order', 'ingredient__name']
        unique_together = [['menu_item', 'ingredient']]

    def __str__(self):
        return f"{self.ingredient.name} ({self.amount_grams}г) в {self.menu_item.name}"

    def get_nutrition_values(self):
        """
        Рассчитывает пищевую ценность для данного количества ингредиента.
        """
        weight_ratio = self.amount_grams / Decimal('100.0')

        return {
            'calories': round(self.ingredient.calories_per_100g * weight_ratio, 2),
            'protein': round(self.ingredient.protein_per_100g * weight_ratio, 2),
            'fat': round(self.ingredient.fat_per_100g * weight_ratio, 2),
            'carbs': round(self.ingredient.carbs_per_100g * weight_ratio, 2),
            'fiber': round(self.ingredient.fiber_per_100g * weight_ratio, 2),
            'sugar': round(self.ingredient.sugar_per_100g * weight_ratio, 2),
        }


class Modifier(models.Model):
    """
    Модель для представления модификаторов блюд (например, "без лука", "двойная порция", "острый").
    """

    class ModifierType(models.TextChoices):
        ADDITION = 'ADDITION', _('Добавка')
        REMOVAL = 'REMOVAL', _('Убрать ингредиент')
        SUBSTITUTION = 'SUBSTITUTION', _('Замена')
        PREPARATION = 'PREPARATION', _('Способ приготовления')
        SIZE = 'SIZE', _('Размер порции')
        OTHER = 'OTHER', _('Другое')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('Уникальный идентификатор')
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_('Название модификатора')
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Описание')
    )
    modifier_type = models.CharField(
        max_length=20,
        choices=ModifierType.choices,
        default=ModifierType.OTHER,
        verbose_name=_('Тип модификатора')
    )
    price_change = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Изменение цены'),
        help_text=_('Положительное значение для надбавки, отрицательное для скидки')
    )

    applicable_items = models.ManyToManyField(
        MenuItem,
        related_name='available_modifiers',
        blank=True,
        verbose_name=_('Применимо к блюдам')
    )

    related_ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='modifiers',
        verbose_name=_('Связанный ингредиент')
    )

    nutrition_impact = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('Влияние на пищевую ценность'),
        help_text=_('JSON с изменениями КБЖУ, например: {"calories": 50, "protein": 5}')
    )

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='modifiers',
        verbose_name=_('Ресторан')
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Активен')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата создания')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Дата обновления')
    )

    class Meta:
        verbose_name = _('Модификатор')
        verbose_name_plural = _('Модификаторы')
        ordering = ['restaurant', 'name']
        unique_together = [['name', 'restaurant']]

    def __str__(self):
        price_display = ""
        if self.price_change > 0:
            price_display = f" (+{self.price_change})"
        elif self.price_change < 0:
            price_display = f" ({self.price_change})"

        return f"{self.name}{price_display} ({self.restaurant.name})"

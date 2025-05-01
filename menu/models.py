from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_('Название категории'))
    description = models.TextField(blank=True, null=True, verbose_name=_('Описание'))

    class Meta:
        verbose_name = _('Категория меню')
        verbose_name_plural = _('Категории меню')
        ordering = ['name']

    def __str__(self):
        return self.name

class Allergen(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_('Название аллергена'))

    class Meta:
        verbose_name = _('Аллерген')
        verbose_name_plural = _('Аллергены')
        ordering = ['name']

    def __str__(self):
        return self.name

class Ingredient(models.Model):
    name = models.CharField(max_length=150, unique=True, verbose_name=_('Название ингредиента'))

    calories_per_100g = models.DecimalField(
        max_digits=7, decimal_places=2, default=0.00,
        validators=[MinValueValidator(Decimal('0.00'))], verbose_name=_('Калории (на 100г)')
    )
    protein_per_100g = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00,
        validators=[MinValueValidator(Decimal('0.00'))], verbose_name=_('Белки (на 100г)')
    )
    fat_per_100g = models.DecimalField(
         max_digits=5, decimal_places=2, default=0.00,
         validators=[MinValueValidator(Decimal('0.00'))], verbose_name=_('Жиры (на 100г)')
    )
    carbs_per_100g = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00,
        validators=[MinValueValidator(Decimal('0.00'))], verbose_name=_('Углеводы (на 100г)')
    )
    allergens = models.ManyToManyField(
        Allergen, blank=True, related_name='ingredients', verbose_name=_('Аллергены')
    )

    class Meta:
        verbose_name = _('Ингредиент')
        verbose_name_plural = _('Ингредиенты')
        ordering = ['name']

    def __str__(self):
        return self.name

class MenuItem(models.Model):
    class MenuItemStatus(models.TextChoices):
        AVAILABLE = 'AV', _('Доступно')
        UNAVAILABLE = 'UN', _('Недоступно')

    name = models.CharField(max_length=150, verbose_name=_('Название блюда/напитка'))
    description = models.TextField(blank=True, verbose_name=_('Описание'))
    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))], verbose_name=_('Цена')
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT,
        related_name='menu_items', verbose_name=_('Категория')
    )
    image = models.ImageField(upload_to='menu_images/', blank=True, null=True, verbose_name=_('Фотография'))
    status = models.CharField(
        max_length=2, choices=MenuItemStatus.choices,
        default=MenuItemStatus.AVAILABLE, verbose_name=_('Статус')
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='MenuItemIngredient',
        related_name='menu_items',
        verbose_name=_('Ингредиенты')
    )

    is_vegetarian = models.BooleanField(default=False, verbose_name=_('Вегетарианское'))
    is_vegan = models.BooleanField(default=False, verbose_name=_('Веганское'))
    is_gluten_free = models.BooleanField(default=False, verbose_name=_('Без глютена'))
    is_lactose_free = models.BooleanField(default=False, verbose_name=_('Без лактозы'))

    preparation_time = models.DurationField(blank=True, null=True, verbose_name=_('Время приготовления'))
    recipe_instructions = models.TextField(blank=True, null=True, verbose_name=_('Инструкции по приготовлению'))

    class Meta:
        verbose_name = _('Позиция меню')
        verbose_name_plural = _('Позиции меню')
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.category.name})"

    @property
    def calculated_calories(self):
        # TODO: Реализовать расчет на основе MenuItemIngredient
        total_calories = Decimal('0.0')
        for item_ingredient in self.menuitemingredient_set.all():
            total_calories += item_ingredient.get_ingredient_calories()
        return round(total_calories, 2)

    @property
    def calculated_protein(self):
        # TODO: Реализовать расчет
        total_protein = Decimal('0.0')
        for item_ingredient in self.menuitemingredient_set.all():
            total_protein += item_ingredient.get_ingredient_protein()
        return round(total_protein, 2)

    @property
    def calculated_fat(self):
        # TODO: Реализовать расчет
        total_fat = Decimal('0.0')
        for item_ingredient in self.menuitemingredient_set.all():
            total_fat += item_ingredient.get_ingredient_fat()
        return round(total_fat, 2)

    @property
    def calculated_carbs(self):
        # TODO: Реализовать расчет
        total_carbs = Decimal('0.0')
        for item_ingredient in self.menuitemingredient_set.all():
            total_carbs += item_ingredient.get_ingredient_carbs()
        return round(total_carbs, 2)

    @property
    def present_allergens(self):
        # TODO: Реализовать получение списка аллергенов из ингредиентов
        allergens = set()
        for item_ingredient in self.menuitemingredient_set.all():
            allergens.update(item_ingredient.ingredient.allergens.all())
        return list(allergens)

class MenuItemIngredient(models.Model):
    """Промежуточная модель для связи Блюда и Ингредиента с указанием количества"""
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    # Количество ингредиента в граммах (или мл для жидкостей)
    amount_grams = models.DecimalField(
        max_digits=7, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))], verbose_name=_('Количество (гр)')
    )

    class Meta:
        verbose_name = _('Ингредиент в блюде')
        verbose_name_plural = _('Ингредиенты в блюдах')
        unique_together = ('menu_item', 'ingredient')

    def __str__(self):
        return f"{self.ingredient.name} для {self.menu_item.name} ({self.amount_grams} гр)"

    def get_ingredient_calories(self):
        return (self.ingredient.calories_per_100g * self.amount_grams) / Decimal('100.0')

    def get_ingredient_protein(self):
        return (self.ingredient.protein_per_100g * self.amount_grams) / Decimal('100.0')

    def get_ingredient_fat(self):
        return (self.ingredient.fat_per_100g * self.amount_grams) / Decimal('100.0')

    def get_ingredient_carbs(self):
        return (self.ingredient.carbs_per_100g * self.amount_grams) / Decimal('100.0')


class Modifier(models.Model):
    name = models.CharField(max_length=100, verbose_name=_('Название модификатора'))
    price_change = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, verbose_name=_('Изменение цены'))

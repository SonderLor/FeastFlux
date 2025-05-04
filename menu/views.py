from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string

from restaurants.models import Restaurant
from .models import Category, MenuItem, Ingredient, Allergen, MenuItemIngredient, Modifier
from .forms import (
    CategoryForm,
    IngredientForm,
    MenuItemForm,
    MenuItemIngredientFormSet,
    ModifierForm,
    MenuFilterForm,
)


def public_menu(request, restaurant_id):
    """Публичный просмотр меню ресторана для посетителей."""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)

    root_categories = Category.objects.filter(
        restaurant=restaurant, is_active=True, parent__isnull=True
    ).order_by("order", "name")

    form = MenuFilterForm(request.GET, restaurant=restaurant)

    menu_items = MenuItem.objects.filter(
        restaurant=restaurant, is_active=True, status=MenuItem.MenuItemStatus.AVAILABLE
    )

    if form.is_valid():
        category = form.cleaned_data.get("category")
        search = form.cleaned_data.get("search")
        is_vegetarian = form.cleaned_data.get("is_vegetarian")
        is_vegan = form.cleaned_data.get("is_vegan")
        is_gluten_free = form.cleaned_data.get("is_gluten_free")
        is_lactose_free = form.cleaned_data.get("is_lactose_free")
        max_price = form.cleaned_data.get("max_price")
        spicy_level = form.cleaned_data.get("spicy_level")

        if category:
            category_ids = [category.id]
            subcategories = Category.objects.filter(parent=category, is_active=True)
            category_ids.extend(list(subcategories.values_list("id", flat=True)))

            menu_items = menu_items.filter(category_id__in=category_ids)

        if search:
            menu_items = menu_items.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        if is_vegetarian:
            menu_items = menu_items.filter(is_vegetarian=True)

        if is_vegan:
            menu_items = menu_items.filter(is_vegan=True)

        if is_gluten_free:
            menu_items = menu_items.filter(is_gluten_free=True)

        if is_lactose_free:
            menu_items = menu_items.filter(is_lactose_free=True)

        if max_price:
            menu_items = menu_items.filter(price__lte=max_price)

        if spicy_level:
            menu_items = menu_items.filter(spicy_level=spicy_level)

    categories_with_items = {}
    for category in root_categories:
        category_ids = [category.id]
        subcategories = Category.objects.filter(parent=category, is_active=True)

        if subcategories.exists():
            category_ids.extend(list(subcategories.values_list("id", flat=True)))
            categories_with_items[category] = {
                "items": menu_items.filter(category_id__in=category_ids).order_by(
                    "order_in_category", "name"
                ),
                "subcategories": subcategories,
            }
        else:
            categories_with_items[category] = {
                "items": menu_items.filter(category=category).order_by("order_in_category", "name"),
                "subcategories": [],
            }

    signature_items = menu_items.filter(is_signature=True).order_by("?")[:6]

    context = {
        "restaurant": restaurant,
        "categories_with_items": categories_with_items,
        "signature_items": signature_items,
        "form": form,
    }

    return render(request, "menu/public_menu.html", context)


@login_required
@permission_required("menu.view_menuitem", raise_exception=True)
def menu_view(request, restaurant_id=None):
    """Просмотр меню ресторана для авторизованных сотрудников."""
    user = request.user

    if restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)

        if user.is_waiter() and (not user.restaurant or user.restaurant.id != restaurant.id):
            messages.error(request, _("У вас нет доступа к этому ресторану."))
            return redirect("restaurant_list")
    elif user.restaurant:
        restaurant = user.restaurant
    else:
        if user.is_admin():
            restaurants = Restaurant.objects.filter(is_active=True)
        elif user.is_manager():
            restaurants = user.managed_restaurants.filter(is_active=True)
        else:
            messages.error(request, _("У вас нет доступа к ресторанам."))
            return redirect("home")

        if restaurants.count() == 1:
            restaurant = restaurants.first()
        else:
            context = {
                "restaurants": restaurants,
            }
            return render(request, "menu/select_restaurant.html", context)

    form = MenuFilterForm(request.GET, restaurant=restaurant)

    menu_items = MenuItem.objects.filter(restaurant=restaurant)

    if form.is_valid():
        category = form.cleaned_data.get("category")
        search = form.cleaned_data.get("search")
        is_vegetarian = form.cleaned_data.get("is_vegetarian")
        is_vegan = form.cleaned_data.get("is_vegan")
        is_gluten_free = form.cleaned_data.get("is_gluten_free")
        is_lactose_free = form.cleaned_data.get("is_lactose_free")
        max_price = form.cleaned_data.get("max_price")
        spicy_level = form.cleaned_data.get("spicy_level")

        if category:
            category_ids = [category.id]
            subcategories = Category.objects.filter(parent=category, is_active=True)
            category_ids.extend(list(subcategories.values_list("id", flat=True)))

            menu_items = menu_items.filter(category_id__in=category_ids)

        if search:
            menu_items = menu_items.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        if is_vegetarian:
            menu_items = menu_items.filter(is_vegetarian=True)

        if is_vegan:
            menu_items = menu_items.filter(is_vegan=True)

        if is_gluten_free:
            menu_items = menu_items.filter(is_gluten_free=True)

        if is_lactose_free:
            menu_items = menu_items.filter(is_lactose_free=True)

        if max_price:
            menu_items = menu_items.filter(price__lte=max_price)

        if spicy_level:
            menu_items = menu_items.filter(spicy_level=spicy_level)

    paginator = Paginator(menu_items.order_by("category__name", "order_in_category", "name"), 18)
    page = request.GET.get("page")

    try:
        menu_items_page = paginator.page(page)
    except PageNotAnInteger:
        menu_items_page = paginator.page(1)
    except EmptyPage:
        menu_items_page = paginator.page(paginator.num_pages)

    categories = Category.objects.filter(restaurant=restaurant, is_active=True)

    context = {
        "restaurant": restaurant,
        "menu_items": menu_items_page,
        "categories": categories,
        "form": form,
    }

    return render(request, "menu/menu_view.html", context)


@login_required
@permission_required("menu.manage_menu", raise_exception=True)
def menu_management(request, restaurant_id=None):
    """Интерфейс для управления меню ресторана."""
    user = request.user

    if restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)

        if user.is_manager() and not user.managed_restaurants.filter(id=restaurant.id).exists():
            messages.error(request, _("У вас нет прав на управление меню этого ресторана."))
            return redirect("restaurant_list")
    elif user.restaurant:
        restaurant = user.restaurant
    else:
        if user.is_admin():
            restaurants = Restaurant.objects.filter(is_active=True)
        elif user.is_manager():
            restaurants = user.managed_restaurants.filter(is_active=True)
        else:
            messages.error(request, _("У вас нет доступа к ресторанам."))
            return redirect("home")

        if restaurants.count() == 1:
            restaurant = restaurants.first()
        else:
            context = {
                "restaurants": restaurants,
                "back_url": request.META.get("HTTP_REFERER", "home"),
            }
            return render(request, "menu/select_restaurant.html", context)

    root_categories = Category.objects.filter(restaurant=restaurant, parent__isnull=True).order_by(
        "order", "name"
    )

    categories_data = []

    for category in root_categories:
        subcategories = []

        for subcategory in Category.objects.filter(parent=category).order_by("order", "name"):
            subcategory_items = MenuItem.objects.filter(category=subcategory).order_by(
                "order_in_category", "name"
            )

            subcategories.append(
                {
                    "category": subcategory,
                    "items": subcategory_items,
                    "items_count": subcategory_items.count(),
                    "active_count": subcategory_items.filter(is_active=True).count(),
                }
            )

        category_items = MenuItem.objects.filter(category=category).order_by(
            "order_in_category", "name"
        )

        categories_data.append(
            {
                "category": category,
                "subcategories": subcategories,
                "items": category_items,
                "items_count": category_items.count(),
                "active_count": category_items.filter(is_active=True).count(),
                "has_inactive": category_items.filter(is_active=False).exists(),
            }
        )

    recent_items = MenuItem.objects.filter(restaurant=restaurant).order_by("-updated_at")[:10]

    total_items = MenuItem.objects.filter(restaurant=restaurant).count()
    active_items = MenuItem.objects.filter(restaurant=restaurant, is_active=True).count()

    context = {
        "restaurant": restaurant,
        "categories_data": categories_data,
        "recent_items": recent_items,
        "total_items": total_items,
        "active_items": active_items,
        "inactive_items": total_items - active_items,
    }

    return render(request, "menu/menu_management.html", context)


@login_required
@permission_required("menu.add_category", raise_exception=True)
def category_create(request, restaurant_id=None):
    """Создание новой категории меню."""
    if restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    elif request.user.restaurant:
        restaurant = request.user.restaurant
    else:
        messages.error(request, _("Необходимо указать ресторан."))
        return redirect("menu_management")

    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            category = form.save(commit=False)
            if not category.restaurant:
                category.restaurant = restaurant
            category.save()

            messages.success(request, _("Категория успешно создана!"))
            return redirect("menu_management", restaurant_id=restaurant.id)
    else:
        form = CategoryForm(user=request.user, initial={"restaurant": restaurant})

    context = {
        "form": form,
        "restaurant": restaurant,
        "is_create": True,
    }

    return render(request, "menu/category_form.html", context)


@login_required
@permission_required("menu.change_category", raise_exception=True)
def category_edit(request, category_id):
    """Редактирование категории меню."""
    category = get_object_or_404(Category, id=category_id)
    restaurant = category.restaurant

    user = request.user
    if (user.is_manager() and not user.managed_restaurants.filter(id=restaurant.id).exists()) or (
        user.is_waiter() and (not user.restaurant or user.restaurant.id != restaurant.id)
    ):
        messages.error(request, _("У вас нет прав на редактирование этой категории."))
        return redirect("menu_management")

    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES, instance=category, user=user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Категория успешно обновлена!"))
            return redirect("menu_management", restaurant_id=restaurant.id)
    else:
        form = CategoryForm(instance=category, user=user)

    context = {
        "form": form,
        "category": category,
        "restaurant": restaurant,
        "is_create": False,
    }

    return render(request, "menu/category_form.html", context)


@login_required
@permission_required("menu.delete_category", raise_exception=True)
def category_delete(request, category_id):
    """Удаление категории меню."""
    category = get_object_or_404(Category, id=category_id)
    restaurant = category.restaurant

    user = request.user
    if user.is_manager() and not user.managed_restaurants.filter(id=restaurant.id).exists():
        messages.error(request, _("У вас нет прав на удаление этой категории."))
        return redirect("menu_management")

    menu_items = MenuItem.objects.filter(category=category)
    subcategories = Category.objects.filter(parent=category)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "delete":
            for subcategory in subcategories:
                MenuItem.objects.filter(category=subcategory).delete()
                subcategory.delete()

            menu_items.delete()
            category.delete()

            messages.success(request, _("Категория успешно удалена!"))
        elif action == "deactivate":
            category.is_active = False
            category.save()

            for subcategory in subcategories:
                subcategory.is_active = False
                subcategory.save()

                MenuItem.objects.filter(category=subcategory).update(is_active=False)

            MenuItem.objects.filter(category=category).update(is_active=False)

            messages.success(request, _("Категория и все её содержимое деактивированы!"))

        return redirect("menu_management", restaurant_id=restaurant.id)

    context = {
        "category": category,
        "restaurant": restaurant,
        "menu_items_count": menu_items.count(),
        "subcategories_count": subcategories.count(),
        "has_dependencies": menu_items.exists() or subcategories.exists(),
    }

    return render(request, "menu/category_delete.html", context)


@login_required
@permission_required("menu.add_menuitem", raise_exception=True)
def menu_item_create(request, restaurant_id=None, category_id=None):
    """Создание новой позиции меню."""
    user = request.user

    if restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    elif user.restaurant:
        restaurant = user.restaurant
    else:
        messages.error(request, _("Необходимо указать ресторан."))
        return redirect("menu_management")

    if user.is_manager() and not user.managed_restaurants.filter(id=restaurant.id).exists():
        messages.error(request, _("У вас нет прав на добавление блюд в этот ресторан."))
        return redirect("menu_management")

    initial_data = {"restaurant": restaurant}
    if category_id:
        category = get_object_or_404(Category, id=category_id, restaurant=restaurant)
        initial_data["category"] = category

    if request.method == "POST":
        form = MenuItemForm(request.POST, request.FILES, user=user)

        formset = MenuItemIngredientFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            menu_item = form.save(commit=False)
            if not menu_item.restaurant:
                menu_item.restaurant = restaurant
            menu_item.created_by = user
            menu_item.save()

            formset.instance = menu_item
            for ingredient_form in formset:
                if ingredient_form.cleaned_data and not ingredient_form.cleaned_data.get(
                    "DELETE", False
                ):
                    ingredient_link = ingredient_form.save(commit=False)
                    ingredient_link.menu_item = menu_item
                    ingredient_link.save()

            menu_item.update_dietary_flags()

            messages.success(request, _("Блюдо успешно создано!"))
            return redirect("menu_item_detail", item_id=menu_item.id)
    else:
        form = MenuItemForm(user=user, initial=initial_data)
        formset = MenuItemIngredientFormSet()

    context = {
        "form": form,
        "formset": formset,
        "restaurant": restaurant,
        "is_create": True,
    }

    return render(request, "menu/menu_item_form.html", context)


@login_required
@permission_required("menu.change_menuitem", raise_exception=True)
def menu_item_edit(request, item_id):
    """Редактирование позиции меню."""
    menu_item = get_object_or_404(MenuItem, id=item_id)
    restaurant = menu_item.restaurant

    user = request.user
    if (user.is_manager() and not user.managed_restaurants.filter(id=restaurant.id).exists()) or (
        user.is_waiter() and (not user.restaurant or user.restaurant.id != restaurant.id)
    ):
        messages.error(request, _("У вас нет прав на редактирование этого блюда."))
        return redirect("menu_management")

    if request.method == "POST":
        form = MenuItemForm(request.POST, request.FILES, instance=menu_item, user=user)
        formset = MenuItemIngredientFormSet(request.POST, instance=menu_item)

        if form.is_valid() and formset.is_valid():
            menu_item = form.save()
            formset.save()

            menu_item.update_dietary_flags()

            messages.success(request, _("Блюдо успешно обновлено!"))
            return redirect("menu_item_detail", item_id=menu_item.id)
    else:
        form = MenuItemForm(instance=menu_item, user=user)
        formset = MenuItemIngredientFormSet(instance=menu_item)

    nutrition = menu_item.calculate_total_nutrition()

    allergens = menu_item.get_allergens()

    context = {
        "form": form,
        "formset": formset,
        "menu_item": menu_item,
        "restaurant": restaurant,
        "is_create": False,
        "nutrition": nutrition,
        "allergens": allergens,
    }

    return render(request, "menu/menu_item_form.html", context)


@login_required
@permission_required("menu.view_menuitem", raise_exception=True)
def menu_item_detail(request, item_id):
    """Просмотр детальной информации о позиции меню."""
    menu_item = get_object_or_404(MenuItem, id=item_id)
    restaurant = menu_item.restaurant

    user = request.user
    if user.is_waiter() and (not user.restaurant or user.restaurant.id != restaurant.id):
        messages.error(request, _("У вас нет прав на просмотр этого блюда."))
        return redirect("menu_management")

    nutrition = menu_item.calculate_total_nutrition()

    allergens = menu_item.get_allergens()

    modifiers = Modifier.objects.filter(
        Q(applicable_items=menu_item) | Q(applicable_items__isnull=True, restaurant=restaurant),
        is_active=True,
    ).distinct()

    ingredients = (
        MenuItemIngredient.objects.filter(menu_item=menu_item)
        .select_related("ingredient")
        .order_by("-is_main", "order", "ingredient__name")
    )

    context = {
        "menu_item": menu_item,
        "restaurant": restaurant,
        "nutrition": nutrition,
        "allergens": allergens,
        "modifiers": modifiers,
        "ingredients": ingredients,
    }

    return render(request, "menu/menu_item_detail.html", context)


@login_required
@permission_required("menu.delete_menuitem", raise_exception=True)
def menu_item_delete(request, item_id):
    """Удаление позиции меню."""
    menu_item = get_object_or_404(MenuItem, id=item_id)
    restaurant = menu_item.restaurant

    user = request.user
    if user.is_manager() and not user.managed_restaurants.filter(id=restaurant.id).exists():
        messages.error(request, _("У вас нет прав на удаление этого блюда."))
        return redirect("menu_management")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "delete":
            menu_item.delete()
            messages.success(request, _("Блюдо успешно удалено!"))
        elif action == "deactivate":
            menu_item.is_active = False
            menu_item.save()
            messages.success(request, _("Блюдо успешно деактивировано!"))

        return redirect("menu_management", restaurant_id=restaurant.id)

    context = {
        "menu_item": menu_item,
        "restaurant": restaurant,
    }

    return render(request, "menu/menu_item_delete.html", context)


@login_required
@permission_required("menu.view_ingredient", raise_exception=True)
def ingredient_list(request, restaurant_id=None):
    """Список всех ингредиентов для ресторана."""
    user = request.user

    if restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)

        if user.is_waiter() and (not user.restaurant or user.restaurant.id != restaurant.id):
            messages.error(request, _("У вас нет доступа к этому ресторану."))
            return redirect("restaurant_list")
    elif user.restaurant:
        restaurant = user.restaurant
    else:
        if user.is_admin():
            restaurants = Restaurant.objects.filter(is_active=True)
        elif user.is_manager():
            restaurants = user.managed_restaurants.filter(is_active=True)
        else:
            messages.error(request, _("У вас нет доступа к ресторанам."))
            return redirect("home")

        if restaurants.count() == 1:
            restaurant = restaurants.first()
        else:
            context = {
                "restaurants": restaurants,
                "back_url": request.META.get("HTTP_REFERER", "home"),
                "action": "ingredients",
            }
            return render(request, "menu/select_restaurant.html", context)

    search_query = request.GET.get("search", "")
    allergen_id = request.GET.get("allergen", "")
    dietary_filter = request.GET.get("dietary", "")

    ingredients = Ingredient.objects.filter(restaurant=restaurant)

    if search_query:
        ingredients = ingredients.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

    if allergen_id:
        try:
            allergen = Allergen.objects.get(id=allergen_id)
            ingredients = ingredients.filter(allergens=allergen)
        except Allergen.DoesNotExist:
            pass

    if dietary_filter:
        if dietary_filter == "vegetarian":
            ingredients = ingredients.filter(is_vegetarian=True)
        elif dietary_filter == "vegan":
            ingredients = ingredients.filter(is_vegan=True)
        elif dietary_filter == "gluten_free":
            ingredients = ingredients.filter(is_gluten_free=True)

    paginator = Paginator(ingredients.order_by("name"), 20)
    page = request.GET.get("page")

    try:
        ingredients_page = paginator.page(page)
    except PageNotAnInteger:
        ingredients_page = paginator.page(1)
    except EmptyPage:
        ingredients_page = paginator.page(paginator.num_pages)

    allergens = Allergen.objects.all().order_by("name")

    context = {
        "restaurant": restaurant,
        "ingredients": ingredients_page,
        "allergens": allergens,
        "search_query": search_query,
        "allergen_id": allergen_id,
        "dietary_filter": dietary_filter,
    }

    return render(request, "menu/ingredient_list.html", context)


@login_required
@permission_required("menu.add_ingredient", raise_exception=True)
def ingredient_create(request, restaurant_id=None):
    """Создание нового ингредиента."""
    user = request.user

    if restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    elif user.restaurant:
        restaurant = user.restaurant
    else:
        messages.error(request, _("Необходимо указать ресторан."))
        return redirect("ingredient_list")

    if user.is_manager() and not user.managed_restaurants.filter(id=restaurant.id).exists():
        messages.error(request, _("У вас нет прав на добавление ингредиентов в этот ресторан."))
        return redirect("ingredient_list")

    if request.method == "POST":
        form = IngredientForm(request.POST, request.FILES, user=user)
        if form.is_valid():
            ingredient = form.save(commit=False)
            if not ingredient.restaurant:
                ingredient.restaurant = restaurant
            ingredient.created_by = user
            ingredient.save()

            form.save_m2m()

            messages.success(request, _("Ингредиент успешно создан!"))
            return redirect("ingredient_list", restaurant_id=restaurant.id)
    else:
        form = IngredientForm(user=user, initial={"restaurant": restaurant})

    context = {
        "form": form,
        "restaurant": restaurant,
        "is_create": True,
    }

    return render(request, "menu/ingredient_form.html", context)


@login_required
@permission_required("menu.change_ingredient", raise_exception=True)
def ingredient_edit(request, ingredient_id):
    """Редактирование ингредиента."""
    ingredient = get_object_or_404(Ingredient, id=ingredient_id)
    restaurant = ingredient.restaurant

    user = request.user
    if user.is_manager() and not user.managed_restaurants.filter(id=restaurant.id).exists():
        messages.error(request, _("У вас нет прав на редактирование этого ингредиента."))
        return redirect("ingredient_list")

    if request.method == "POST":
        form = IngredientForm(request.POST, request.FILES, instance=ingredient, user=user)
        if form.is_valid():
            form.save()

            for menu_item in MenuItem.objects.filter(ingredients=ingredient):
                menu_item.update_dietary_flags()

            messages.success(request, _("Ингредиент успешно обновлен!"))
            return redirect("ingredient_list", restaurant_id=restaurant.id)
    else:
        form = IngredientForm(instance=ingredient, user=user)

    menu_items_count = MenuItem.objects.filter(ingredients=ingredient).count()

    context = {
        "form": form,
        "ingredient": ingredient,
        "restaurant": restaurant,
        "is_create": False,
        "menu_items_count": menu_items_count,
    }

    return render(request, "menu/ingredient_form.html", context)


@login_required
@permission_required("menu.delete_ingredient", raise_exception=True)
def ingredient_delete(request, ingredient_id):
    """Удаление ингредиента."""
    ingredient = get_object_or_404(Ingredient, id=ingredient_id)
    restaurant = ingredient.restaurant

    user = request.user
    if user.is_manager() and not user.managed_restaurants.filter(id=restaurant.id).exists():
        messages.error(request, _("У вас нет прав на удаление этого ингредиента."))
        return redirect("ingredient_list")

    menu_items = MenuItem.objects.filter(ingredients=ingredient)

    if request.method == "POST":
        if menu_items.exists() and request.POST.get("confirm") != "yes":
            messages.error(request, _("Ингредиент используется в блюдах. Подтвердите удаление."))
            return redirect("ingredient_delete", ingredient_id=ingredient.id)

        MenuItemIngredient.objects.filter(ingredient=ingredient).delete()

        ingredient.delete()

        messages.success(request, _("Ингредиент успешно удален!"))
        return redirect("ingredient_list", restaurant_id=restaurant.id)

    context = {
        "ingredient": ingredient,
        "restaurant": restaurant,
        "menu_items": menu_items,
        "menu_items_count": menu_items.count(),
    }

    return render(request, "menu/ingredient_delete.html", context)


@login_required
@permission_required("menu.view_modifier", raise_exception=True)
def modifier_list(request, restaurant_id=None):
    """Список всех модификаторов для ресторана."""
    user = request.user

    if restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)

        if user.is_waiter() and (not user.restaurant or user.restaurant.id != restaurant.id):
            messages.error(request, _("У вас нет доступа к этому ресторану."))
            return redirect("restaurant_list")
    elif user.restaurant:
        restaurant = user.restaurant
    else:
        if user.is_admin():
            restaurants = Restaurant.objects.filter(is_active=True)
        elif user.is_manager():
            restaurants = user.managed_restaurants.filter(is_active=True)
        else:
            messages.error(request, _("У вас нет доступа к ресторанам."))
            return redirect("home")

        if restaurants.count() == 1:
            restaurant = restaurants.first()
        else:
            context = {
                "restaurants": restaurants,
                "back_url": request.META.get("HTTP_REFERER", "home"),
                "action": "modifiers",
            }
            return render(request, "menu/select_restaurant.html", context)

    search_query = request.GET.get("search", "")
    modifier_type = request.GET.get("type", "")

    modifiers = Modifier.objects.filter(restaurant=restaurant)

    if search_query:
        modifiers = modifiers.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

    if modifier_type:
        modifiers = modifiers.filter(modifier_type=modifier_type)

    paginator = Paginator(modifiers.order_by("name"), 20)
    page = request.GET.get("page")

    try:
        modifiers_page = paginator.page(page)
    except PageNotAnInteger:
        modifiers_page = paginator.page(1)
    except EmptyPage:
        modifiers_page = paginator.page(paginator.num_pages)

    context = {
        "restaurant": restaurant,
        "modifiers": modifiers_page,
        "search_query": search_query,
        "modifier_type": modifier_type,
        "modifier_types": Modifier.ModifierType.choices,
    }

    return render(request, "menu/modifier_list.html", context)


@login_required
@permission_required("menu.add_modifier", raise_exception=True)
def modifier_create(request, restaurant_id=None):
    """Создание нового модификатора."""
    user = request.user

    if restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    elif user.restaurant:
        restaurant = user.restaurant
    else:
        messages.error(request, _("Необходимо указать ресторан."))
        return redirect("modifier_list")

    if user.is_manager() and not user.managed_restaurants.filter(id=restaurant.id).exists():
        messages.error(request, _("У вас нет прав на добавление модификаторов в этот ресторан."))
        return redirect("modifier_list")

    if request.method == "POST":
        form = ModifierForm(request.POST, user=user)
        if form.is_valid():
            modifier = form.save(commit=False)
            if not modifier.restaurant:
                modifier.restaurant = restaurant
            modifier.save()

            form.save_m2m()

            messages.success(request, _("Модификатор успешно создан!"))
            return redirect("modifier_list", restaurant_id=restaurant.id)
    else:
        form = ModifierForm(user=user, initial={"restaurant": restaurant})

    context = {
        "form": form,
        "restaurant": restaurant,
        "is_create": True,
    }

    return render(request, "menu/modifier_form.html", context)


@login_required
@permission_required("menu.change_modifier", raise_exception=True)
def modifier_edit(request, modifier_id):
    """Редактирование модификатора."""
    modifier = get_object_or_404(Modifier, id=modifier_id)
    restaurant = modifier.restaurant

    user = request.user
    if user.is_manager() and not user.managed_restaurants.filter(id=restaurant.id).exists():
        messages.error(request, _("У вас нет прав на редактирование этого модификатора."))
        return redirect("modifier_list")

    if request.method == "POST":
        form = ModifierForm(request.POST, instance=modifier, user=user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Модификатор успешно обновлен!"))
            return redirect("modifier_list", restaurant_id=restaurant.id)
    else:
        form = ModifierForm(instance=modifier, user=user)

    context = {
        "form": form,
        "modifier": modifier,
        "restaurant": restaurant,
        "is_create": False,
    }

    return render(request, "menu/modifier_form.html", context)


@login_required
@permission_required("menu.delete_modifier", raise_exception=True)
def modifier_delete(request, modifier_id):
    """Удаление модификатора."""
    modifier = get_object_or_404(Modifier, id=modifier_id)
    restaurant = modifier.restaurant

    user = request.user
    if user.is_manager() and not user.managed_restaurants.filter(id=restaurant.id).exists():
        messages.error(request, _("У вас нет прав на удаление этого модификатора."))
        return redirect("modifier_list")

    menu_items_count = modifier.applicable_items.count()

    if request.method == "POST":
        modifier.delete()
        messages.success(request, _("Модификатор успешно удален!"))
        return redirect("modifier_list", restaurant_id=restaurant.id)

    context = {
        "modifier": modifier,
        "restaurant": restaurant,
        "menu_items_count": menu_items_count,
    }

    return render(request, "menu/modifier_delete.html", context)


@login_required
@permission_required("menu.change_menuitem", raise_exception=True)
@require_POST
def toggle_menu_item_status(request, item_id):
    """API для изменения статуса блюда (активно/неактивно)."""
    menu_item = get_object_or_404(MenuItem, id=item_id)

    user = request.user
    if (
        user.is_manager()
        and not user.managed_restaurants.filter(id=menu_item.restaurant.id).exists()
    ):
        return JsonResponse({"success": False, "error": "Permission denied"}, status=403)

    menu_item.is_active = not menu_item.is_active
    menu_item.save()

    return JsonResponse(
        {
            "success": True,
            "is_active": menu_item.is_active,
        }
    )


@login_required
@permission_required("menu.change_category", raise_exception=True)
@require_POST
def toggle_category_status(request, category_id):
    """API для изменения статуса категории (активна/неактивна)."""
    category = get_object_or_404(Category, id=category_id)

    user = request.user
    if (
        user.is_manager()
        and not user.managed_restaurants.filter(id=category.restaurant.id).exists()
    ):
        return JsonResponse({"success": False, "error": "Permission denied"}, status=403)

    category.is_active = not category.is_active
    category.save()

    return JsonResponse(
        {
            "success": True,
            "is_active": category.is_active,
        }
    )


@csrf_exempt
@login_required
@permission_required("menu.view_menuitem", raise_exception=True)
def get_menu_item_info(request, item_id):
    """API для получения информации о блюде."""
    menu_item = get_object_or_404(MenuItem, id=item_id)

    nutrition = menu_item.calculate_total_nutrition()

    allergens = [{"id": str(a.id), "name": a.name} for a in menu_item.get_allergens()]

    ingredients = [
        {
            "id": str(mi.ingredient.id),
            "name": mi.ingredient.name,
            "amount": float(mi.amount_grams),
            "is_main": mi.is_main,
            "is_visible": mi.is_visible,
        }
        for mi in MenuItemIngredient.objects.filter(menu_item=menu_item).select_related(
            "ingredient"
        )
    ]

    modifiers = [
        {
            "id": str(m.id),
            "name": m.name,
            "price_change": float(m.price_change),
            "type": m.modifier_type,
        }
        for m in Modifier.objects.filter(applicable_items=menu_item, is_active=True)
    ]

    data = {
        "id": str(menu_item.id),
        "name": menu_item.name,
        "description": menu_item.description,
        "price": float(menu_item.price),
        "status": menu_item.status,
        "is_active": menu_item.is_active,
        "is_vegetarian": menu_item.is_vegetarian,
        "is_vegan": menu_item.is_vegan,
        "is_gluten_free": menu_item.is_gluten_free,
        "is_lactose_free": menu_item.is_lactose_free,
        "spicy_level": menu_item.spicy_level,
        "spicy_level_display": menu_item.get_spicy_level_display(),
        "nutrition": nutrition,
        "allergens": allergens,
        "ingredients": ingredients,
        "modifiers": modifiers,
        "image_url": menu_item.image.url if menu_item.image else None,
    }

    return JsonResponse(data)


@login_required
@permission_required("menu.view_menuitem", raise_exception=True)
def menu_item_modal(request, item_id):
    """Возвращает HTML для модального окна с информацией о блюде."""
    menu_item = get_object_or_404(MenuItem, id=item_id)

    nutrition = menu_item.calculate_total_nutrition()

    allergens = menu_item.get_allergens()

    ingredients = (
        MenuItemIngredient.objects.filter(menu_item=menu_item, is_visible=True)
        .select_related("ingredient")
        .order_by("-is_main", "order", "ingredient__name")
    )

    modifiers = Modifier.objects.filter(applicable_items=menu_item, is_active=True).order_by("name")

    context = {
        "menu_item": menu_item,
        "nutrition": nutrition,
        "allergens": allergens,
        "ingredients": ingredients,
        "modifiers": modifiers,
    }

    html = render_to_string("menu/partials/menu_item_modal.html", context, request=request)

    return JsonResponse({"html": html})

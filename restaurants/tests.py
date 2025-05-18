import uuid
from datetime import timedelta, datetime, time
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import Restaurant, Table, Reservation
from menu.models import Allergen

User = get_user_model()


class RestaurantModelTestCase(TestCase):
    """Тесты модели Restaurant."""

    def setUp(self):
        self.restaurant = Restaurant.objects.create(
            name="Test Restaurant",
            address="123 Test St",
            city="Test City",
            phone="1234567890",
            email="test@restaurant.com",
            opening_hours={
                "monday": {"open": "09:00", "close": "22:00"},
                "tuesday": {"open": "09:00", "close": "22:00"},
                "wednesday": {"open": "09:00", "close": "22:00"},
                "thursday": {"open": "09:00", "close": "22:00"},
                "friday": {"open": "09:00", "close": "23:00"},
                "saturday": {"open": "10:00", "close": "23:00"},
                "sunday": {"open": "10:00", "close": "22:00"},
            },
        )

    def test_restaurant_creation(self):
        """Тест создания ресторана."""
        self.assertEqual(self.restaurant.name, "Test Restaurant")
        self.assertEqual(self.restaurant.city, "Test City")
        self.assertTrue(self.restaurant.is_active)
        self.assertEqual(self.restaurant.get_table_count(), 0)

    def test_restaurant_str_representation(self):
        """Тест строкового представления ресторана."""
        self.assertEqual(str(self.restaurant), "Test Restaurant (Test City)")

    def test_get_table_count(self):
        """Тест метода get_table_count."""
        Table.objects.create(restaurant=self.restaurant, number=1, capacity=4)
        Table.objects.create(restaurant=self.restaurant, number=2, capacity=2)

        self.assertEqual(self.restaurant.get_table_count(), 2)

    def test_get_active_tables(self):
        """Тест метода get_active_tables."""
        Table.objects.create(restaurant=self.restaurant, number=1, capacity=4, is_active=True)
        Table.objects.create(restaurant=self.restaurant, number=2, capacity=2, is_active=False)

        self.assertEqual(self.restaurant.get_active_tables().count(), 1)

    def test_get_reservations_today(self):
        """Тест метода get_reservations_today."""
        table = Table.objects.create(restaurant=self.restaurant, number=1, capacity=4)

        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)

        Reservation.objects.create(
            restaurant=self.restaurant,
            table=table,
            customer_name="Today Customer",
            customer_email="today@example.com",
            customer_phone="1234567890",
            reservation_date=today,
            reservation_time=time(19, 0),
            end_time=time(21, 0),
        )

        Reservation.objects.create(
            restaurant=self.restaurant,
            table=table,
            customer_name="Tomorrow Customer",
            customer_email="tomorrow@example.com",
            customer_phone="0987654321",
            reservation_date=tomorrow,
            reservation_time=time(19, 0),
            end_time=time(21, 0),
        )

        self.assertEqual(self.restaurant.get_reservations_today().count(), 1)

    def test_get_current_occupancy(self):
        """Тест метода get_current_occupancy."""
        Table.objects.create(
            restaurant=self.restaurant, number=1, capacity=4, status=Table.TableStatus.FREE
        )
        Table.objects.create(
            restaurant=self.restaurant, number=2, capacity=2, status=Table.TableStatus.OCCUPIED
        )
        Table.objects.create(
            restaurant=self.restaurant, number=3, capacity=6, status=Table.TableStatus.OCCUPIED
        )

        self.assertEqual(self.restaurant.get_current_occupancy(), 2)


class TableModelTestCase(TestCase):
    """Тесты модели Table."""

    def setUp(self):
        self.restaurant = Restaurant.objects.create(
            name="Test Restaurant",
            address="123 Test St",
            city="Test City",
            phone="1234567890",
            email="test@restaurant.com",
        )

        self.table = Table.objects.create(
            restaurant=self.restaurant,
            number=1,
            capacity=4,
            shape=Table.TableShape.SQUARE,
            width=80,
            length=80,
        )

    def test_table_creation(self):
        """Тест создания столика."""
        self.assertEqual(self.table.number, 1)
        self.assertEqual(self.table.capacity, 4)
        self.assertEqual(self.table.status, Table.TableStatus.FREE)
        self.assertEqual(self.table.shape, Table.TableShape.SQUARE)
        self.assertEqual(self.table.width, 80)
        self.assertEqual(self.table.length, 80)
        self.assertTrue(self.table.is_active)

    def test_table_str_representation(self):
        """Тест строкового представления столика."""
        self.assertEqual(str(self.table), f"Столик №1 ({self.restaurant.name})")

    def test_is_available_method(self):
        """Тест метода is_available."""
        today = timezone.now().date()
        future_date = today + timedelta(days=2)

        Reservation.objects.create(
            restaurant=self.restaurant,
            table=self.table,
            customer_name="Test Customer",
            customer_email="test@example.com",
            customer_phone="1234567890",
            reservation_date=today,
            reservation_time=time(19, 0),
            end_time=time(21, 0),
            status=Reservation.ReservationStatus.CONFIRMED,
        )

        self.assertFalse(self.table.is_available(today, time(20, 0)))

        self.assertTrue(self.table.is_available(today, time(16, 0)))

        self.assertTrue(self.table.is_available(future_date, time(19, 0)))

        self.table.is_active = False
        self.table.save()
        self.assertFalse(self.table.is_available(future_date, time(19, 0)))

        self.table.is_active = True
        self.table.status = Table.TableStatus.UNAVAILABLE
        self.table.save()
        self.assertFalse(self.table.is_available(future_date, time(19, 0)))


class ReservationModelTestCase(TestCase):
    """Тесты модели Reservation."""

    def setUp(self):
        self.restaurant = Restaurant.objects.create(
            name="Test Restaurant",
            address="123 Test St",
            city="Test City",
            phone="1234567890",
            email="test@restaurant.com",
        )

        self.table = Table.objects.create(restaurant=self.restaurant, number=1, capacity=4)

        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword"
        )

        self.reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            table=self.table,
            user=self.user,
            customer_name="Test Customer",
            customer_email="test@example.com",
            customer_phone="1234567890",
            number_of_guests=3,
            reservation_date=timezone.now().date(),
            reservation_time=time(19, 0),
            status=Reservation.ReservationStatus.PENDING,
            special_requests="No onions, please.",
        )

    def test_reservation_creation(self):
        """Тест создания бронирования."""
        self.assertEqual(self.reservation.customer_name, "Test Customer")
        self.assertEqual(self.reservation.number_of_guests, 3)
        self.assertEqual(self.reservation.status, Reservation.ReservationStatus.PENDING)
        self.assertIsNotNone(self.reservation.end_time)

    def test_reservation_str_representation(self):
        """Тест строкового представления бронирования."""
        expected = f"Бронь {self.reservation.customer_name} на {self.reservation.reservation_date} {self.reservation.reservation_time} (Столик №{self.table.number})"
        self.assertEqual(str(self.reservation), expected)

    def test_calculate_duration(self):
        """Тест метода calculate_duration."""
        self.reservation.reservation_time = time(19, 0)
        self.reservation.end_time = time(21, 0)
        self.reservation.save()

        self.assertEqual(self.reservation.calculate_duration(), 120)

    def test_auto_set_end_time(self):
        """Тест автоматической установки end_time."""
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            table=self.table,
            customer_name="Auto Test Customer",
            customer_email="auto@example.com",
            customer_phone="1234567890",
            number_of_guests=2,
            reservation_date=timezone.now().date(),
            reservation_time=time(18, 30),
        )

        expected_end_time = time(20, 30)
        self.assertEqual(reservation.end_time.hour, expected_end_time.hour)
        self.assertEqual(reservation.end_time.minute, expected_end_time.minute)

    def test_confirm_reservation_updates_table_status(self):
        """Тест обновления статуса столика при подтверждении бронирования."""
        self.table.status = Table.TableStatus.FREE
        self.table.save()

        self.reservation.status = Reservation.ReservationStatus.CONFIRMED
        self.reservation.save()

        self.table.refresh_from_db()
        self.assertEqual(self.table.status, Table.TableStatus.RESERVED)


class RestaurantListViewTestCase(TestCase):
    """Тесты представления списка ресторанов."""

    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_user(
            username="testadmin", email="admin@example.com", password="adminpassword", is_staff=True
        )
        self.admin.user_permissions.add(
            *User.objects.filter(username="testadmin").first().user_permissions.all()
        )

        self.manager = User.objects.create_user(
            username="testmanager",
            email="manager@example.com",
            password="managerpassword",
            is_staff=True,
        )

        self.waiter = User.objects.create_user(
            username="testwaiter", email="waiter@example.com", password="waiterpassword"
        )

        self.customer = User.objects.create_user(
            username="testcustomer", email="customer@example.com", password="customerpassword"
        )

        self.restaurant1 = Restaurant.objects.create(
            name="First Restaurant",
            address="123 First St",
            city="First City",
            phone="1234567890",
            email="first@restaurant.com",
        )

        self.restaurant2 = Restaurant.objects.create(
            name="Second Restaurant",
            address="456 Second St",
            city="Second City",
            phone="0987654321",
            email="second@restaurant.com",
        )

        self.restaurant1.managers.add(self.manager)

        self.waiter.restaurant = self.restaurant1
        self.waiter.save()

        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        content_type = ContentType.objects.get_for_model(Restaurant)

        view_restaurant_perm = Permission.objects.get(
            content_type=content_type, codename="view_restaurant"
        )

        self.admin.user_permissions.add(view_restaurant_perm)
        self.manager.user_permissions.add(view_restaurant_perm)
        self.waiter.user_permissions.add(view_restaurant_perm)

    def test_restaurant_list_admin_access(self):
        """Тест доступа администратора к списку ресторанов."""
        self.client.login(username="testadmin", password="adminpassword")
        response = self.client.get(reverse("restaurants:restaurant_list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurants/restaurant_list.html")
        self.assertIn(self.restaurant1, response.context["restaurants"])
        self.assertIn(self.restaurant2, response.context["restaurants"])

    def test_restaurant_list_manager_access(self):
        """Тест доступа менеджера к списку ресторанов."""
        self.client.login(username="testmanager", password="managerpassword")
        response = self.client.get(reverse("restaurants:restaurant_list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurants/restaurant_list.html")
        self.assertIn(self.restaurant1, response.context["restaurants"])
        self.assertNotIn(self.restaurant2, response.context["restaurants"])

    def test_restaurant_list_waiter_access(self):
        """Тест доступа официанта к списку ресторанов."""
        self.client.login(username="testwaiter", password="waiterpassword")
        response = self.client.get(reverse("restaurants:restaurant_list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurants/restaurant_list.html")

    def test_restaurant_list_customer_access_denied(self):
        """Тест запрета доступа клиента к списку ресторанов."""
        self.client.login(username="testcustomer", password="customerpassword")
        response = self.client.get(reverse("restaurants:restaurant_list"))

        self.assertEqual(response.status_code, 403)

    def test_restaurant_list_filter_by_city(self):
        """Тест фильтрации списка ресторанов по городу."""
        self.client.login(username="testadmin", password="adminpassword")
        response = self.client.get(f"{reverse('restaurants:restaurant_list')}?city=First+City")

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.restaurant1, response.context["restaurants"])
        self.assertNotIn(self.restaurant2, response.context["restaurants"])

    def test_restaurant_list_filter_by_search(self):
        """Тест поиска ресторанов."""
        self.client.login(username="testadmin", password="adminpassword")
        response = self.client.get(f"{reverse('restaurants:restaurant_list')}?search=Second")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.restaurant1, response.context["restaurants"])
        self.assertIn(self.restaurant2, response.context["restaurants"])


class RestaurantDetailViewTestCase(TestCase):
    """Тесты представления деталей ресторана."""

    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_user(
            username="testadmin", email="admin@example.com", password="adminpassword", is_staff=True
        )

        self.waiter = User.objects.create_user(
            username="testwaiter", email="waiter@example.com", password="waiterpassword"
        )

        self.waiter2 = User.objects.create_user(
            username="testwaiter2", email="waiter2@example.com", password="waiterpassword"
        )

        self.customer = User.objects.create_user(
            username="testcustomer", email="customer@example.com", password="customerpassword"
        )

        self.restaurant = Restaurant.objects.create(
            name="Test Restaurant",
            address="123 Test St",
            city="Test City",
            phone="1234567890",
            email="test@restaurant.com",
            opening_hours={
                "monday": {"open": "09:00", "close": "22:00"},
            },
        )

        self.table1 = Table.objects.create(
            restaurant=self.restaurant, number=1, capacity=4, status=Table.TableStatus.FREE
        )

        self.table2 = Table.objects.create(
            restaurant=self.restaurant, number=2, capacity=2, status=Table.TableStatus.OCCUPIED
        )

        self.waiter.restaurant = self.restaurant
        self.waiter.save()

        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        content_type = ContentType.objects.get_for_model(Restaurant)

        view_restaurant_perm = Permission.objects.get(
            content_type=content_type, codename="view_restaurant"
        )

        self.admin.user_permissions.add(view_restaurant_perm)
        self.waiter.user_permissions.add(view_restaurant_perm)
        self.waiter2.user_permissions.add(view_restaurant_perm)

    def test_restaurant_detail_admin_access(self):
        """Тест доступа администратора к деталям ресторана."""
        self.client.login(username="testadmin", password="adminpassword")
        response = self.client.get(
            reverse("restaurants:restaurant_detail", kwargs={"id": self.restaurant.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurants/restaurant_detail.html")
        self.assertEqual(response.context["restaurant"], self.restaurant)
        self.assertEqual(response.context["tables_count"], 2)
        self.assertEqual(response.context["tables_free"], 1)
        self.assertEqual(response.context["tables_occupied"], 1)

    def test_restaurant_detail_waiter_access(self):
        """Тест доступа официанта к деталям своего ресторана."""
        self.client.login(username="testwaiter", password="waiterpassword")
        response = self.client.get(
            reverse("restaurants:restaurant_detail", kwargs={"id": self.restaurant.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurants/restaurant_detail.html")

    def test_restaurant_detail_waiter_access_denied_other_restaurant(self):
        """Тест запрета доступа официанта к деталям чужого ресторана."""
        self.client.login(username="testwaiter2", password="waiterpassword")
        response = self.client.get(
            reverse("restaurants:restaurant_detail", kwargs={"id": self.restaurant.id})
        )

        self.assertEqual(response.status_code, 302)

    def test_restaurant_detail_customer_access_denied(self):
        """Тест запрета доступа клиента к деталям ресторана."""
        self.client.login(username="testcustomer", password="customerpassword")
        response = self.client.get(
            reverse("restaurants:restaurant_detail", kwargs={"id": self.restaurant.id})
        )

        self.assertEqual(response.status_code, 403)


class RestaurantManagementViewsTestCase(TestCase):
    """Тесты представлений для управления ресторанами."""

    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_user(
            username="testadmin", email="admin@example.com", password="adminpassword", is_staff=True
        )

        self.manager = User.objects.create_user(
            username="testmanager",
            email="manager@example.com",
            password="managerpassword",
            is_staff=True,
        )

        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        content_type = ContentType.objects.get_for_model(Restaurant)

        manage_restaurant_perm = Permission.objects.get(
            content_type=content_type, codename="manage_restaurant"
        )

        self.admin.user_permissions.add(manage_restaurant_perm)

        self.restaurant = Restaurant.objects.create(
            name="Test Restaurant",
            address="123 Test St",
            city="Test City",
            phone="1234567890",
            email="test@restaurant.com",
        )

    def test_restaurant_manage_admin_access(self):
        """Тест доступа администратора к странице управления ресторанами."""
        self.client.login(username="testadmin", password="adminpassword")
        response = self.client.get(reverse("restaurants:restaurant_manage"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurants/restaurant_manage.html")
        self.assertIn(self.restaurant, response.context["restaurants"])

    def test_restaurant_manage_manager_access_denied(self):
        """Тест запрета доступа менеджера к странице управления ресторанами."""
        self.client.login(username="testmanager", password="managerpassword")
        response = self.client.get(reverse("restaurants:restaurant_manage"))

        self.assertEqual(response.status_code, 403)

    def test_restaurant_create(self):
        """Тест создания нового ресторана."""
        self.client.login(username="testadmin", password="adminpassword")

        logo = SimpleUploadedFile(
            name="test_logo.jpg", content=b"file_content", content_type="image/jpeg"
        )

        response = self.client.post(
            reverse("restaurants:restaurant_create"),
            {
                "name": "New Restaurant",
                "address": "789 New St",
                "city": "New City",
                "phone": "5551234567",
                "email": "new@restaurant.com",
                "logo": logo,
                "monday_open": "09:00",
                "monday_close": "22:00",
                "tuesday_open": "09:00",
                "tuesday_close": "22:00",
                "wednesday_open": "09:00",
                "wednesday_close": "22:00",
                "thursday_open": "09:00",
                "thursday_close": "22:00",
                "friday_open": "09:00",
                "friday_close": "23:00",
                "saturday_open": "10:00",
                "saturday_close": "23:00",
                "sunday_open": "10:00",
                "sunday_close": "22:00",
            },
        )

        self.assertEqual(Restaurant.objects.count(), 2)
        new_restaurant = Restaurant.objects.get(name="New Restaurant")
        self.assertRedirects(
            response, reverse("restaurants:restaurant_detail", kwargs={"id": new_restaurant.id})
        )

        self.assertEqual(new_restaurant.city, "New City")
        self.assertEqual(new_restaurant.phone, "5551234567")
        self.assertEqual(new_restaurant.opening_hours["monday"]["open"], "09:00")
        self.assertEqual(new_restaurant.opening_hours["monday"]["close"], "22:00")

    def test_restaurant_edit(self):
        """Тест редактирования ресторана."""
        self.client.login(username="testadmin", password="adminpassword")

        response = self.client.post(
            reverse("restaurants:restaurant_edit", kwargs={"id": self.restaurant.id}),
            {
                "name": "Updated Restaurant",
                "address": "123 Test St",
                "city": "Updated City",
                "phone": "1234567890",
                "email": "updated@restaurant.com",
                "monday_open": "10:00",
                "monday_close": "23:00",
            },
        )

        self.assertRedirects(
            response, reverse("restaurants:restaurant_detail", kwargs={"id": self.restaurant.id})
        )

        self.restaurant.refresh_from_db()
        self.assertEqual(self.restaurant.name, "Updated Restaurant")
        self.assertEqual(self.restaurant.city, "Updated City")
        self.assertEqual(self.restaurant.email, "updated@restaurant.com")
        self.assertEqual(self.restaurant.opening_hours["monday"]["open"], "10:00")


class TableViewsTestCase(TestCase):
    """Тесты представлений для работы со столиками."""

    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_user(
            username="testadmin", email="admin@example.com", password="adminpassword", is_staff=True
        )

        self.manager = User.objects.create_user(
            username="testmanager",
            email="manager@example.com",
            password="managerpassword",
            is_staff=True,
        )

        self.waiter = User.objects.create_user(
            username="testwaiter", email="waiter@example.com", password="waiterpassword"
        )

        self.customer = User.objects.create_user(
            username="testcustomer", email="customer@example.com", password="customerpassword"
        )

        self.restaurant = Restaurant.objects.create(
            name="Test Restaurant",
            address="123 Test St",
            city="Test City",
            phone="1234567890",
            email="test@restaurant.com",
        )

        self.table = Table.objects.create(
            restaurant=self.restaurant, number=1, capacity=4, shape=Table.TableShape.SQUARE
        )

        self.restaurant.managers.add(self.manager)

        self.waiter.restaurant = self.restaurant
        self.waiter.save()

        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        restaurant_content_type = ContentType.objects.get_for_model(Restaurant)
        table_content_type = ContentType.objects.get_for_model(Table)

        view_table_perm = Permission.objects.get(
            content_type=table_content_type, codename="view_table"
        )
        add_table_perm = Permission.objects.get(
            content_type=table_content_type, codename="add_table"
        )
        change_table_perm = Permission.objects.get(
            content_type=table_content_type, codename="change_table"
        )
        delete_table_perm = Permission.objects.get(
            content_type=table_content_type, codename="delete_table"
        )
        view_public_tables_perm = Permission.objects.get(
            content_type=table_content_type, codename="view_public_tables"
        )

        self.admin.user_permissions.add(
            view_table_perm, add_table_perm, change_table_perm, delete_table_perm
        )
        self.manager.user_permissions.add(
            view_table_perm, add_table_perm, change_table_perm, delete_table_perm
        )
        self.waiter.user_permissions.add(view_table_perm)
        self.customer.user_permissions.add(view_public_tables_perm)

    def test_table_layout_admin_access(self):
        """Тест доступа администратора к плану столиков."""
        self.client.login(username="testadmin", password="adminpassword")
        response = self.client.get(
            reverse("restaurants:table_layout", kwargs={"id": self.restaurant.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurants/table_layout.html")
        self.assertIn(self.table, response.context["tables"])
        self.assertEqual(response.context["restaurant"], self.restaurant)

    def test_table_layout_waiter_access(self):
        """Тест доступа официанта к плану столиков своего ресторана."""
        self.client.login(username="testwaiter", password="waiterpassword")
        response = self.client.get(
            reverse("restaurants:table_layout", kwargs={"id": self.restaurant.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurants/table_layout.html")

    def test_table_layout_waiter_access_denied(self):
        """Тест запрета доступа официанта к плану столиков чужого ресторана."""

        other_restaurant = Restaurant.objects.create(
            name="Other Restaurant",
            address="456 Other St",
            city="Other City",
            phone="0987654321",
            email="other@restaurant.com",
        )

        self.client.login(username="testwaiter", password="waiterpassword")
        response = self.client.get(
            reverse("restaurants:table_layout", kwargs={"id": other_restaurant.id})
        )

        self.assertEqual(response.status_code, 302)

    def test_table_layout_customer_access_denied(self):
        """Тест запрета доступа клиента к плану столиков."""
        self.client.login(username="testcustomer", password="customerpassword")
        response = self.client.get(
            reverse("restaurants:table_layout", kwargs={"id": self.restaurant.id})
        )

        self.assertEqual(response.status_code, 403)

    def test_table_create(self):
        """Тест создания нового столика."""
        self.client.login(username="testadmin", password="adminpassword")

        response = self.client.post(
            reverse("restaurants:table_create", kwargs={"restaurant_id": self.restaurant.id}),
            {
                "restaurant": self.restaurant.id,
                "number": 2,
                "capacity": 6,
                "shape": Table.TableShape.RECTANGULAR,
                "width": 120,
                "length": 80,
                "position_x": 100,
                "position_y": 150,
                "is_active": True,
            },
        )

        self.assertEqual(Table.objects.count(), 2)
        new_table = Table.objects.get(number=2)
        self.assertRedirects(
            response, reverse("restaurants:table_layout", kwargs={"id": self.restaurant.id})
        )

        self.assertEqual(new_table.capacity, 6)
        self.assertEqual(new_table.shape, Table.TableShape.RECTANGULAR)
        self.assertEqual(new_table.width, 120)
        self.assertEqual(new_table.length, 80)
        self.assertEqual(new_table.position_x, 100)
        self.assertEqual(new_table.position_y, 150)

    def test_table_edit(self):
        """Тест редактирования столика."""
        self.client.login(username="testadmin", password="adminpassword")

        response = self.client.post(
            reverse("restaurants:table_edit", kwargs={"id": self.table.id}),
            {
                "restaurant": self.restaurant.id,
                "number": 1,
                "capacity": 8,
                "shape": Table.TableShape.ROUND,
                "width": 100,
                "length": 100,
                "position_x": 200,
                "position_y": 300,
                "is_active": True,
            },
        )

        self.assertRedirects(
            response, reverse("restaurants:table_layout", kwargs={"id": self.restaurant.id})
        )

        self.table.refresh_from_db()
        self.assertEqual(self.table.capacity, 8)
        self.assertEqual(self.table.shape, Table.TableShape.ROUND)
        self.assertEqual(self.table.position_x, 200)
        self.assertEqual(self.table.position_y, 300)

    def test_table_delete(self):
        """Тест удаления столика."""
        self.client.login(username="testadmin", password="adminpassword")

        response = self.client.post(
            reverse("restaurants:table_delete", kwargs={"id": self.table.id})
        )

        self.assertRedirects(
            response, reverse("restaurants:table_layout", kwargs={"id": self.restaurant.id})
        )
        self.assertEqual(Table.objects.count(), 0)


class ReservationViewsTestCase(TestCase):
    """Тесты представлений для бронирования столиков."""

    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_user(
            username="testadmin", email="admin@example.com", password="adminpassword", is_staff=True
        )

        self.manager = User.objects.create_user(
            username="testmanager",
            email="manager@example.com",
            password="managerpassword",
            is_staff=True,
        )

        self.waiter = User.objects.create_user(
            username="testwaiter", email="waiter@example.com", password="waiterpassword"
        )

        self.customer = User.objects.create_user(
            username="testcustomer", email="customer@example.com", password="customerpassword"
        )

        self.restaurant = Restaurant.objects.create(
            name="Test Restaurant",
            address="123 Test St",
            city="Test City",
            phone="1234567890",
            email="test@restaurant.com",
        )

        self.table = Table.objects.create(restaurant=self.restaurant, number=1, capacity=4)

        self.reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            table=self.table,
            user=self.customer,
            customer_name="Test Customer",
            customer_email="test@example.com",
            customer_phone="1234567890",
            number_of_guests=3,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=time(19, 0),
            end_time=time(21, 0),
            status=Reservation.ReservationStatus.CONFIRMED,
        )

        self.waiter.restaurant = self.restaurant
        self.waiter.save()

        self.allergen1 = Allergen.objects.create(name="Gluten")
        self.allergen2 = Allergen.objects.create(name="Lactose")

        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        reservation_content_type = ContentType.objects.get_for_model(Reservation)

        view_reservation_perm = Permission.objects.get(
            content_type=reservation_content_type, codename="view_reservation"
        )
        add_reservation_perm = Permission.objects.get(
            content_type=reservation_content_type, codename="add_reservation"
        )
        change_reservation_perm = Permission.objects.get(
            content_type=reservation_content_type, codename="change_reservation"
        )
        delete_reservation_perm = Permission.objects.get(
            content_type=reservation_content_type, codename="delete_reservation"
        )

        self.admin.user_permissions.add(
            view_reservation_perm,
            add_reservation_perm,
            change_reservation_perm,
            delete_reservation_perm,
        )
        self.manager.user_permissions.add(
            view_reservation_perm,
            add_reservation_perm,
            change_reservation_perm,
            delete_reservation_perm,
        )
        self.waiter.user_permissions.add(
            view_reservation_perm,
            add_reservation_perm,
            change_reservation_perm,
            delete_reservation_perm,
        )
        self.customer.user_permissions.add(add_reservation_perm)

    def test_reservation_list_admin_access(self):
        """Тест доступа администратора к списку бронирований."""
        self.client.login(username="testadmin", password="adminpassword")
        response = self.client.get(
            reverse("restaurants:reservation_list", kwargs={"id": self.restaurant.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurants/reservation_list.html")
        self.assertIn(self.reservation, response.context["reservations"])

    def test_reservation_list_waiter_access(self):
        """Тест доступа официанта к списку бронирований своего ресторана."""
        self.client.login(username="testwaiter", password="waiterpassword")
        response = self.client.get(
            reverse("restaurants:reservation_list", kwargs={"id": self.restaurant.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurants/reservation_list.html")

    def test_reservation_list_waiter_access_denied(self):
        """Тест запрета доступа официанта к списку бронирований чужого ресторана."""

        other_restaurant = Restaurant.objects.create(
            name="Other Restaurant",
            address="456 Other St",
            city="Other City",
            phone="0987654321",
            email="other@restaurant.com",
        )

        self.client.login(username="testwaiter", password="waiterpassword")
        response = self.client.get(
            reverse("restaurants:reservation_list", kwargs={"id": other_restaurant.id})
        )

        self.assertEqual(response.status_code, 302)

    def test_reservation_list_customer_access_denied(self):
        """Тест запрета доступа клиента к списку бронирований."""
        self.client.login(username="testcustomer", password="customerpassword")
        response = self.client.get(
            reverse("restaurants:reservation_list", kwargs={"id": self.restaurant.id})
        )

        self.assertEqual(response.status_code, 403)

    def test_reservation_create_by_staff(self):
        """Тест создания бронирования персоналом."""
        self.client.login(username="testadmin", password="adminpassword")

        tomorrow = timezone.now().date() + timedelta(days=1)

        response = self.client.post(
            reverse("restaurants:reservation_create", kwargs={"id": self.restaurant.id}),
            {
                "customer_name": "New Reservation",
                "customer_email": "new@example.com",
                "customer_phone": "9876543210",
                "number_of_guests": 2,
                "reservation_date": tomorrow.strftime("%Y-%m-%d"),
                "reservation_time": "20:00",
                "duration": 2,
                "table": self.table.id,
                "status": Reservation.ReservationStatus.CONFIRMED,
                "special_requests": "Window seat, please.",
                "is_vegetarian": True,
                "allergens": [self.allergen1.id],
            },
        )

        self.assertEqual(Reservation.objects.count(), 2)
        new_reservation = Reservation.objects.latest("created_at")
        self.assertRedirects(
            response, reverse("restaurants:reservation_list", kwargs={"id": self.restaurant.id})
        )

        self.assertEqual(new_reservation.customer_name, "New Reservation")
        self.assertEqual(new_reservation.number_of_guests, 2)
        self.assertEqual(new_reservation.status, Reservation.ReservationStatus.CONFIRMED)
        self.assertEqual(new_reservation.table, self.table)
        self.assertTrue(new_reservation.dietary_preferences.get("vegetarian", False))
        self.assertIn(str(self.allergen1.id), new_reservation.allergy_information.get("ids", []))

    def test_reservation_edit(self):
        """Тест редактирования бронирования."""
        self.client.login(username="testadmin", password="adminpassword")

        tomorrow = timezone.now().date() + timedelta(days=1)

        response = self.client.post(
            reverse("restaurants:reservation_edit", kwargs={"id": self.reservation.id}),
            {
                "customer_name": "Updated Reservation",
                "customer_email": "updated@example.com",
                "customer_phone": "1234567890",
                "number_of_guests": 4,
                "reservation_date": tomorrow.strftime("%Y-%m-%d"),
                "reservation_time": "18:00",
                "duration": 3,
                "table": self.table.id,
                "status": Reservation.ReservationStatus.CONFIRMED,
                "special_requests": "Updated request",
                "is_gluten_free": True,
            },
        )

        self.assertRedirects(
            response, reverse("restaurants:reservation_list", kwargs={"id": self.restaurant.id})
        )

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.customer_name, "Updated Reservation")
        self.assertEqual(self.reservation.customer_email, "updated@example.com")
        self.assertEqual(self.reservation.number_of_guests, 4)
        self.assertEqual(self.reservation.reservation_time.strftime("%H:%M"), "18:00")
        self.assertEqual(self.reservation.special_requests, "Updated request")
        self.assertTrue(self.reservation.dietary_preferences.get("gluten_free", False))

    def test_reservation_cancel(self):
        """Тест отмены бронирования."""
        self.client.login(username="testadmin", password="adminpassword")

        response = self.client.post(
            reverse("restaurants:reservation_cancel", kwargs={"id": self.reservation.id}),
            {"reason": "Customer called to cancel."},
        )

        self.assertRedirects(
            response, reverse("restaurants:reservation_list", kwargs={"id": self.restaurant.id})
        )

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, Reservation.ReservationStatus.CANCELLED)
        self.assertIn("Customer called to cancel.", self.reservation.special_requests)

    def test_customer_reservation_history(self):
        """Тест истории бронирований клиента."""
        self.client.login(username="testcustomer", password="customerpassword")
        response = self.client.get(reverse("restaurants:customer_reservation_history"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurants/customer_reservation_history.html")
        self.assertIn(self.reservation, response.context["reservations"])

    def test_customer_reservation_filter_by_status(self):
        """Тест фильтрации истории бронирований клиента по статусу."""

        Reservation.objects.create(
            restaurant=self.restaurant,
            table=self.table,
            user=self.customer,
            customer_name="Test Customer",
            customer_email="test@example.com",
            customer_phone="1234567890",
            number_of_guests=2,
            reservation_date=timezone.now().date() + timedelta(days=2),
            reservation_time=time(20, 0),
            end_time=time(22, 0),
            status=Reservation.ReservationStatus.PENDING,
        )

        self.client.login(username="testcustomer", password="customerpassword")
        response = self.client.get(
            f"{reverse('restaurants:customer_reservation_history')}?status={Reservation.ReservationStatus.CONFIRMED}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["reservations"]), 1)
        self.assertEqual(
            response.context["reservations"][0].status, Reservation.ReservationStatus.CONFIRMED
        )


class PublicRestaurantViewsTestCase(TestCase):
    """Тесты публичных представлений для ресторанов."""

    def setUp(self):
        self.client = Client()

        self.customer = User.objects.create_user(
            username="testcustomer", email="customer@example.com", password="customerpassword"
        )

        self.restaurant1 = Restaurant.objects.create(
            name="First Restaurant",
            address="123 First St",
            city="First City",
            phone="1234567890",
            email="first@restaurant.com",
            is_active=True,
            opening_hours={
                "monday": {"open": "09:00", "close": "22:00"},
                "tuesday": {"open": "09:00", "close": "22:00"},
                "wednesday": {"open": "09:00", "close": "22:00"},
                "thursday": {"open": "09:00", "close": "22:00"},
                "friday": {"open": "09:00", "close": "23:00"},
                "saturday": {"open": "10:00", "close": "23:00"},
                "sunday": {"open": "10:00", "close": "22:00"},
            },
        )

        self.restaurant2 = Restaurant.objects.create(
            name="Second Restaurant",
            address="456 Second St",
            city="Second City",
            phone="0987654321",
            email="second@restaurant.com",
            is_active=True,
        )

        self.inactive_restaurant = Restaurant.objects.create(
            name="Inactive Restaurant",
            address="789 Third St",
            city="Third City",
            phone="1122334455",
            email="inactive@restaurant.com",
            is_active=False,
        )

        self.table1 = Table.objects.create(
            restaurant=self.restaurant1, number=1, capacity=4, is_active=True
        )

        self.table2 = Table.objects.create(
            restaurant=self.restaurant1, number=2, capacity=2, is_active=True
        )

        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        table_content_type = ContentType.objects.get_for_model(Table)
        reservation_content_type = ContentType.objects.get_for_model(Reservation)

        view_public_tables_perm = Permission.objects.get(
            content_type=table_content_type, codename="view_public_tables"
        )
        add_reservation_perm = Permission.objects.get(
            content_type=reservation_content_type, codename="add_reservation"
        )

        self.customer.user_permissions.add(view_public_tables_perm, add_reservation_perm)

    def test_public_restaurant_list(self):
        """Тест публичного списка ресторанов."""
        response = self.client.get(reverse("restaurants:public_restaurant_list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurants/public_restaurant_list.html")

        self.assertIn(self.restaurant1, response.context["restaurants"])
        self.assertIn(self.restaurant2, response.context["restaurants"])
        self.assertNotIn(self.inactive_restaurant, response.context["restaurants"])

    def test_public_restaurant_list_filter_by_city(self):
        """Тест фильтрации публичного списка ресторанов по городу."""
        response = self.client.get(
            f"{reverse('restaurants:public_restaurant_list')}?city=First+City"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.restaurant1, response.context["restaurants"])
        self.assertNotIn(self.restaurant2, response.context["restaurants"])

    def test_public_restaurant_list_filter_by_search(self):
        """Тест поиска в публичном списке ресторанов."""
        response = self.client.get(f"{reverse('restaurants:public_restaurant_list')}?search=Second")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.restaurant1, response.context["restaurants"])
        self.assertIn(self.restaurant2, response.context["restaurants"])

    def test_public_restaurant_detail(self):
        """Тест публичной страницы ресторана."""
        response = self.client.get(
            reverse("restaurants:public_restaurant_detail", kwargs={"id": self.restaurant1.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurants/public_restaurant_detail.html")
        self.assertEqual(response.context["restaurant"], self.restaurant1)

    def test_public_restaurant_detail_inactive(self):
        """Тест доступа к публичной странице неактивного ресторана."""
        response = self.client.get(
            reverse(
                "restaurants:public_restaurant_detail", kwargs={"id": self.inactive_restaurant.id}
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_public_table_view_authenticated(self):
        """Тест доступа авторизованного пользователя к публичному просмотру столиков."""
        self.client.login(username="testcustomer", password="customerpassword")
        response = self.client.get(
            reverse("restaurants:public_table_view", kwargs={"id": self.restaurant1.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurants/public_table_view.html")
        self.assertIn(self.table1, response.context["tables"])
        self.assertIn(self.table2, response.context["tables"])

    def test_public_table_view_unauthenticated(self):
        """Тест запрета доступа неавторизованного пользователя к публичному просмотру столиков."""
        response = self.client.get(
            reverse("restaurants:public_table_view", kwargs={"id": self.restaurant1.id})
        )

        login_url = reverse("users:login")
        self.assertRedirects(
            response,
            f"{login_url}?next={reverse('restaurants:public_table_view', kwargs={'id': self.restaurant1.id})}",
        )

    def test_public_table_view_filter_by_capacity(self):
        """Тест фильтрации столиков по вместимости."""
        self.client.login(username="testcustomer", password="customerpassword")
        response = self.client.get(
            f"{reverse('restaurants:public_table_view', kwargs={'id': self.restaurant1.id})}?min_capacity=3"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.table1, response.context["tables"])
        self.assertNotIn(self.table2, response.context["tables"])

    def test_customer_reservation_create(self):
        """Тест создания бронирования клиентом."""
        self.client.login(username="testcustomer", password="customerpassword")

        tomorrow = timezone.now().date() + timedelta(days=1)

        response = self.client.post(
            reverse("restaurants:customer_reservation", kwargs={"id": self.restaurant1.id}),
            {
                "customer_name": "Customer Reservation",
                "customer_email": "customer@example.com",
                "customer_phone": "1234567890",
                "number_of_guests": 2,
                "reservation_date": tomorrow.strftime("%Y-%m-%d"),
                "reservation_time": "20:00",
                "duration": 2,
                "table_id": self.table2.id,
                "is_vegetarian": True,
                "special_requests": "Please reserve a quiet table.",
            },
        )

        self.assertEqual(Reservation.objects.count(), 1)
        new_reservation = Reservation.objects.first()

        self.assertRedirects(
            response,
            reverse("restaurants:reservation_confirmation", kwargs={"id": new_reservation.id}),
        )

        self.assertEqual(new_reservation.customer_name, "Customer Reservation")
        self.assertEqual(new_reservation.number_of_guests, 2)
        self.assertEqual(new_reservation.status, Reservation.ReservationStatus.PENDING)
        self.assertEqual(new_reservation.table, self.table2)
        self.assertTrue(new_reservation.dietary_preferences.get("vegetarian", False))
        self.assertEqual(new_reservation.special_requests, "Please reserve a quiet table.")
        self.assertEqual(new_reservation.user, self.customer)

    def test_reservation_confirmation_view(self):
        """Тест страницы подтверждения бронирования."""
        self.client.login(username="testcustomer", password="customerpassword")

        reservation = Reservation.objects.create(
            restaurant=self.restaurant1,
            table=self.table1,
            user=self.customer,
            customer_name="Test Customer",
            customer_email="test@example.com",
            customer_phone="1234567890",
            number_of_guests=4,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=time(19, 0),
            end_time=time(21, 0),
            status=Reservation.ReservationStatus.PENDING,
        )

        response = self.client.get(
            reverse("restaurants:reservation_confirmation", kwargs={"id": reservation.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurants/reservation_confirmation.html")
        self.assertEqual(response.context["reservation"], reservation)

    def test_reservation_confirmation_access_denied(self):
        """Тест запрета доступа к странице подтверждения чужого бронирования."""

        other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="otherpassword"
        )

        reservation = Reservation.objects.create(
            restaurant=self.restaurant1,
            table=self.table1,
            user=other_user,
            customer_name="Other User",
            customer_email="other@example.com",
            customer_phone="9876543210",
            number_of_guests=4,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=time(19, 0),
            end_time=time(21, 0),
            status=Reservation.ReservationStatus.PENDING,
        )

        self.client.login(username="testcustomer", password="customerpassword")
        response = self.client.get(
            reverse("restaurants:reservation_confirmation", kwargs={"id": reservation.id})
        )

        self.assertEqual(response.status_code, 302)


class HelperFunctionsTestCase(TestCase):
    """Тесты вспомогательных функций."""

    def setUp(self):

        self.restaurant = Restaurant.objects.create(
            name="Test Restaurant",
            address="123 Test St",
            city="Test City",
            phone="1234567890",
            email="test@restaurant.com",
            opening_hours={
                "monday": {"open": "09:00", "close": "22:00"},
                "tuesday": {"open": "09:00", "close": "22:00"},
                "wednesday": {"open": "09:00", "close": "22:00"},
                "thursday": {"open": "09:00", "close": "22:00"},
                "friday": {"open": "09:00", "close": "23:00"},
                "saturday": {"open": "10:00", "close": "23:00"},
                "sunday": {"open": "10:00", "close": "22:00"},
            },
        )

        from restaurants.views import is_restaurant_open

        self.is_restaurant_open = is_restaurant_open

    def test_is_restaurant_open(self):
        """Тест функции is_restaurant_open."""

        real_now = timezone.now

        try:

            monday_morning = datetime(2023, 5, 1, 10, 0)

            timezone.now = lambda: monday_morning.replace(tzinfo=timezone.utc)
            self.assertTrue(self.is_restaurant_open(self.restaurant))

            monday_early = datetime(2023, 5, 1, 8, 0)
            timezone.now = lambda: monday_early.replace(tzinfo=timezone.utc)
            self.assertFalse(self.is_restaurant_open(self.restaurant))

            monday_late = datetime(2023, 5, 1, 22, 30)
            timezone.now = lambda: monday_late.replace(tzinfo=timezone.utc)
            self.assertFalse(self.is_restaurant_open(self.restaurant))

            saturday_morning = datetime(2023, 5, 6, 11, 0)
            timezone.now = lambda: saturday_morning.replace(tzinfo=timezone.utc)
            self.assertTrue(self.is_restaurant_open(self.restaurant))

            self.restaurant.opening_hours = {}
            self.assertFalse(self.is_restaurant_open(self.restaurant))

            self.restaurant.opening_hours = {"monday": {"open": "09:00"}}
            self.assertFalse(self.is_restaurant_open(self.restaurant))

        finally:

            timezone.now = real_now

    def test_is_restaurant_open_overnight(self):
        """Тест функции is_restaurant_open для ресторана, работающего ночью."""

        real_now = timezone.now

        try:

            self.restaurant.opening_hours = {
                "monday": {"open": "18:00", "close": "02:00"},
                "tuesday": {"open": "18:00", "close": "02:00"},
            }
            self.restaurant.save()

            monday_evening = datetime(2023, 5, 1, 20, 0)
            timezone.now = lambda: monday_evening.replace(tzinfo=timezone.utc)
            self.assertTrue(self.is_restaurant_open(self.restaurant))

            tuesday_early = datetime(2023, 5, 2, 1, 0)
            timezone.now = lambda: tuesday_early.replace(tzinfo=timezone.utc)
            self.assertTrue(self.is_restaurant_open(self.restaurant))

            tuesday_morning = datetime(2023, 5, 2, 3, 0)
            timezone.now = lambda: tuesday_morning.replace(tzinfo=timezone.utc)
            self.assertFalse(self.is_restaurant_open(self.restaurant))

        finally:

            timezone.now = real_now


class FormTestCase(TestCase):
    """Тесты форм приложения restaurants."""

    def setUp(self):

        self.restaurant = Restaurant.objects.create(
            name="Test Restaurant",
            address="123 Test St",
            city="Test City",
            phone="1234567890",
            email="test@restaurant.com",
        )

        self.table = Table.objects.create(
            restaurant=self.restaurant, number=1, capacity=4, shape=Table.TableShape.SQUARE
        )

        self.admin = User.objects.create_user(
            username="testadmin", email="admin@example.com", password="adminpassword", is_staff=True
        )

        self.customer = User.objects.create_user(
            username="testcustomer", email="customer@example.com", password="customerpassword"
        )

        self.allergen1 = Allergen.objects.create(name="Gluten")
        self.allergen2 = Allergen.objects.create(name="Lactose")

    def test_restaurant_form_valid(self):
        """Тест валидации формы ресторана с корректными данными."""
        from restaurants.forms import RestaurantForm

        form_data = {
            "name": "New Restaurant",
            "address": "789 New St",
            "city": "New City",
            "postal_code": "12345",
            "country": "New Country",
            "phone": "5551234567",
            "email": "new@restaurant.com",
            "description": "A nice new restaurant",
            "is_active": True,
            "monday_open": "09:00",
            "monday_close": "22:00",
            "tuesday_open": "09:00",
            "tuesday_close": "22:00",
        }

        form = RestaurantForm(data=form_data)
        self.assertTrue(form.is_valid())

        restaurant = form.save()

        self.assertEqual(restaurant.name, "New Restaurant")
        self.assertEqual(restaurant.city, "New City")
        self.assertEqual(restaurant.opening_hours["monday"]["open"], "09:00")
        self.assertEqual(restaurant.opening_hours["monday"]["close"], "22:00")

    def test_restaurant_form_invalid(self):
        """Тест валидации формы ресторана с некорректными данными."""
        from restaurants.forms import RestaurantForm

        form_data = {
            "address": "789 New St",
            "city": "New City",
            "phone": "5551234567",
            "email": "invalid-email",
        }

        form = RestaurantForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
        self.assertIn("email", form.errors)

    def test_table_form_valid(self):
        """Тест валидации формы столика с корректными данными."""
        from restaurants.forms import TableForm

        form_data = {
            "restaurant": self.restaurant.id,
            "number": 2,
            "capacity": 6,
            "status": Table.TableStatus.FREE,
            "shape": Table.TableShape.RECTANGULAR,
            "width": 120,
            "length": 80,
            "position_x": 100,
            "position_y": 150,
            "is_active": True,
        }

        form = TableForm(data=form_data, user=self.admin)
        self.assertTrue(form.is_valid())

        table = form.save()

        self.assertEqual(table.number, 2)
        self.assertEqual(table.capacity, 6)
        self.assertEqual(table.shape, Table.TableShape.RECTANGULAR)
        self.assertEqual(table.width, 120)
        self.assertEqual(table.length, 80)

    def test_table_form_invalid(self):
        """Тест валидации формы столика с некорректными данными."""
        from restaurants.forms import TableForm

        form_data = {
            "restaurant": self.restaurant.id,
            "capacity": 0,
            "shape": "INVALID_SHAPE",
        }

        form = TableForm(data=form_data, user=self.admin)
        self.assertFalse(form.is_valid())
        self.assertIn("number", form.errors)
        self.assertIn("capacity", form.errors)
        self.assertIn("shape", form.errors)

    def test_reservation_form_valid(self):
        """Тест валидации формы бронирования с корректными данными."""
        from restaurants.forms import ReservationForm

        tomorrow = timezone.now().date() + timedelta(days=1)

        form_data = {
            "customer_name": "Test Reservation",
            "customer_email": "reservation@test.com",
            "customer_phone": "1234567890",
            "number_of_guests": 3,
            "reservation_date": tomorrow.strftime("%Y-%m-%d"),
            "reservation_time": "19:00",
            "duration": 2,
            "special_requests": "Window seat, please.",
            "is_vegetarian": True,
            "allergens": [self.allergen1.id, self.allergen2.id],
        }

        form = ReservationForm(data=form_data, restaurant=self.restaurant, user=self.customer)

        self.assertTrue(form.is_valid())
        self.assertTrue(hasattr(form, "available_tables"))
        self.assertIn(self.table, form.available_tables)

        reservation = form.save()
        reservation.table = self.table
        reservation.save()

        self.assertEqual(reservation.customer_name, "Test Reservation")
        self.assertEqual(reservation.number_of_guests, 3)
        self.assertEqual(reservation.reservation_time.strftime("%H:%M"), "19:00")
        self.assertTrue(reservation.dietary_preferences.get("vegetarian", False))
        self.assertEqual(len(reservation.allergy_information["ids"]), 2)

    def test_reservation_form_invalid_past_date(self):
        """Тест валидации формы бронирования с прошедшей датой."""
        from restaurants.forms import ReservationForm

        yesterday = timezone.now().date() - timedelta(days=1)

        form_data = {
            "customer_name": "Test Reservation",
            "customer_email": "reservation@test.com",
            "customer_phone": "1234567890",
            "number_of_guests": 3,
            "reservation_date": yesterday.strftime("%Y-%m-%d"),
            "reservation_time": "19:00",
            "duration": 2,
        }

        form = ReservationForm(data=form_data, restaurant=self.restaurant, user=self.customer)
        self.assertFalse(form.is_valid())
        self.assertIn("reservation_date", form.errors)

    def test_reservation_form_invalid_too_many_guests(self):
        """Тест валидации формы бронирования со слишком большим количеством гостей."""
        from restaurants.forms import ReservationForm

        tomorrow = timezone.now().date() + timedelta(days=1)

        form_data = {
            "customer_name": "Test Reservation",
            "customer_email": "reservation@test.com",
            "customer_phone": "1234567890",
            "number_of_guests": 10,
            "reservation_date": tomorrow.strftime("%Y-%m-%d"),
            "reservation_time": "19:00",
            "duration": 2,
        }

        form = ReservationForm(data=form_data, restaurant=self.restaurant, user=self.customer)
        self.assertFalse(form.is_valid())

        self.assertTrue(form.non_field_errors())

    def test_staff_reservation_form(self):
        """Тест формы бронирования для персонала."""
        from restaurants.forms import StaffReservationForm

        tomorrow = timezone.now().date() + timedelta(days=1)

        form_data = {
            "customer_name": "Staff Reservation",
            "customer_email": "reservation@test.com",
            "customer_phone": "1234567890",
            "number_of_guests": 3,
            "reservation_date": tomorrow.strftime("%Y-%m-%d"),
            "reservation_time": "19:00",
            "duration": 2,
            "table": self.table.id,
            "status": Reservation.ReservationStatus.CONFIRMED,
            "is_vegetarian": True,
        }

        form = StaffReservationForm(data=form_data, restaurant=self.restaurant, user=self.admin)
        self.assertTrue(form.is_valid())

        reservation = form.save()

        self.assertEqual(reservation.customer_name, "Staff Reservation")
        self.assertEqual(reservation.table, self.table)
        self.assertEqual(reservation.status, Reservation.ReservationStatus.CONFIRMED)
        self.assertTrue(reservation.dietary_preferences.get("vegetarian", False))

    def test_filter_forms(self):
        """Тест форм фильтрации."""
        from restaurants.forms import TableFilterForm, RestaurantFilterForm

        table_filter_data = {
            "min_capacity": 2,
            "max_capacity": 6,
            "date": timezone.now().date().strftime("%Y-%m-%d"),
            "time": "19:00",
            "shape": Table.TableShape.SQUARE,
        }

        table_form = TableFilterForm(data=table_filter_data)
        self.assertTrue(table_form.is_valid())
        self.assertEqual(table_form.cleaned_data["min_capacity"], 2)
        self.assertEqual(table_form.cleaned_data["max_capacity"], 6)
        self.assertEqual(table_form.cleaned_data["shape"], Table.TableShape.SQUARE)

        restaurant_filter_data = {
            "city": "Test City",
            "search": "Restaurant",
        }

        restaurant_form = RestaurantFilterForm(data=restaurant_filter_data)
        self.assertTrue(restaurant_form.is_valid())
        self.assertEqual(restaurant_form.cleaned_data["city"], "Test City")
        self.assertEqual(restaurant_form.cleaned_data["search"], "Restaurant")

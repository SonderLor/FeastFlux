import random
import os
from datetime import time, datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from restaurants.models import Restaurant, Table, Reservation

User = get_user_model()


class Command(BaseCommand):
    help = 'Создает примеры ресторанов и столиков для демонстрации'

    def add_arguments(self, parser):
        parser.add_argument(
            '--restaurants',
            type=int,
            default=5,
            help='Количество ресторанов для создания'
        )
        parser.add_argument(
            '--tables',
            type=int,
            default=10,
            help='Количество столиков для каждого ресторана'
        )
        parser.add_argument(
            '--reservations',
            type=int,
            default=5,
            help='Количество бронирований для каждого ресторана'
        )

    def handle(self, *args, **options):
        num_restaurants = options['restaurants']
        num_tables_per_restaurant = options['tables']
        num_reservations_per_restaurant = options['reservations']

        self.stdout.write(
            self.style.SUCCESS(f'Создаем {num_restaurants} ресторанов с {num_tables_per_restaurant} столиками каждый')
        )

        managers = self._ensure_managers_exist()

        created_restaurants = []
        for i in range(num_restaurants):
            restaurant = self._create_restaurant(i + 1, managers)
            created_restaurants.append(restaurant)
            self.stdout.write(f'Ресторан создан: {restaurant.name}')

            for j in range(num_tables_per_restaurant):
                table = self._create_table(restaurant, j + 1)
                self.stdout.write(f'  Столик создан: {table.number} ({table.shape})')

            for k in range(num_reservations_per_restaurant):
                if k % 3 == 0:
                    reservation = self._create_reservation(restaurant, is_today=True)
                else:
                    reservation = self._create_reservation(restaurant, is_today=False)
                self.stdout.write(f'  Бронь создана: {reservation.customer_name} на {reservation.reservation_date}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Успешно создано {num_restaurants} ресторанов, '
                f'{num_restaurants * num_tables_per_restaurant} столиков и '
                f'{num_restaurants * num_reservations_per_restaurant} бронирований'
            )
        )

    def _ensure_managers_exist(self):
        """Убеждаемся, что есть пользователи-менеджеры"""
        existing_managers = User.objects.filter(role='MANAGER')
        if existing_managers.exists():
            return list(existing_managers)

        managers = []
        manager_data = [
            {
                'username': 'manager1',
                'email': 'manager1@example.com',
                'first_name': 'Иван',
                'last_name': 'Петров',
                'password': 'password123',
            },
            {
                'username': 'manager2',
                'email': 'manager2@example.com',
                'first_name': 'Анна',
                'last_name': 'Смирнова',
                'password': 'password123',
            },
            {
                'username': 'manager3',
                'email': 'manager3@example.com',
                'first_name': 'Дмитрий',
                'last_name': 'Соколов',
                'password': 'password123',
            }
        ]

        for data in manager_data:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'role': 'MANAGER',
                    'is_active': True,
                    'is_active_employee': True,
                }
            )
            if created:
                user.set_password(data['password'])
                user.save()
                self.stdout.write(f'Создан менеджер: {user.first_name} {user.last_name}')
            managers.append(user)

        return managers

    def _create_restaurant(self, index, managers):
        """Создает ресторан с реалистичными данными"""
        restaurant_templates = [
            {
                'name': 'Старый Тифлис',
                'cuisine': 'Грузинская кухня',
                'description': 'Аутентичная грузинская кухня в сердце города. Мы предлагаем широкий выбор блюд, приготовленных по традиционным рецептам. Особенно рекомендуем хачапури по-аджарски, хинкали и шашлыки.',
                'city': 'Москва',
                'address': 'ул. Пушкина, 12',
                'phone': '+7 (495) 123-45-67',
            },
            {
                'name': 'Сакура',
                'cuisine': 'Японская кухня',
                'description': 'Японский ресторан с аутентичной атмосферой и изысканным меню. Наши шеф-повара готовят лучшие суши, сашими и роллы. Каждое блюдо – это произведение искусства, которое порадует не только вкусовые рецепторы, но и глаза.',
                'city': 'Санкт-Петербург',
                'address': 'Невский проспект, 45',
                'phone': '+7 (812) 765-43-21',
            },
            {
                'name': 'Венеция',
                'cuisine': 'Итальянская кухня',
                'description': 'Настоящая итальянская пиццерия. Мы выпекаем пиццу в дровяной печи, используем только свежие ингредиенты и соблюдаем оригинальные рецепты. Наши пасты и пиццы не оставят равнодушным даже самого взыскательного гурмана.',
                'city': 'Москва',
                'address': 'Тверская ул., 22',
                'phone': '+7 (495) 987-65-43',
            },
            {
                'name': 'Эль Гаучо',
                'cuisine': 'Аргентинская кухня',
                'description': 'Аргентинский гриль-ресторан, где готовят лучшие стейки в городе. Мясо, приготовленное на открытом огне, подается с традиционными аргентинскими соусами и гарнирами. Широкий выбор вин дополнит ваш ужин.',
                'city': 'Екатеринбург',
                'address': 'пр. Ленина, 30',
                'phone': '+7 (343) 234-56-78',
            },
            {
                'name': 'Тадж-Махал',
                'cuisine': 'Индийская кухня',
                'description': 'Аутентичная индийская кухня, которая перенесет вас в экзотический мир пряностей и ароматов. Разнообразие вегетарианских и мясных блюд удовлетворит любой вкус. Особенно рекомендуем фирменные карри и тандури.',
                'city': 'Казань',
                'address': 'ул. Баумана, 17',
                'phone': '+7 (843) 876-54-32',
            },
            {
                'name': 'Пекинская утка',
                'cuisine': 'Китайская кухня',
                'description': 'Лучшая китайская кухня в традиционном исполнении. Наши повара приехали из разных провинций Китая и привезли с собой знание региональных особенностей приготовления блюд. Фирменное блюдо – пекинская утка – готовится по старинному рецепту.',
                'city': 'Новосибирск',
                'address': 'Красный проспект, 25',
                'phone': '+7 (383) 345-67-89',
            },
            {
                'name': 'Эль Патио',
                'cuisine': 'Испанская кухня',
                'description': 'Испанский ресторан с традиционными тапас, паэльей и сангрией. Яркая атмосфера, живая музыка фламенко по выходным и превосходная кухня сделают ваш вечер незабываемым. Каждое блюдо готовится из свежайших продуктов по оригинальным рецептам.',
                'city': 'Сочи',
                'address': 'ул. Морская, 11',
                'phone': '+7 (862) 654-32-10',
            },
        ]

        template_index = (index - 1) % len(restaurant_templates)
        template = restaurant_templates[template_index]

        opening_hours = self._generate_opening_hours()

        restaurant = Restaurant.objects.create(
            name=template['name'],
            description=f"{template['description']} Наш ресторан {template['cuisine']} предлагает уютную атмосферу и отличное обслуживание.",
            address=template['address'],
            city=template['city'],
            postal_code=f"1{index}0000",
            country="Россия",
            phone=template['phone'],
            email=f"info@{template['name'].lower().replace(' ', '')}.ru",
            website=f"https://www.{template['name'].lower().replace(' ', '')}.ru",
            opening_hours=opening_hours,
            is_active=True
        )

        num_managers = random.randint(1, min(2, len(managers)))
        selected_managers = random.sample(managers, num_managers)
        for manager in selected_managers:
            restaurant.managers.add(manager)

        return restaurant

    def _generate_opening_hours(self):
        """Генерирует реалистичные часы работы ресторана"""
        opening_hours = {}
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

        weekday_open = "10:00"
        weekday_close = "22:00"
        weekend_open = "11:00"
        weekend_close = "23:00"

        for day in days:
            if day in ['saturday', 'sunday']:
                opening_hours[day] = {
                    "open": weekend_open,
                    "close": weekend_close
                }
            else:
                opening_hours[day] = {
                    "open": weekday_open,
                    "close": weekday_close
                }

        if random.random() < 0.2:
            opening_hours.pop('monday', None)

        return opening_hours

    def _create_table(self, restaurant, table_number):
        """Создает столик для ресторана"""
        shapes = [
            Table.TableShape.SQUARE,
            Table.TableShape.ROUND,
            Table.TableShape.RECTANGULAR,
            Table.TableShape.OVAL,
        ]
        shape_weights = [0.4, 0.3, 0.2, 0.1]
        shape = random.choices(shapes, weights=shape_weights)[0]

        capacities = [2, 2, 2, 4, 4, 4, 6, 6, 8, 10]
        capacity = random.choice(capacities)

        statuses = [
            Table.TableStatus.FREE,
            Table.TableStatus.FREE,
            Table.TableStatus.FREE,
            Table.TableStatus.RESERVED,
            Table.TableStatus.OCCUPIED,
            Table.TableStatus.UNAVAILABLE,
        ]
        status_weights = [0.6, 0.6, 0.6, 0.1, 0.05, 0.05]  # Веса для статусов
        status = random.choices(statuses, weights=status_weights)[0]

        position_x = random.uniform(10, 90)
        position_y = random.uniform(10, 90)

        table = Table.objects.create(
            restaurant=restaurant,
            number=table_number,
            capacity=capacity,
            status=status,
            shape=shape,
            width=random.randint(60, 100) if shape in [Table.TableShape.SQUARE, Table.TableShape.RECTANGULAR] else None,
            length=random.randint(60, 120) if shape in [Table.TableShape.RECTANGULAR, Table.TableShape.OVAL] else None,
            min_spend=random.choice([None, 1500, 2000, 2500, 3000]) if capacity >= 6 else None,
            location_description=random.choice([
                "Возле окна",
                "В центре зала",
                "У камина",
                "В тихом углу",
                "На террасе",
                "У бара",
                None,
                None
            ]),
            is_active=True,
            position_x=position_x,
            position_y=position_y
        )

        return table

    def _create_reservation(self, restaurant, is_today=False):
        """Создает бронирование для ресторана"""
        tables = restaurant.tables.filter(is_active=True).exclude(status=Table.TableStatus.UNAVAILABLE)
        if not tables.exists():
            return None

        table = random.choice(tables)

        if is_today:
            reservation_date = timezone.now().date()
        else:
            days_offset = random.randint(1, 30)
            reservation_date = timezone.now().date() + timedelta(days=days_offset)

        day_name = reservation_date.strftime('%A').lower()

        if day_name not in restaurant.opening_hours:
            for day in restaurant.opening_hours:
                day_name = day
                break

        if day_name in restaurant.opening_hours:
            try:
                open_time = datetime.strptime(restaurant.opening_hours[day_name]['open'], '%H:%M').time()
                close_time = datetime.strptime(restaurant.opening_hours[day_name]['close'], '%H:%M').time()

                open_minutes = open_time.hour * 60 + open_time.minute
                close_minutes = close_time.hour * 60 + close_time.minute

                max_reservation_minutes = close_minutes - 120

                if max_reservation_minutes <= open_minutes:
                    reservation_minutes = (open_minutes + close_minutes) // 2
                else:
                    reservation_minutes = random.randint(open_minutes, max_reservation_minutes)

                reservation_minutes = (reservation_minutes // 30) * 30
                reservation_hour = reservation_minutes // 60
                reservation_minute = reservation_minutes % 60

                reservation_time = time(reservation_hour, reservation_minute)

                end_datetime = datetime.combine(datetime.today(), reservation_time) + timedelta(hours=2)
                end_time = end_datetime.time()
            except (ValueError, KeyError):
                reservation_time = time(19, 0)
                end_time = time(21, 0)
        else:
            reservation_time = time(19, 0)
            end_time = time(21, 0)

        if is_today:
            statuses = [
                Reservation.ReservationStatus.PENDING,
                Reservation.ReservationStatus.CONFIRMED,
                Reservation.ReservationStatus.CANCELLED,
                Reservation.ReservationStatus.COMPLETED
            ]
            status_weights = [0.2, 0.5, 0.1, 0.2]
        else:
            statuses = [
                Reservation.ReservationStatus.PENDING,
                Reservation.ReservationStatus.CONFIRMED,
                Reservation.ReservationStatus.CANCELLED
            ]
            status_weights = [0.3, 0.6, 0.1]

        status = random.choices(statuses, weights=status_weights)[0]

        first_names = [
            "Александр", "Сергей", "Дмитрий", "Ирина", "Екатерина",
            "Ольга", "Михаил", "Андрей", "Анна", "Елена",
            "Алексей", "Наталья", "Николай", "Татьяна", "Владимир"
        ]

        last_names = [
            "Иванов", "Смирнов", "Кузнецов", "Попов", "Соколов",
            "Лебедев", "Козлов", "Новиков", "Морозов", "Петров",
            "Волков", "Соловьев", "Васильев", "Зайцев", "Павлов"
        ]

        customer_name = f"{random.choice(first_names)} {random.choice(last_names)}"
        customer_email = f"{customer_name.lower().replace(' ', '.')}@example.com"
        customer_phone = f"+7 ({random.randint(900, 999)}) {random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(10, 99)}"

        reservation = Reservation.objects.create(
            restaurant=restaurant,
            table=table,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            number_of_guests=random.randint(1, table.capacity),
            reservation_date=reservation_date,
            reservation_time=reservation_time,
            end_time=end_time,
            status=status,
            special_requests=random.choice([
                "Хотим столик у окна",
                "Празднуем день рождения",
                "Нужен детский стульчик",
                "Будет гость с аллергией на орехи",
                "Предпочитаем тихое место",
                None,
                None,
                None
            ]),
            dietary_preferences=random.choice([
                {"vegetarian": True},
                {"vegan": True},
                {"gluten_free": True},
                {"lactose_intolerant": True},
                None,
                None
            ]),
            allergy_information=random.choice([
                {"nuts": True},
                {"seafood": True},
                {"dairy": True},
                {"gluten": True},
                None,
                None,
                None,
                None
            ])
        )

        if status == Reservation.ReservationStatus.CONFIRMED and is_today:
            current_time = timezone.now().time()
            if current_time >= reservation_time and current_time < end_time:
                table.status = Table.TableStatus.OCCUPIED
            else:
                table.status = Table.TableStatus.RESERVED
            table.save(update_fields=["status"])

        return reservation

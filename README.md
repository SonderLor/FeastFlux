# FeastFlux 🍽️

FeastFlux is a comprehensive restaurant management system built with Django that transforms food service operations by combining order management with nutritional transparency.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2-green.svg)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🌟 Key Features

- **Dynamic Nutritional Analysis**: Calculate nutritional values (calories, protein, fat, carbs) and allergens for entire orders in real-time
- **Dietary Preference Filtering**: Filter menu by dietary requirements (vegetarian, vegan, gluten-free, etc.)
- **Allergy Warnings**: Visual alerts for allergens present in orders
- **Role-Based Access**: Specialized interfaces for waitstaff, kitchen, and management
- **Comprehensive Order Management**: Track orders from creation to payment
- **Analytics & Reporting**: Gain insights into sales, popular dishes, and more

## 🏗️ Architecture

FeastFlux is built with a modular architecture consisting of:

- **Core**: Base configurations and utilities
- **Users**: User authentication and role management
- **Restaurants**: Restaurant and table management
- **Menu**: Menu items, categories, ingredients, and allergens
- **Orders**: Order processing and tracking
- **Kitchen**: Kitchen display system
- **Analytics**: Reports and business insights

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose
- Git

### Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/SonderLor/FeastFlux.git
   cd FeastFlux
   ```

2. Create an environment file:
    ```bash
    cp .env.example .env
    # Edit .env with your settings
    ```
   
3. Build and start the containers:
    ```bash
    docker-compose up -d
    ```
4. Create a superuser:
    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```
5. Access the application at http://localhost

### Development Setup

For local development:

1. Create a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
2. Install dependencies:
    ```bash
    pip install uv
    uv pip install -e .
    ```

3. Create an environment file:
    ```bash
    cp .env.example .env
    # Edit .env with your settings
    ```
   
4. Run migrations:
    ```bash
    python manage.py migrate
    ```
   
5. Create a superuser:
    ```bash
    python manage.py createsuperuser
    ```
   
6. Run the development server:
    ```bash
    python manage.py runserver
    ```

## 🧩 System Components
#### User Roles
- **Administrator**: Full system access and configuration
- **Manager**: Restaurant management, reports, menu management
- **Waiter**: Order taking, table management
- **Kitchen Staff**: Order preparation and status updates

#### Core Workflows
- **Table Management**: Track table availability and occupancy
- **Menu Management**: Create and update menu items with nutritional data
- **Order Processing**: From creation to payment
- **Kitchen Operations**: Order preparation and status updates
- **Reporting**: Sales, popular items, nutritional analytics

## 📝 License
This project is licensed under the MIT License - see the LICENSE file for details.

## 🛠️ Technologies
- **Backend**: Django 5.2
- **Database**: PostgreSQL 15
- **Task Queue**: Celery with Redis
- **Caching**: Redis
- **Containerization**: Docker & Docker Compose
- **CSS Framework**: Bootstrap 5

## 📊 Data Models
- **User Management**: Custom User model with role-based permissions
- **Restaurant**: Tables with status tracking
- **Menu**: Categories, Items, Ingredients, Allergens
- **Order**: Order tracking with status workflow
- **Analytics**: Sales and performance data

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Contact
For questions or support, please contact your-email@example.com.
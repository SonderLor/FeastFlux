from django.shortcuts import render
from django.views.generic import TemplateView
from restaurants.models import Restaurant


def home_view(request):
    """Главная страница (лендинг)."""
    featured_restaurants = Restaurant.objects.filter(is_active=True)[:4]

    context = {
        'featured_restaurants': featured_restaurants
    }
    return render(request, 'core/home.html', context)


class AboutView(TemplateView):
    """Страница 'О нас'."""
    template_name = 'core/about.html'


class ContactView(TemplateView):
    """Страница контактов."""
    template_name = 'core/contact.html'


class PrivacyPolicyView(TemplateView):
    """Политика конфиденциальности."""
    template_name = 'core/privacy_policy.html'


class TermsOfServiceView(TemplateView):
    """Условия использования."""
    template_name = 'core/terms_of_service.html'

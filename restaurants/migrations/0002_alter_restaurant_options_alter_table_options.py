# Generated by Django 5.2 on 2025-05-16 19:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("restaurants", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="restaurant",
            options={
                "ordering": ["name"],
                "permissions": [("manage_restaurant", "Может управлять рестораном")],
                "verbose_name": "Ресторан",
                "verbose_name_plural": "Рестораны",
            },
        ),
        migrations.AlterModelOptions(
            name="table",
            options={
                "ordering": ["restaurant", "number"],
                "permissions": [("view_public_tables", "Может публично просматривать столики")],
                "verbose_name": "Столик",
                "verbose_name_plural": "Столики",
            },
        ),
    ]

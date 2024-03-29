# Generated by Django 2.2.13 on 2021-03-16 12:58

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0018_add_verified_personal_information_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="implicit_connection",
            field=models.BooleanField(
                default=False,
                help_text="If enabled, this service doesn't require explicit service connections to profiles",
            ),
        ),
    ]

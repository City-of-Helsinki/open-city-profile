# Generated by Django 2.2.4 on 2019-11-12 07:21

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("services", "0005_move_service_to_model")]

    operations = [
        migrations.AlterModelOptions(
            name="service",
            options={
                "permissions": (
                    ("can_manage_profiles", "Can manage profiles"),
                    ("can_view_profiles", "Can view profiles"),
                )
            },
        )
    ]

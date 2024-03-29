# Generated by Django 2.2.8 on 2020-03-24 14:23

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("profiles", "0021_increase_postal_code_field_length")]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="newsletters_via_email",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="newsletters_via_sms",
            field=models.BooleanField(default=False),
        ),
    ]

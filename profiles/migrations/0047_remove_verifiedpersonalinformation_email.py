# Generated by Django 2.2.24 on 2021-06-30 14:43

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0046_change_null_to_empty_value_field_implementation__noop"),
    ]

    operations = [
        migrations.RemoveField(model_name="verifiedpersonalinformation", name="email"),
    ]

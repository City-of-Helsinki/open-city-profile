# Generated by Django 2.2.8 on 2020-01-09 11:36

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("profiles", "0017_allow_profile_user_null_and_protect")]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="nickname",
            field=models.CharField(blank=True, default="", max_length=32),
            preserve_default=False,
        )
    ]

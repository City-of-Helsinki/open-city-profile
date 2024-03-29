# Generated by Django 2.2.4 on 2019-11-05 09:27

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("profiles", "0009_add_profile_uuid"),
        ("services", "0003_pre_profile_uuid"),
    ]

    operations = [
        migrations.RemoveField("profile", "id"),
        migrations.RenameField(model_name="profile", old_name="uuid", new_name="id"),
        migrations.AlterField(
            model_name="profile",
            name="id",
            field=models.UUIDField(default=uuid.uuid4, serialize=False, editable=False),
        ),
        migrations.AlterField(
            model_name="profile",
            name="id",
            field=models.UUIDField(
                primary_key=True, default=uuid.uuid4, serialize=False, editable=False
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="concepts_of_interest",
            field=models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="profile",
            name="divisions_of_interest",
            field=models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name="legalrelationship",
            name="representative",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="representatives",
                to="profiles.Profile",
            ),
        ),
        migrations.AlterField(
            model_name="legalrelationship",
            name="representee",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="representees",
                to="profiles.Profile",
            ),
        ),
    ]

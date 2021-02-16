# Generated by Django 2.2.13 on 2020-11-11 06:33

from django.db import migrations, models
import django.db.models.deletion
import encrypted_fields.fields
import utils.models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0030_verifiedpersonalinformationpermanentaddress"),
    ]

    operations = [
        migrations.CreateModel(
            name="VerifiedPersonalInformationTemporaryAddress",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "street_address",
                    encrypted_fields.fields.EncryptedCharField(
                        blank=True, max_length=1024
                    ),
                ),
                (
                    "postal_code",
                    encrypted_fields.fields.EncryptedCharField(
                        blank=True, max_length=1024
                    ),
                ),
                (
                    "post_office",
                    encrypted_fields.fields.EncryptedCharField(
                        blank=True, max_length=1024
                    ),
                ),
                (
                    "verified_personal_information",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="temporary_address",
                        to="profiles.VerifiedPersonalInformation",
                    ),
                ),
            ],
            options={"abstract": False,},
            bases=(models.Model, utils.models.UpdateMixin),
        ),
    ]
import encrypted_fields.fields
from django.conf import settings
from django.db import migrations


def copy_data_to_searchable_field(apps, schema_editor):
    VerifiedPersonalInformation = apps.get_model(
        "profiles", "VerifiedPersonalInformation"
    )
    for obj in VerifiedPersonalInformation.objects.all():
        obj.new_national_identification_number = obj.national_identification_number
        obj.save()


def copy_data_from_searchable_field(apps, schema_editor):
    VerifiedPersonalInformation = apps.get_model(
        "profiles", "VerifiedPersonalInformation"
    )
    for obj in VerifiedPersonalInformation.objects.all():
        obj.national_identification_number = obj.new_national_identification_number
        obj.save()


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0036_start_using_raw_verifiedpersonalinformation_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="verifiedpersonalinformation",
            name="_national_identification_number_data",
            field=encrypted_fields.fields.EncryptedCharField(
                blank=True,
                help_text="Finnish national identification number.",
                max_length=1024,
            ),
        ),
        migrations.AddField(
            model_name="verifiedpersonalinformation",
            name="new_national_identification_number",
            field=encrypted_fields.fields.SearchField(
                db_index=True,
                encrypted_field_name="_national_identification_number_data",
                hash_key=settings.SALT_NATIONAL_IDENTIFICATION_NUMBER,
                max_length=66,
                null=True,
            ),
        ),
        migrations.RunPython(
            copy_data_to_searchable_field, reverse_code=copy_data_from_searchable_field
        ),
    ]

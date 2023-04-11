from django.db import migrations, models


def copy_names_to_raw_fields(apps, schema_editor):
    VerifiedPersonalInformation = apps.get_model(
        "profiles", "VerifiedPersonalInformation"
    )
    for obj in VerifiedPersonalInformation.objects.all():
        obj.new_first_name = obj.first_name
        obj.new_last_name = obj.last_name
        obj.save()


def copy_names_from_raw_fields(apps, schema_editor):
    VerifiedPersonalInformation = apps.get_model(
        "profiles", "VerifiedPersonalInformation"
    )
    for obj in VerifiedPersonalInformation.objects.all():
        obj.first_name = obj.new_first_name
        obj.last_name = obj.new_last_name
        obj.save()


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0034_add_help_texts_to_fields__noop"),
    ]

    operations = [
        migrations.AddField(
            model_name="verifiedpersonalinformation",
            name="new_first_name",
            field=models.CharField(
                blank=True, help_text="First name(s).", max_length=1024
            ),
        ),
        migrations.AddField(
            model_name="verifiedpersonalinformation",
            name="new_last_name",
            field=models.CharField(blank=True, help_text="Last name.", max_length=1024),
        ),
        migrations.RunPython(
            copy_names_to_raw_fields, reverse_code=copy_names_from_raw_fields
        ),
    ]

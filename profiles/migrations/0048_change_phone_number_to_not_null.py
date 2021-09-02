from django.db import migrations, models


def delete_null_phones(apps, schema_editor):
    Phone = apps.get_model("profiles", "Phone")
    Phone.objects.filter(phone=None).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0047_remove_verifiedpersonalinformation_email"),
    ]

    operations = [
        migrations.RunPython(
            delete_null_phones, reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="phone",
            name="phone",
            field=models.CharField(db_index=True, default="-", max_length=255),
            preserve_default=False,
        ),
    ]

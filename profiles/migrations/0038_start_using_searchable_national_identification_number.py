from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0037_add_searchable_national_identification_number"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="verifiedpersonalinformation",
            name="national_identification_number",
        ),
        migrations.RenameField(
            model_name="verifiedpersonalinformation",
            old_name="new_national_identification_number",
            new_name="national_identification_number",
        ),
    ]

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0035_add_raw_verifiedpersonalinformation_names"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="verifiedpersonalinformation", name="first_name"
        ),
        migrations.RenameField(
            model_name="verifiedpersonalinformation",
            old_name="new_first_name",
            new_name="first_name",
        ),
        migrations.RemoveField(
            model_name="verifiedpersonalinformation", name="last_name"
        ),
        migrations.RenameField(
            model_name="verifiedpersonalinformation",
            old_name="new_last_name",
            new_name="last_name",
        ),
    ]

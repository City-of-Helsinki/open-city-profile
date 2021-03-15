from django.db import migrations


def remove_contenttypes(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="account").delete()
    ContentType.objects.filter(app_label="socialaccount").delete()


class Migration(migrations.Migration):
    dependencies = []

    tables_to_remove = [
        "account_emailaddress",
        "account_emailconfirmation",
        "socialaccount_socialaccount",
        "socialaccount_socialapp",
        "socialaccount_socialapp_sites",
        "socialaccount_socialtoken",
    ]

    operations = [
        migrations.RunPython(remove_contenttypes),
        migrations.RunSQL(
            "DROP TABLE IF EXISTS {}".format(", ".join(tables_to_remove))
        ),
    ]

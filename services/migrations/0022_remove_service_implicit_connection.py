from django.db import migrations


def set_implicit_connection_to_profile_service(apps, schema_editor):
    Service = apps.get_model("services", "Service")

    Service.objects.filter(is_profile_service=True).update(implicit_connection=True)


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0021_add_is_profile_service_field"),
    ]

    operations = [
        migrations.RunPython(
            migrations.RunPython.noop,
            reverse_code=set_implicit_connection_to_profile_service,
        ),
        migrations.RemoveField(model_name="service", name="implicit_connection"),
    ]

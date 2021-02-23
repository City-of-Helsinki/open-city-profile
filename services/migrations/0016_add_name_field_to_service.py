from django.db import migrations, models


def copy_service_type_to_name(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    for obj in Service.objects.all():
        obj.name = obj.service_type.value
        obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0015_serviceclientid"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="name",
            field=models.CharField(max_length=200, null=True, unique=True),
        ),
        migrations.RunPython(
            copy_service_type_to_name, reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="service",
            name="name",
            field=models.CharField(max_length=200, unique=True),
        ),
    ]

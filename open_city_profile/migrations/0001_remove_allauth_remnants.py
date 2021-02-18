from django.db import migrations


class Migration(migrations.Migration):
    dependencies = []

    # Removed the operations for destroying data, to allow for doing a
    # rollback during the next release.
    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
        migrations.RunSQL(migrations.RunSQL.noop, migrations.RunSQL.noop),
    ]

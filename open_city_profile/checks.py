from django.core.checks import register, Tags, Warning
from django.db import connections


@register(Tags.database)
def check_obsolete_database_tables(app_configs, **kwargs):
    KNOWN_UNMANAGED_TABLE_NAMES = {"django_migrations"}

    errors = []

    all_connections = connections.all()

    # Only one database connection is supported
    if len(all_connections) == 1:
        conn = all_connections[0]

        existing_table_names = conn.introspection.table_names()
        expected_table_names = conn.introspection.django_table_names()

        possibly_obsolete_table_names = (
            set(existing_table_names)
            - set(expected_table_names)
            - KNOWN_UNMANAGED_TABLE_NAMES
        )
        if possibly_obsolete_table_names:
            possibly_obsolete_table_names = ", ".join(
                sorted(possibly_obsolete_table_names)
            )
            errors.append(
                Warning(
                    f"Possibly obsolete tables exist in the database: {possibly_obsolete_table_names}.",
                    hint="Perhaps these should be removed.",
                )
            )

    return errors

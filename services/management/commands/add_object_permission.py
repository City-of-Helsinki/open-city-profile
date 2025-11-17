from guardian.shortcuts import assign_perm

from services.management.commands.object_permission_command import (
    ObjectPermissionCommand,
)


class Command(ObjectPermissionCommand):
    help = "Add service permissions for groups"

    def do_handle(self, permission, group, service):
        assign_perm(permission, group, service)
        self.stdout.write(
            self.style.SUCCESS(
                f"Permission {permission} added for {group} on service {service.name}"
            )
        )

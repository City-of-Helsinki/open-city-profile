from guardian.shortcuts import remove_perm

from services.management.commands.object_permission_command import (
    ObjectPermissionCommand,
)


class Command(ObjectPermissionCommand):
    help = "Remove service permissions for groups"

    def do_handle(self, permission, group, service):
        remove_perm(permission, group, service)
        self.stdout.write(
            self.style.SUCCESS(
                "Permission {} removed for {} on service {}".format(
                    permission, group, service.name
                )
            )
        )

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from services.models import Service

available_permissions = [item[0] for item in Service._meta.permissions]


class ObjectPermissionCommand(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "service", type=str, help="Service, identified by its name",
        )
        parser.add_argument(
            "group_name",
            type=str,
            help="Group name (must match group name in the model)",
        )
        parser.add_argument(
            "permission",
            type=str,
            help="Permission (options: {})".format(", ".join(available_permissions)),
        )

    def do_handle(self, permission, group, service):
        raise NotImplementedError("Implement do_handle in the derived class")

    def handle(self, *args, **kwargs):
        try:
            if kwargs["permission"] not in available_permissions:
                raise ValueError
            service_name = kwargs["service"]
            service = Service.objects.get(name=service_name)
            group = Group.objects.get(name=kwargs["group_name"])
            permission = kwargs["permission"]

            self.do_handle(permission, group, service)
        except Service.DoesNotExist:
            raise CommandError("Invalid service given")
        except Group.DoesNotExist:
            raise CommandError("Invalid group_name given")
        except ValueError:
            raise CommandError("Invalid permission given")

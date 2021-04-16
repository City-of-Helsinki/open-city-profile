from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from guardian.shortcuts import remove_perm

from services.models import Service

available_permissions = [item[0] for item in Service._meta.permissions]


class Command(BaseCommand):
    help = "Remove service permissions for groups"

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

    def handle(self, *args, **kwargs):
        try:
            if kwargs["permission"] not in available_permissions:
                raise ValueError
            service_name = kwargs["service"]
            service = Service.objects.get(name=service_name)
            group = Group.objects.get(name=kwargs["group_name"])
            permission = kwargs["permission"]
            remove_perm(permission, group, service)
            self.stdout.write(
                self.style.SUCCESS(
                    "Permission {} removed for {} on service {}".format(
                        permission, group, service.name
                    )
                )
            )

        except Service.DoesNotExist:
            self.stdout.write(self.style.ERROR("Invalid service given"))
        except Group.DoesNotExist:
            self.stdout.write(self.style.ERROR("Invalid group_name given"))
        except ValueError:
            self.stdout.write(self.style.ERROR("Invalid permission given"))

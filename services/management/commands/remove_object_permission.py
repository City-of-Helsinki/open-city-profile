from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from guardian.shortcuts import remove_perm

from services.enums import ServiceType
from services.models import Service

available_permissions = [item[0] for item in Service._meta.permissions]


class Command(BaseCommand):
    help = "Remove service permissions for groups"

    def add_arguments(self, parser):
        parser.add_argument(
            "service_type",
            type=str,
            help="Service type (must match service type in the model)",
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
            service_type = kwargs["service_type"]
            service = Service.objects.get(service_type=ServiceType[service_type])
            group = Group.objects.get(name=kwargs["group_name"])
            permission = kwargs["permission"]
            remove_perm(permission, group, service)
            self.stdout.write(
                self.style.SUCCESS(
                    "Permission {} removed for {} on service {}".format(
                        permission, group, service.service_type
                    )
                )
            )

        except Service.DoesNotExist:
            self.stdout.write(self.style.ERROR("Invalid service_type given"))
        except Group.DoesNotExist:
            self.stdout.write(self.style.ERROR("Invalid group_name given"))
        except ValueError:
            self.stdout.write(self.style.ERROR("Invalid permission given"))

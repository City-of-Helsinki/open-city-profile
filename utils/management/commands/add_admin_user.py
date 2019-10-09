from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Add admin user"

    def add_arguments(self, parser):
        parser.add_argument(
            "-u", "--username", type=str, help="Username", default="admin"
        )
        parser.add_argument(
            "-p", "--password", type=str, help="Password", default="admin"
        )
        parser.add_argument(
            "-e", "--email", type=str, help="Email", default="admin@example.com"
        )

    def handle(self, *args, **kwargs):
        if not get_user_model().objects.filter(username=kwargs["username"]).count():
            get_user_model().objects.create_superuser(
                kwargs["username"], kwargs["email"], kwargs["password"]
            )

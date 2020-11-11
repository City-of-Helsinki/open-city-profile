import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import serializers
from django.core.management.base import BaseCommand
from helusers.models import ADGroup

from youths.models import AdditionalContactPerson, YouthProfile

User = get_user_model()

YOUTH_MEMBERSHIP_GROUP_NAME = "youth_membership"


class Command(BaseCommand):
    help = "Export youth data as a JSON file for the youth-membership backend's import_youth_data command."

    def add_arguments(self, parser):
        parser.add_argument("filename", nargs="+", type=str)

    def handle(self, *args, **kwargs):
        ADGroup.natural_key = lambda x: (x.name,)
        YouthProfile.natural_key = lambda x: (str(x.profile_id),)

        youths = YouthProfile.objects.all()
        user_data = self._serialize(
            User.objects.filter(profile__youth_profile__in=youths),
            use_natural_primary_keys=True,
            fields=[
                "password",
                "last_login",
                "is_superuser",
                "username",
                "first_name",
                "last_name",
                "email",
                "is_staff",
                "is_active",
                "date_joined",
                "uuid",
                "department_name",
            ],  # all except groups, user_permissions and ad_groups (they should be empty, but just in case)
        )

        user_uuids_by_youth_id = {
            youth.pk: str(youth.profile.user.uuid)
            for youth in youths.select_related("profile__user")
            if youth.profile.user
        }
        youth_data = self._serialize(youths)
        for obj in youth_data:
            # in youth-membership User is related directly to YouthProfile.
            # we'll want this to be used as a natural key when deserializing, hence the tuple
            obj["fields"]["user"] = (user_uuids_by_youth_id.get(obj["pk"]),)
            # in youth-membership YouthProfile pk should be the pk of the corresponding Profile
            obj["pk"] = obj["fields"].pop("profile")

        additional_contact_person_data = self._serialize(
            AdditionalContactPerson.objects.all(), use_natural_foreign_keys=True
        )
        for a in additional_contact_person_data:
            a.pop("pk")

        try:
            ad_groups = ADGroup.objects.filter(
                groups__group=Group.objects.get(name=YOUTH_MEMBERSHIP_GROUP_NAME)
            )
        except Group.DoesNotExist:
            ad_groups = ()
        ad_group_data = self._serialize(ad_groups, use_natural_primary_keys=True)

        filename = kwargs["filename"][0]
        with open(filename, "w") as outfile:
            outfile.write(
                json.dumps(
                    user_data
                    + youth_data
                    + additional_contact_person_data
                    + ad_group_data,
                    indent=4,
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully wrote {len(user_data)} users and "
                f"{len(youth_data)} youth profiles to {filename}"
            )
        )

    @staticmethod
    def _serialize(data, **kwargs):
        return json.loads(serializers.serialize("json", data, **kwargs))

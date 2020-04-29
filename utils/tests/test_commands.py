from django.contrib.auth.models import Group
from django.core.management import call_command

from profiles.models import Profile
from services.enums import ServiceType
from services.models import AllowedDataField, Service
from users.models import User
from utils.utils import DATA_FIELD_VALUES
from youths.models import YouthProfile


def test_command_seed_data_works_without_arguments():
    call_command("seed_data")

    assert Service.objects.count() == len(ServiceType)
    assert Group.objects.count() == len(ServiceType)
    assert User.objects.filter(is_superuser=True).count() == 0
    assert AllowedDataField.objects.count() == len(DATA_FIELD_VALUES)


def test_command_seed_data_initializes_development_data():
    args = [
        "--development",
        "--superuser",
    ]
    call_command("seed_data", *args)

    anonymous_users = 1
    admin_users = 1
    normal_users = 50
    assert (
        User.objects.count()
        == normal_users + len(ServiceType) + admin_users + anonymous_users
    )
    assert Profile.objects.count() == normal_users
    assert YouthProfile.objects.count() == 10
    assert User.objects.filter(is_superuser=True).count() == admin_users


def test_command_seed_data_works_withs_arguments():
    args = [
        "--development",
        "--profilecount=20",
        "--youthprofilepercentage=0.5",
        "--locale=fi_FI",
        "--superuser",
    ]
    call_command("seed_data", *args)
    assert Profile.objects.count() == 20
    assert YouthProfile.objects.count() == 10
    assert User.objects.filter(is_superuser=True).count() == 1

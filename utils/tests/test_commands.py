import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command

from profiles.models import Profile
from services.models import AllowedDataField, Service
from users.models import User
from utils.management.commands.seed_development_data import DATA_FIELD_VALUES
from utils.utils import SERVICES


@pytest.mark.parametrize("create_superuser", [True, False])
def test_command_seed_development_data_initializes_development_data(create_superuser):
    args = [
        "--no-clear",  # Flushing not needed in tests + it caused test failures
    ]
    if create_superuser:
        args.append("--superuser")
        admin_users = 1
    else:
        admin_users = 0
    call_command("seed_development_data", *args)

    normal_users = 50
    assert Service.objects.count() == len(SERVICES)
    assert Group.objects.count() == len(SERVICES)
    assert User.objects.count() == normal_users + len(SERVICES) + admin_users
    assert User.objects.filter(is_superuser=True).count() == admin_users
    assert Profile.objects.count() == normal_users
    assert AllowedDataField.objects.count() == len(DATA_FIELD_VALUES)


def test_command_seed_development_data_with_more_arguments():
    args = [
        "--no-clear",  # Flushing not needed in tests + it caused test failures
        "--profilecount=20",
        "--locale=fi_FI",
        "--superuser",
    ]
    call_command("seed_development_data", *args)
    assert Profile.objects.count() == 20
    assert User.objects.filter(is_superuser=True).count() == 1

from django.db import models
from django.utils.translation import gettext_lazy as _
from helusers.models import AbstractUser


class User(AbstractUser):
    is_system_user = models.BooleanField(
        _("system user status"),
        default=False,
        help_text=_(
            "Designates that this user represents another system instead of a human being."  # noqa: E501
        ),
    )

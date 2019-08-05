import reversion

from helusers.models import AbstractUser


@reversion.register()
class User(AbstractUser):
    pass

from profiles.loaders import (
    AddressesByProfileIdLoader,
    EmailsByProfileIdLoader,
    PhonesByProfileIdLoader,
    PrimaryAddressForProfileLoader,
    PrimaryEmailForProfileLoader,
    PrimaryPhoneForProfileLoader,
)

LOADERS = {
    "addresses_by_profile_id_loader": AddressesByProfileIdLoader,
    "emails_by_profile_id_loader": EmailsByProfileIdLoader,
    "phones_by_profile_id_loader": PhonesByProfileIdLoader,
    "primary_address_for_profile_loader": PrimaryAddressForProfileLoader,
    "primary_email_for_profile_loader": PrimaryEmailForProfileLoader,
    "primary_phone_for_profile_loader": PrimaryPhoneForProfileLoader,
}


class GQLDataLoaders:
    def __init__(self):
        self.cached_loaders = False

    def resolve(self, next, root, info, **kwargs):
        context = info.context

        if not self.cached_loaders:
            for loader_name, loader_class in LOADERS.items():
                setattr(context, loader_name, loader_class())

            self.cached_loaders = True

        return next(root, info, **kwargs)

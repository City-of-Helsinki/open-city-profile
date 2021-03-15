from collections import defaultdict

from promise import Promise
from promise.dataloader import DataLoader

from profiles.models import Address, Email, Phone


def loader_for_profile(model):
    class BaseByProfileIdLoader(DataLoader):
        def batch_load_fn(self, profile_ids):
            items_by_profile_ids = defaultdict(list)
            for item in model.objects.filter(profile_id__in=profile_ids).iterator():
                items_by_profile_ids[item.profile_id].append(item)
            return Promise.resolve(
                [items_by_profile_ids.get(profile_id, []) for profile_id in profile_ids]
            )

    return BaseByProfileIdLoader


def loader_for_profile_primary(model):
    class BaseByProfileIdPrimaryLoader(DataLoader):
        def batch_load_fn(self, profile_ids):
            items_by_profile_ids = defaultdict()
            for item in model.objects.filter(
                profile_id__in=profile_ids, primary=True
            ).iterator():
                items_by_profile_ids[item.profile_id] = item

            return Promise.resolve(
                [items_by_profile_ids.get(profile_id) for profile_id in profile_ids]
            )

    return BaseByProfileIdPrimaryLoader


EmailsByProfileIdLoader = loader_for_profile(Email)
PhonesByProfileIdLoader = loader_for_profile(Phone)
AddressesByProfileIdLoader = loader_for_profile(Address)

PrimaryEmailForProfileLoader = loader_for_profile_primary(Email)
PrimaryPhoneForProfileLoader = loader_for_profile_primary(Phone)
PrimaryAddressForProfileLoader = loader_for_profile_primary(Address)


__all__ = [
    "AddressesByProfileIdLoader",
    "EmailsByProfileIdLoader",
    "PhonesByProfileIdLoader",
    "PrimaryAddressForProfileLoader",
    "PrimaryEmailForProfileLoader",
    "PrimaryPhoneForProfileLoader",
]

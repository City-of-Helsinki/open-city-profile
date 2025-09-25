import uuid
from collections import defaultdict
from collections.abc import Callable

from profiles.models import Address, Email, Phone


def loader_for_profile(model) -> Callable:
    def batch_load_fn(profile_ids: list[uuid.UUID]) -> list[list[model]]:
        items_by_profile_ids = defaultdict(list)
        for item in model.objects.filter(profile_id__in=profile_ids).iterator():
            items_by_profile_ids[item.profile_id].append(item)

        return [items_by_profile_ids[profile_id] for profile_id in profile_ids]

    return batch_load_fn


def loader_for_profile_primary(model) -> Callable:
    def batch_load_fn(profile_ids: list[uuid.UUID]) -> list[model]:
        items_by_profile_ids = {}
        for item in model.objects.filter(
            profile_id__in=profile_ids, primary=True
        ).iterator():
            items_by_profile_ids[item.profile_id] = item

        return [items_by_profile_ids.get(profile_id) for profile_id in profile_ids]

    return batch_load_fn


addresses_by_profile_id_loader = loader_for_profile(Address)
emails_by_profile_id_loader = loader_for_profile(Email)
phones_by_profile_id_loader = loader_for_profile(Phone)

primary_address_for_profile_loader = loader_for_profile_primary(Address)
primary_email_for_profile_loader = loader_for_profile_primary(Email)
primary_phone_for_profile_loader = loader_for_profile_primary(Phone)


__all__ = [
    "addresses_by_profile_id_loader",
    "emails_by_profile_id_loader",
    "phones_by_profile_id_loader",
    "primary_address_for_profile_loader",
    "primary_email_for_profile_loader",
    "primary_phone_for_profile_loader",
]

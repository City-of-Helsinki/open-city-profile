from collections import defaultdict

from promise import Promise
from promise.dataloader import DataLoader

from profiles.models import Email


class EmailsByProfileIdLoader(DataLoader):
    def batch_load_fn(self, profile_ids):
        emails_by_profile_ids = defaultdict(list)
        for email in Email.objects.filter(profile_id__in=profile_ids).iterator():
            emails_by_profile_ids[email.profile_id].append(email)
        return Promise.resolve(
            [emails_by_profile_ids.get(profile_id, []) for profile_id in profile_ids]
        )

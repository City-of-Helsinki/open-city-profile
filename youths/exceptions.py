from open_city_profile.exceptions import ProfileGraphQLError


# Youth Profile
class ApproverEmailCannotBeEmptyForMinorsError(ProfileGraphQLError):
    """Approver email is required for youth under 18 years old"""


class CannotCreateYouthProfileIfUnder13YearsOldError(ProfileGraphQLError):
    """Under 13 years old cannot create youth profile"""


class CannotRenewYouthProfileError(ProfileGraphQLError):
    """Youth profile is already renewed or not yet in the next renew window"""


class CannotSetPhotoUsagePermissionIfUnder15YearsError(ProfileGraphQLError):
    """A youth cannot set photo usage permission by himself if he is under 15 years old"""

from graphql import GraphQLError


class ProfileGraphQLError(GraphQLError):
    """GraphQLError that is not sent to Sentry."""


# Open city profile


class APINotImplementedError(ProfileGraphQLError):
    """The functionality is not yet implemented"""


class ConnectedServiceDeletionFailedError(GraphQLError):
    """Deleting a connected service has failed.

    This should be logged.
    """


class ConnectedServiceDeletionNotAllowedError(ProfileGraphQLError):
    """Deleting a connected service is not allowed."""


class CannotPerformThisActionWithGivenServiceType(ProfileGraphQLError):
    """Incorrect service type for given action"""


class InvalidEmailFormatError(ProfileGraphQLError):
    """Email must be in valid email format"""


class ProfileDoesNotExistError(ProfileGraphQLError):
    """Profile does not exist"""


class ProfileHasNoPrimaryEmailError(ProfileGraphQLError):
    """Profile does not have a primary email address"""


class ProfileMustHaveOnePrimaryEmail(ProfileGraphQLError):
    """Profile must have exactly one primary email"""


class ServiceAlreadyExistsError(ProfileGraphQLError):
    """Service already connected for the user"""


class TokenExpiredError(ProfileGraphQLError):
    """Token has expired"""


# Youth Profile


class ApproverEmailCannotBeEmptyForMinorsError(ProfileGraphQLError):
    """Approver email is required for youth under 18 years old"""


class CannotCreateYouthProfileIfUnder13YearsOldError(ProfileGraphQLError):
    """Under 13 years old cannot create youth profile"""


class CannotRenewYouthProfileError(ProfileGraphQLError):
    """Youth profile is already renewed or not yet in the next renew window"""


class CannotSetPhotoUsagePermissionIfUnder15YearsError(ProfileGraphQLError):
    """A youth cannot set photo usage permission by himself if he is under 15 years old"""

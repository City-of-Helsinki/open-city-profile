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


class MissingGDPRApiTokenError(ProfileGraphQLError):
    """API token intended for GDPR API of a service is missing."""


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


class ServiceAlreadyExistsError(ProfileGraphQLError):
    """Service already connected for the user"""


class ServiceNotIdentifiedError(ProfileGraphQLError):
    """The requester failed to identify the service they are coming from"""


class TokenExpiredError(ProfileGraphQLError):
    """Token has expired"""


class TokenExchangeError(Exception):
    """OAuth/OIDC token exchange related exception."""

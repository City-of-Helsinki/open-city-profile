from graphql import GraphQLError


class ProfileGraphQLError(GraphQLError):
    """GraphQLError that is not sent to Sentry."""


# Open city profile


class ProfileAlreadyExistsForUserError(ProfileGraphQLError):
    """Profile already exists for the user"""


class ConnectedServiceDataQueryFailedError(GraphQLError):
    """Querying data from a connected service failed."""


class ConnectedServiceDeletionFailedError(GraphQLError):
    """Deleting a connected service has failed.

    This should be logged.
    """


class MissingGDPRApiTokenError(ProfileGraphQLError):
    """API token intended for GDPR API of a service is missing."""


class ConnectedServiceDeletionNotAllowedError(ProfileGraphQLError):
    """Deleting a connected service is not allowed."""


class DataConflictError(ProfileGraphQLError):
    """Conflicting data encountered"""


class InvalidEmailFormatError(ProfileGraphQLError):
    """Email must be in valid email format"""


class ProfileMustHavePrimaryEmailError(ProfileGraphQLError):
    """A profile must have a primary email"""


class ProfileDoesNotExistError(ProfileGraphQLError):
    """Profile does not exist"""


class ServiceDoesNotExist(ProfileGraphQLError):
    """Service does not exist"""


class ServiceAlreadyExistsError(ProfileGraphQLError):
    """Service already connected for the user"""


class ServiceConnectionDoesNotExist(ProfileGraphQLError):
    """Service connection does not exist"""


class ServiceNotIdentifiedError(ProfileGraphQLError):
    """The requester failed to identify the service they are coming from"""


class TokenExpiredError(ProfileGraphQLError):
    """Token has expired"""


class TokenExchangeError(Exception):
    """OAuth/OIDC token exchange related exception."""


class InsufficientLoaError(ProfileGraphQLError):
    """The requester has insufficient level of authentication to retrieve this data"""

from graphql import GraphQLError


class ProfileGraphQLError(GraphQLError):
    """GraphQLError that is not sent to Sentry."""


class ServiceAlreadyExistsError(ProfileGraphQLError):
    """Service already connected for the user"""


class CannotDeleteProfileWhileServiceConnectedError(ProfileGraphQLError):
    """Profile cannot be deleted while service is still connected"""


class ProfileDoesNotExistError(ProfileGraphQLError):
    """Profile does not exist"""

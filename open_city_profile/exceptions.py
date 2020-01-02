from graphql import GraphQLError


class ProfileGraphQLError(GraphQLError):
    """GraphQLError that is not sent to Sentry."""


class ServiceAlreadyExistsError(ProfileGraphQLError):
    """Service already connected for the user"""


class TokenExpiredError(ProfileGraphQLError):
    """Token has expired"""

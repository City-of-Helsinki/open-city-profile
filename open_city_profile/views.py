import graphene_validator.errors
import sentry_sdk
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import DataError
from graphene.validation import DisableIntrospection, depth_limit_validator
from graphene_django.views import GraphQLView as BaseGraphQLView
from graphql import ExecutionResult, parse, validate
from helusers.oidc import AuthenticationError

from open_city_profile.consts import (
    CONNECTED_SERVICE_DATA_QUERY_FAILED_ERROR,
    CONNECTED_SERVICE_DELETION_FAILED_ERROR,
    CONNECTED_SERVICE_DELETION_NOT_ALLOWED_ERROR,
    DATA_CONFLICT_ERROR,
    FIELD_NOT_ALLOWED_ERROR,
    GENERAL_ERROR,
    INSUFFICIENT_LOA_ERROR,
    INVALID_EMAIL_FORMAT_ERROR,
    JWT_AUTHENTICATION_ERROR,
    MISSING_GDPR_API_TOKEN_ERROR,
    OBJECT_DOES_NOT_EXIST_ERROR,
    PERMISSION_DENIED_ERROR,
    PROFILE_ALREADY_EXISTS_FOR_USER_ERROR,
    PROFILE_DOES_NOT_EXIST_ERROR,
    PROFILE_MUST_HAVE_PRIMARY_EMAIL,
    SERVICE_CONNECTION_ALREADY_EXISTS_ERROR,
    SERVICE_CONNECTION_DOES_NOT_EXIST_ERROR,
    SERVICE_DOES_NOT_EXIST_ERROR,
    SERVICE_NOT_IDENTIFIED_ERROR,
    TOKEN_EXPIRED_ERROR,
    VALIDATION_ERROR,
)
from open_city_profile.exceptions import (
    ConnectedServiceDataQueryFailedError,
    ConnectedServiceDeletionFailedError,
    ConnectedServiceDeletionNotAllowedError,
    DataConflictError,
    FieldNotAllowedError,
    InsufficientLoaError,
    InvalidEmailFormatError,
    MissingGDPRApiTokenError,
    ProfileAlreadyExistsForUserError,
    ProfileDoesNotExistError,
    ProfileGraphQLError,
    ProfileMustHavePrimaryEmailError,
    ServiceAlreadyExistsError,
    ServiceConnectionDoesNotExistError,
    ServiceDoesNotExistError,
    ServiceNotIdentifiedError,
    TokenExpiredError,
)
from profiles.models import Profile

error_codes_shared = {
    Exception: GENERAL_ERROR,
    ObjectDoesNotExist: OBJECT_DOES_NOT_EXIST_ERROR,
    TokenExpiredError: TOKEN_EXPIRED_ERROR,
    PermissionDenied: PERMISSION_DENIED_ERROR,
    ValidationError: VALIDATION_ERROR,
    graphene_validator.errors.ValidationGraphQLError: VALIDATION_ERROR,
    InvalidEmailFormatError: INVALID_EMAIL_FORMAT_ERROR,
    AuthenticationError: JWT_AUTHENTICATION_ERROR,
    DataConflictError: DATA_CONFLICT_ERROR,
}

error_codes_profile = {
    ConnectedServiceDataQueryFailedError: CONNECTED_SERVICE_DATA_QUERY_FAILED_ERROR,
    ConnectedServiceDeletionFailedError: CONNECTED_SERVICE_DELETION_FAILED_ERROR,
    ConnectedServiceDeletionNotAllowedError: CONNECTED_SERVICE_DELETION_NOT_ALLOWED_ERROR,  # noqa: E501
    ProfileAlreadyExistsForUserError: PROFILE_ALREADY_EXISTS_FOR_USER_ERROR,
    ProfileDoesNotExistError: PROFILE_DOES_NOT_EXIST_ERROR,
    ProfileMustHavePrimaryEmailError: PROFILE_MUST_HAVE_PRIMARY_EMAIL,
    MissingGDPRApiTokenError: MISSING_GDPR_API_TOKEN_ERROR,
    ServiceDoesNotExistError: SERVICE_DOES_NOT_EXIST_ERROR,
    ServiceAlreadyExistsError: SERVICE_CONNECTION_ALREADY_EXISTS_ERROR,
    ServiceConnectionDoesNotExistError: SERVICE_CONNECTION_DOES_NOT_EXIST_ERROR,
    ServiceNotIdentifiedError: SERVICE_NOT_IDENTIFIED_ERROR,
    InsufficientLoaError: INSUFFICIENT_LOA_ERROR,
    FieldNotAllowedError: FIELD_NOT_ALLOWED_ERROR,
}

sentry_ignored_errors = (
    ObjectDoesNotExist,
    PermissionDenied,
    Profile.sensitivedata.RelatedObjectDoesNotExist,
)


error_codes = {**error_codes_shared, **error_codes_profile}


def _get_error_code(exception):
    """Get the most specific error code for the exception via superclass"""
    for exc in exception.mro():
        try:
            return error_codes[exc]
        except KeyError:
            continue


class GraphQLView(BaseGraphQLView):
    def _run_custom_validators(self, query):
        result = None

        validation_rules = [
            depth_limit_validator(max_depth=settings.GRAPHQL_QUERY_DEPTH_LIMIT)
        ]

        if not settings.ENABLE_GRAPHQL_INTROSPECTION:
            validation_rules.append(DisableIntrospection)

        try:
            document = parse(query)
        except Exception:
            # Execution will also fail in super().execute_graphql_request()
            # when parsing the query so no need to do anything here.
            pass
        else:
            validation_errors = validate(
                schema=self.schema.graphql_schema,
                document_ast=document,
                rules=validation_rules,
            )
            if validation_errors:
                result = ExecutionResult(data=None, errors=validation_errors)

        return result

    def execute_graphql_request(self, request, data, query, *args, **kwargs):
        """Extract any exceptions and send some of them to Sentry"""
        result = self._run_custom_validators(query)

        if not result:
            result = super().execute_graphql_request(
                request, data, query, *args, **kwargs
            )

        if result and result.errors:
            errors = [
                e
                for e in result.errors
                if not (
                    isinstance(getattr(e, "original_error", None), ProfileGraphQLError)
                    or isinstance(
                        getattr(e, "original_error", None), sentry_ignored_errors
                    )
                )
            ]
            if errors:
                self._capture_sentry_exceptions(result.errors, query)
        return result

    def _capture_sentry_exceptions(self, errors, query):
        with sentry_sdk.configure_scope() as scope:
            scope.set_extra("graphql_query", query)
            for error in errors:
                if hasattr(error, "original_error"):
                    error = error.original_error
                sentry_sdk.capture_exception(error)

    @staticmethod
    def format_error(error):
        formatted_error = super(GraphQLView, GraphQLView).format_error(error)

        original_error = getattr(error, "original_error", None)
        if isinstance(original_error, DataError):
            formatted_error["message"] = "Invalid data format."

        if isinstance(formatted_error, dict):
            try:
                error_code = _get_error_code(error.original_error.__class__)
            except AttributeError:
                error_code = GENERAL_ERROR

            if error_code:
                if "extensions" not in formatted_error:
                    formatted_error["extensions"] = {}

                if "code" not in formatted_error["extensions"]:
                    formatted_error["extensions"]["code"] = error_code

                    if error_code == FIELD_NOT_ALLOWED_ERROR:
                        formatted_error["extensions"]["field_name"] = getattr(
                            error.original_error, "field_name", ""
                        )

        return formatted_error

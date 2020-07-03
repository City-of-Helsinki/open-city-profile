import sentry_sdk
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from graphene_django.views import GraphQLView as BaseGraphQLView
from graphql_jwt.exceptions import PermissionDenied as JwtPermissionDenied

from open_city_profile.consts import (
    API_NOT_IMPLEMENTED_ERROR,
    CANNOT_PERFORM_THIS_ACTION_WITH_GIVEN_SERVICE_TYPE_ERROR,
    CONNECTED_SERVICE_DELETION_FAILED_ERROR,
    CONNECTED_SERVICE_DELETION_NOT_ALLOWED_ERROR,
    GENERAL_ERROR,
    INVALID_EMAIL_FORMAT_ERROR,
    OBJECT_DOES_NOT_EXIST_ERROR,
    PERMISSION_DENIED_ERROR,
    PROFILE_DOES_NOT_EXIST_ERROR,
    PROFILE_HAS_NO_PRIMARY_EMAIL_ERROR,
    PROFILE_MUST_HAVE_ONE_PRIMARY_EMAIL,
    SERVICE_CONNECTION_ALREADY_EXISTS_ERROR,
    TOKEN_EXPIRED_ERROR,
)
from open_city_profile.exceptions import (
    APINotImplementedError,
    CannotPerformThisActionWithGivenServiceType,
    ConnectedServiceDeletionFailedError,
    ConnectedServiceDeletionNotAllowedError,
    InvalidEmailFormatError,
    ProfileDoesNotExistError,
    ProfileGraphQLError,
    ProfileHasNoPrimaryEmailError,
    ProfileMustHaveOnePrimaryEmail,
    ServiceAlreadyExistsError,
    TokenExpiredError,
)
from profiles.models import Profile
from youths.consts import (
    APPROVER_EMAIL_CANNOT_BE_EMPTY_FOR_MINORS_ERROR,
    CANNOT_CREATE_YOUTH_PROFILE_IF_UNDER_13_YEARS_OLD_ERROR,
    CANNOT_RENEW_YOUTH_PROFILE_ERROR,
    CANNOT_SET_PHOTO_USAGE_PERMISSION_IF_UNDER_15_YEARS_ERROR,
)
from youths.exceptions import (
    ApproverEmailCannotBeEmptyForMinorsError,
    CannotCreateYouthProfileIfUnder13YearsOldError,
    CannotRenewYouthProfileError,
    CannotSetPhotoUsagePermissionIfUnder15YearsError,
)

error_codes_shared = {
    Exception: GENERAL_ERROR,
    ObjectDoesNotExist: OBJECT_DOES_NOT_EXIST_ERROR,
    TokenExpiredError: TOKEN_EXPIRED_ERROR,
    PermissionDenied: PERMISSION_DENIED_ERROR,
    JwtPermissionDenied: PERMISSION_DENIED_ERROR,
    APINotImplementedError: API_NOT_IMPLEMENTED_ERROR,
    CannotPerformThisActionWithGivenServiceType: CANNOT_PERFORM_THIS_ACTION_WITH_GIVEN_SERVICE_TYPE_ERROR,
}
error_codes_profile = {
    ConnectedServiceDeletionFailedError: CONNECTED_SERVICE_DELETION_FAILED_ERROR,
    ConnectedServiceDeletionNotAllowedError: CONNECTED_SERVICE_DELETION_NOT_ALLOWED_ERROR,
    ProfileDoesNotExistError: PROFILE_DOES_NOT_EXIST_ERROR,
    ServiceAlreadyExistsError: SERVICE_CONNECTION_ALREADY_EXISTS_ERROR,
    ProfileHasNoPrimaryEmailError: PROFILE_HAS_NO_PRIMARY_EMAIL_ERROR,
    ProfileMustHaveOnePrimaryEmail: PROFILE_MUST_HAVE_ONE_PRIMARY_EMAIL,
    InvalidEmailFormatError: INVALID_EMAIL_FORMAT_ERROR,
}

error_codes_youth_profile = {
    ApproverEmailCannotBeEmptyForMinorsError: APPROVER_EMAIL_CANNOT_BE_EMPTY_FOR_MINORS_ERROR,
    CannotCreateYouthProfileIfUnder13YearsOldError: CANNOT_CREATE_YOUTH_PROFILE_IF_UNDER_13_YEARS_OLD_ERROR,
    CannotRenewYouthProfileError: CANNOT_RENEW_YOUTH_PROFILE_ERROR,
    CannotSetPhotoUsagePermissionIfUnder15YearsError: CANNOT_SET_PHOTO_USAGE_PERMISSION_IF_UNDER_15_YEARS_ERROR,
}

sentry_ignored_errors = (
    ObjectDoesNotExist,
    JwtPermissionDenied,
    PermissionDenied,
    Profile.sensitivedata.RelatedObjectDoesNotExist,
)


error_codes = {**error_codes_shared, **error_codes_profile, **error_codes_youth_profile}


class GraphQLView(BaseGraphQLView):
    def execute_graphql_request(self, request, data, query, *args, **kwargs):
        """Extract any exceptions and send some of them to Sentry"""
        result = super().execute_graphql_request(request, data, query, *args, **kwargs)
        # If 'invalid' is set, it's a bad request
        if result and result.errors and not result.invalid:
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
        def get_error_code(exception):
            """Get the most specific error code for the exception via superclass"""
            for exception in exception.mro():
                try:
                    return error_codes[exception]
                except KeyError:
                    continue

        try:
            error_code = get_error_code(error.original_error.__class__)
        except AttributeError:
            error_code = GENERAL_ERROR
        formatted_error = super(GraphQLView, GraphQLView).format_error(error)
        if error_code and (
            isinstance(formatted_error, dict)
            and not (
                "extensions" in formatted_error
                and "code" in formatted_error["extensions"]
            )
        ):
            formatted_error["extensions"] = {"code": error_code}
        return formatted_error

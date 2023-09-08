import logging
from dataclasses import dataclass
from json import JSONDecodeError
from typing import List

import requests

from open_city_profile.consts import (
    SERVICE_GDPR_API_REQUEST_ERROR,
    SERVICE_GDPR_API_UNKNOWN_ERROR,
)
from open_city_profile.exceptions import (
    ConnectedServiceDataQueryFailedError,
    ConnectedServiceDeletionNotAllowedError,
    MissingGDPRApiTokenError,
)
from open_city_profile.oidc import KeycloakTokenExchange, TunnistamoTokenExchange
from services.enums import ServiceIdp
from services.models import Service
from utils.auth import BearerAuth

logger = logging.getLogger(__name__)


def _check_service_gdpr_query_configuration(service_connections):
    for service_connection in service_connections:
        service = service_connection.service

        if not service_connection.get_gdpr_url() or not service.gdpr_query_scope:
            logger.error(
                "GDPR URL or GDPR query scope missing for service %s", service.name
            )
            raise ConnectedServiceDataQueryFailedError(
                f"Connected service: {service.name} does not have an API for querying data."
            )

        if (
            service.idp
            and ServiceIdp.KEYCLOAK in service.idp
            and not service.gdpr_audience
        ):
            logger.error("GDPR audience missing for service %s", service.name)
            raise ConnectedServiceDataQueryFailedError(
                f'Connected service: Keycloak connected service "{service.name}" does not have GDPR audience set'
            )


def _any_tunnistamo_connected_services(service_connections):
    return any([not sc.service.is_pure_keycloak for sc in service_connections])


def _any_pure_keycloak_connected_services(service_connections):
    return any([sc.service.is_pure_keycloak for sc in service_connections])


def _get_api_token(service, scope, api_tokens, keycloak_token_exchange):
    api_token = ""
    if not service.is_pure_keycloak:
        api_identifier = scope.rsplit(".", 1)[0]
        api_token = api_tokens.get(api_identifier, "")

    if not api_token and service.idp and ServiceIdp.KEYCLOAK in service.idp:
        logger.debug("Fetch Keycloak API Token for service %s", service.name)
        api_token = keycloak_token_exchange.fetch_api_token(
            service.gdpr_audience, scope
        )
        logger.debug("Keycloak API Token: %s", api_token)

    return api_token


def download_connected_service_data(
    profile, authorization_code, authorization_code_keycloak
):
    service_connections = profile.effective_service_connections_qs().all()
    if not service_connections:
        logger.debug("No service connections for profile %s (query)", profile.id)
        return []

    _check_service_gdpr_query_configuration(service_connections)

    logger.debug("Downloading connected service data for profile %s", profile.id)

    api_tokens = {}
    if _any_tunnistamo_connected_services(service_connections):
        tte = TunnistamoTokenExchange()
        api_tokens = tte.fetch_api_tokens(authorization_code)
        logger.debug("Tunnistamo API Tokens for query: %s", api_tokens)

    keycloak_token_exchange = None
    if _any_pure_keycloak_connected_services(service_connections):
        logger.debug("Pure Keycloak services exist. Fetch Keycloak access token.")
        keycloak_token_exchange = KeycloakTokenExchange()
        keycloak_token_exchange.fetch_access_token(authorization_code_keycloak)

    external_data = []

    for service_connection in service_connections:
        service = service_connection.service
        logger.debug("Starting GDPR query for service %s", service.name)

        api_token = _get_api_token(
            service, service.gdpr_query_scope, api_tokens, keycloak_token_exchange
        )
        if not api_token:
            logger.error(
                "API Token missing for service %s in query (profile %s)",
                service.name,
                profile.id,
            )
            raise MissingGDPRApiTokenError(
                f"Couldn't fetch an API token for service {service.name}."
            )

        try:
            url = service_connection.get_gdpr_url()
            logger.debug("GDPR URL: %s", url)
            response = requests.get(url, auth=BearerAuth(api_token), timeout=5)
            logger.debug(
                "GDPR query response for profile %s to service %s status code: %s, headers: %s, body: %s",
                profile.id,
                service.name,
                response.status_code,
                response.headers,
                response.text,
            )
            response.raise_for_status()

            if response.status_code == 200:
                service_connection_data = response.json()
            else:
                service_connection_data = {}
        except requests.RequestException as e:
            logger.error(
                "Invalid GDPR query response for profile %s from service %s. Exception: %s.",
                profile.id,
                service.name,
                e,
            )
            raise ConnectedServiceDataQueryFailedError(
                f"Invalid response from service {service.name}"
            )

        if service_connection_data:
            external_data.append(service_connection_data)

    return external_data


@dataclass
class DeleteGdprDataErrorMessage:
    lang: str
    text: str


@dataclass
class DeleteGdprDataError:
    code: str
    message: List[DeleteGdprDataErrorMessage]


@dataclass
class DeleteGdprDataResult:
    service: Service
    dry_run: bool
    success: bool
    errors: List[DeleteGdprDataError]


def _validate_gdpr_api_errors(errors):
    try:
        iter(errors)
    except TypeError:
        return False

    expected_keys = {"code", "message"}
    for error in errors:
        if set(error.keys()) != expected_keys:
            return False
        if not error.get("code") or not isinstance(error["code"], str):
            return False
        if not error.get("message") or not isinstance(error["message"], dict):
            return False

        for key, value in error["message"].items():
            if not key or not isinstance(value, str):
                return False

    return True


def _convert_gdpr_api_errors(errors) -> List[DeleteGdprDataError]:
    """Converts errors from the GDPR API to a list of DeleteGdprDataErrors"""
    converted_errors = []
    for error in errors:
        converted_error = DeleteGdprDataError(code=error["code"], message=[])
        for lang, text in error["message"].items():
            converted_error.message.append(
                DeleteGdprDataErrorMessage(lang=lang, text=text)
            )
        converted_errors.append(converted_error)

    return converted_errors


def _add_error_to_result(result, code, message):
    result.errors.append(
        DeleteGdprDataError(
            code=code, message=[DeleteGdprDataErrorMessage(lang="en", text=message)]
        )
    )

    return result


def _delete_service_data(
    service_connection, api_token: str, dry_run=False
) -> DeleteGdprDataResult:
    """Delete service specific GDPR data by profile.

    API token needs to be for a user that can access information for the related
    profile on the related GDPR API.

    Dry run parameter can be used for asking the service if delete is possible.

    The errors content from the service is returned if the service provides a JSON
    response with an "errors" key containing valid error content.
    """
    service = service_connection.service

    result = DeleteGdprDataResult(
        service=service, dry_run=dry_run, success=False, errors=[]
    )

    url = service_connection.get_gdpr_url()

    data = {}
    if dry_run:
        data["dry_run"] = "true"

    try:
        response = requests.delete(
            url, auth=BearerAuth(api_token), timeout=5, params=data
        )
        logger.debug(
            "GDPR delete (dry run: %s) response for profile %s to service %s status code: %s, headers: %s, body: %s",
            dry_run,
            service_connection.profile.id,
            service.name,
            response.status_code,
            response.headers,
            response.text,
        )
    except requests.RequestException as e:
        logger.error(
            "GDPR delete request (dry run: %s) failed for profile %s to service %s. Exception: %s.",
            dry_run,
            service_connection.profile.id,
            service.name,
            e,
        )
        return _add_error_to_result(
            result,
            SERVICE_GDPR_API_REQUEST_ERROR,
            "Error when making a request to the GDPR URL of the service",
        )

    if response.status_code == 204:
        logger.debug(
            "GDPR delete request (dry run: %s) for profile %s to service %s successful",
            dry_run,
            service_connection.profile.id,
            service.name,
        )
        result.success = True
        return result

    if response.status_code in [403, 500]:
        try:
            errors_from_the_service = response.json().get("errors")
            if _validate_gdpr_api_errors(errors_from_the_service):
                logger.debug(
                    "GDPR delete request (dry run: %s) for profile %s to service %s denied with reasons %s",
                    dry_run,
                    service_connection.profile.id,
                    service.name,
                    errors_from_the_service,
                )
                result.errors = _convert_gdpr_api_errors(errors_from_the_service)
                return result
            else:
                logger.warning(
                    "Badly formatted delete response from service %s (profile %s): '%s'",
                    service.name,
                    service_connection.profile.id,
                    response.text,
                )
        except JSONDecodeError:
            logger.debug(
                "Couldn't parse GDPR delete response (status: %s) from service %s as JSON (profile %s). Body '%s'.",
                response.status_code,
                service.name,
                service_connection.profile.id,
                response.text,
            )
    else:
        logger.warning(
            "Unexpected status code %s for GDPR delete request to service %s (profile %s)",
            response.status_code,
            service.name,
            service_connection.profile.id,
        )

    return _add_error_to_result(
        result,
        SERVICE_GDPR_API_UNKNOWN_ERROR,
        "Unknown error occurred when trying to remove data from the service",
    )


def _delete_service_connection_and_service_data(
    service_connections, api_tokens, keycloak_token_exchange, dry_run=False
):
    results = []

    for service_connection in service_connections:
        service = service_connection.service
        api_token = _get_api_token(
            service, service.gdpr_delete_scope, api_tokens, keycloak_token_exchange
        )
        result = _delete_service_data(service_connection, api_token, dry_run=dry_run)
        if result.success and not dry_run:
            service_connection.delete()

        results.append(result)

    return results


def _check_service_gdpr_delete_configuration(service_connections, api_tokens, profile):
    failed_services = []

    for service_connection in service_connections:
        service = service_connection.service

        if not service.gdpr_delete_scope:
            logger.error("GDPR delete scope missing for service %s", service.name)
            raise ConnectedServiceDeletionNotAllowedError(
                f"Connected services: {service.name} does not have an API for removing data."
            )

        if not service.is_pure_keycloak:
            api_identifier = service.gdpr_delete_scope.rsplit(".", 1)[0]
            api_token = api_tokens.get(api_identifier, "")

            if not api_token:
                logger.error(
                    "API Token missing for service %s in delete (profile %s)",
                    service.name,
                    profile.id,
                )
                raise MissingGDPRApiTokenError(
                    f"Couldn't fetch an API token for service {service.name}."
                )

        if not service_connection.get_gdpr_url():
            logger.error(
                "GDPR URL missing for service %s in delete (profile %s)",
                service.name,
                profile.id,
            )
            failed_services.append(service.name)

    if failed_services:
        failed_services_string = ", ".join(failed_services)
        raise ConnectedServiceDeletionNotAllowedError(
            f"Connected services: {failed_services_string} did not allow deleting the profile."
        )


def delete_connected_service_data(
    profile,
    authorization_code,
    authorization_code_keycloak,
    service_connections=None,
    dry_run=False,
):
    if service_connections is None:
        service_connections = profile.effective_service_connections_qs().all()

    if not service_connections:
        logger.debug("No service connections for profile %s (delete)", profile.id)
        return []

    logger.debug("Deleting connected service data for profile %s", profile.id)

    api_tokens = {}
    if _any_tunnistamo_connected_services(service_connections):
        tte = TunnistamoTokenExchange()
        api_tokens = tte.fetch_api_tokens(authorization_code)
        logger.debug("Tunnistamo API Tokens for delete: %s", api_tokens)

    keycloak_token_exchange = None
    if _any_pure_keycloak_connected_services(service_connections):
        logger.debug("Pure Keycloak services exist. Fetch Keycloak access token.")
        keycloak_token_exchange = KeycloakTokenExchange()
        keycloak_token_exchange.fetch_access_token(authorization_code_keycloak)

    _check_service_gdpr_delete_configuration(service_connections, api_tokens, profile)

    results = _delete_service_connection_and_service_data(
        service_connections, api_tokens, keycloak_token_exchange, dry_run=True
    )
    if dry_run or any([len(r.errors) for r in results]):
        return results

    if not dry_run:
        results = _delete_service_connection_and_service_data(
            service_connections, api_tokens, keycloak_token_exchange, dry_run=False
        )
        return results

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
from open_city_profile.oidc import TunnistamoTokenExchange
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


def download_connected_service_data(profile, authorization_code):
    service_connections = profile.effective_service_connections_qs().all()
    if not service_connections:
        logger.debug("No service connections for profile %s", profile.id)
        return []

    _check_service_gdpr_query_configuration(service_connections)

    logger.debug("Downloading connected service data for profile %s", profile.id)

    tte = TunnistamoTokenExchange()
    api_tokens = tte.fetch_api_tokens(authorization_code)
    logger.debug("API Tokens: %s", api_tokens)

    external_data = []

    for service_connection in service_connections:
        service = service_connection.service
        logger.debug("Starting GDPR query for service %s", service.name)

        api_identifier = service.gdpr_query_scope.rsplit(".", 1)[0]
        api_token = api_tokens.get(api_identifier, "")

        if not api_token:
            logger.error(
                "API Token missing for service %s (profile %s)",
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
                "Response status code: %s, headers: %s, body: %s",
                response.status_code,
                response.headers,
                response.text,
            )
            response.raise_for_status()
            service_connection_data = response.json()
        except requests.RequestException as e:
            logger.error(
                "Invalid response for profile %s from service %s. Exception: %s.",
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
    result = DeleteGdprDataResult(
        service=service_connection.service, dry_run=dry_run, success=False, errors=[],
    )

    url = service_connection.get_gdpr_url()

    data = {}
    if dry_run:
        data["dry_run"] = "true"

    try:
        response = requests.delete(
            url, auth=BearerAuth(api_token), timeout=5, params=data
        )
    except requests.RequestException:
        return _add_error_to_result(
            result,
            SERVICE_GDPR_API_REQUEST_ERROR,
            "Error when making a request to the GDPR URL of the service",
        )

    if response.status_code == 204:
        result.success = True
        return result

    if response.status_code in [403, 500]:
        try:
            errors_from_the_service = response.json().get("errors")
            if _validate_gdpr_api_errors(errors_from_the_service):
                result.errors = _convert_gdpr_api_errors(errors_from_the_service)
                return result
        except JSONDecodeError:
            pass

    return _add_error_to_result(
        result,
        SERVICE_GDPR_API_UNKNOWN_ERROR,
        "Unknown error occurred when trying to remove data from the service",
    )


def _delete_service_connection_and_service_data(
    service_connections, api_tokens, dry_run=False
):
    results = []

    for service_connection in service_connections:
        service = service_connection.service
        api_identifier = service.gdpr_delete_scope.rsplit(".", 1)[0]
        api_token = api_tokens.get(api_identifier, "")

        result = _delete_service_data(service_connection, api_token, dry_run=dry_run)
        if result.success and not dry_run:
            service_connection.delete()

        results.append(result)

    return results


def _check_service_gdpr_delete_configuration(service_connections, api_tokens):
    failed_services = []

    for service_connection in service_connections:
        service = service_connection.service

        if not service.gdpr_delete_scope:
            raise ConnectedServiceDeletionNotAllowedError(
                f"Connected services: {service.name}"
                f"does not have an API for removing data."
            )

        api_identifier = service.gdpr_delete_scope.rsplit(".", 1)[0]
        api_token = api_tokens.get(api_identifier, "")

        if not api_token:
            raise MissingGDPRApiTokenError(
                f"Couldn't fetch an API token for service {service.name}."
            )

        if not service_connection.get_gdpr_url():
            failed_services.append(service.name)

    if failed_services:
        failed_services_string = ", ".join(failed_services)
        raise ConnectedServiceDeletionNotAllowedError(
            f"Connected services: {failed_services_string} did not allow deleting the profile."
        )


def delete_connected_service_data(
    profile, authorization_code, service_connections=None, dry_run=False
):
    if service_connections is None:
        service_connections = profile.effective_service_connections_qs().all()

    if not service_connections:
        return []

    tte = TunnistamoTokenExchange()
    api_tokens = tte.fetch_api_tokens(authorization_code)

    _check_service_gdpr_delete_configuration(service_connections, api_tokens)

    results = _delete_service_connection_and_service_data(
        service_connections, api_tokens, dry_run=True
    )
    if dry_run or any([len(r.errors) for r in results]):
        return results

    if not dry_run:
        results = _delete_service_connection_and_service_data(
            service_connections, api_tokens, dry_run=False
        )
        return results

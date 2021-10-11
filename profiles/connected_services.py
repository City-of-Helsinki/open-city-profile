import requests

from open_city_profile.exceptions import (
    ConnectedServiceDeletionFailedError,
    ConnectedServiceDeletionNotAllowedError,
    MissingGDPRApiTokenError,
)
from open_city_profile.oidc import TunnistamoTokenExchange
from services.exceptions import MissingGDPRUrlException


def download_connected_service_data(profile, authorization_code):
    external_data = []

    if profile.service_connections.exists():
        tte = TunnistamoTokenExchange()
        api_tokens = tte.fetch_api_tokens(authorization_code)

        for service_connection in profile.service_connections.all():
            service = service_connection.service

            if not service.gdpr_query_scope:
                continue

            api_identifier = service.gdpr_query_scope.rsplit(".", 1)[0]
            api_token = api_tokens.get(api_identifier, "")

            if not api_token:
                raise MissingGDPRApiTokenError(
                    f"Couldn't fetch an API token for service {service.name}."
                )

            service_connection_data = service_connection.download_gdpr_data(
                api_token=api_token
            )

            if service_connection_data:
                external_data.append(service_connection_data)

    return external_data


def _delete_service_connections_for_profile(profile, api_tokens, dry_run=False):
    failed_services = []

    for service_connection in profile.service_connections.all():
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

        try:
            service_connection.delete_gdpr_data(api_token=api_token, dry_run=dry_run)
            if not dry_run:
                service_connection.delete()
        except (requests.RequestException, MissingGDPRUrlException):
            failed_services.append(service.name)

    if failed_services:
        failed_services_string = ", ".join(failed_services)
        if dry_run:
            raise ConnectedServiceDeletionNotAllowedError(
                f"Connected services: {failed_services_string} did not allow deleting the profile."
            )

        raise ConnectedServiceDeletionFailedError(
            f"Deletion failed for the following connected services: {failed_services_string}."
        )


def delete_connected_service_data(profile, authorization_code):
    if profile.service_connections.exists():
        tte = TunnistamoTokenExchange()
        api_tokens = tte.fetch_api_tokens(authorization_code)

        _delete_service_connections_for_profile(profile, api_tokens, dry_run=True)
        _delete_service_connections_for_profile(profile, api_tokens, dry_run=False)

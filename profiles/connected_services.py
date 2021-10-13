import requests
from django.conf import settings
from django.core.signals import setting_changed
from django.dispatch import receiver

from open_city_profile.exceptions import (
    ConnectedServiceDeletionFailedError,
    ConnectedServiceDeletionNotAllowedError,
    MissingGDPRApiTokenError,
)
from open_city_profile.oidc import TunnistamoTokenExchange
from services.exceptions import MissingGDPRUrlException
from utils.keycloak import KeycloakAdminClient

_keycloak_admin_client = None


def _setup_keycloak_client():
    global _keycloak_admin_client

    if (
        settings.KEYCLOAK_BASE_URL
        and settings.KEYCLOAK_REALM
        and settings.KEYCLOAK_CLIENT_ID
        and settings.KEYCLOAK_CLIENT_SECRET
    ):
        _keycloak_admin_client = KeycloakAdminClient(
            settings.KEYCLOAK_BASE_URL,
            settings.KEYCLOAK_REALM,
            settings.KEYCLOAK_CLIENT_ID,
            settings.KEYCLOAK_CLIENT_SECRET,
        )
    else:
        _keycloak_admin_client = None


_setup_keycloak_client()


@receiver(setting_changed)
def _reload_settings(setting, **kwargs):
    if setting in [
        "KEYCLOAK_BASE_URL",
        "KEYCLOAK_REALM",
        "KEYCLOAK_CLIENT_ID",
        "KEYCLOAK_CLIENT_SECRET",
    ]:
        _setup_keycloak_client()


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

    if _keycloak_admin_client and profile.user:
        user_id = profile.user.uuid

        try:
            _keycloak_admin_client.delete_user(user_id)
        except Exception as err:
            if (
                not isinstance(err, requests.HTTPError)
                or err.response.status_code != 404
            ):
                raise ConnectedServiceDeletionFailedError("User deletion unsuccesful.")


def send_profile_changes_to_keycloak(instance):
    if not instance.user or _keycloak_admin_client is None:
        return

    user_id = instance.user.uuid

    try:
        user_data = _keycloak_admin_client.get_user(user_id)
    except requests.HTTPError as err:
        if err.response.status_code == 404:
            return
        raise

    current_kc_data = {
        "firstName": user_data.get("firstName"),
        "lastName": user_data.get("lastName"),
        "email": user_data.get("email"),
    }

    updated_data = {
        "firstName": instance.first_name,
        "lastName": instance.last_name,
        "email": instance.get_primary_email_value(),
    }

    if current_kc_data == updated_data:
        return

    email_changed = current_kc_data["email"] != updated_data["email"]

    if email_changed:
        updated_data["emailVerified"] = False

    _keycloak_admin_client.update_user(user_id, updated_data)

    if email_changed:
        try:
            _keycloak_admin_client.send_verify_email(user_id)
        except Exception:
            pass

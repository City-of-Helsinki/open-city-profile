import requests
from django.conf import settings
from django.core.signals import setting_changed
from django.dispatch import receiver

from open_city_profile.exceptions import (
    ConnectedServiceDataQueryFailedError,
    ConnectedServiceDeletionFailedError,
    ConnectedServiceDeletionNotAllowedError,
    MissingGDPRApiTokenError,
)
from open_city_profile.oidc import TunnistamoTokenExchange
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


def _check_service_gdpr_query_configuration(service_connections):
    for service_connection in service_connections:
        service = service_connection.service

        if not service.gdpr_query_scope:
            raise ConnectedServiceDataQueryFailedError(
                f"Connected service: {service.name} does not have an API for querying data."
            )


def download_connected_service_data(profile, authorization_code):
    external_data = []

    service_connections = profile.effective_service_connections_qs().all()

    _check_service_gdpr_query_configuration(service_connections)

    if service_connections:
        tte = TunnistamoTokenExchange()
        api_tokens = tte.fetch_api_tokens(authorization_code)

        for service_connection in service_connections:
            service = service_connection.service

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


def _delete_service_connection_and_service_data(
    service_connections, api_tokens, dry_run=False
):
    results = []

    for service_connection in service_connections:
        service = service_connection.service
        api_identifier = service.gdpr_delete_scope.rsplit(".", 1)[0]
        api_token = api_tokens.get(api_identifier, "")

        result = service_connection.delete_gdpr_data(
            api_token=api_token, dry_run=dry_run
        )
        if result.success and not dry_run:
            service_connection.delete()

        results.append(result)

    return results


def _check_service_gdpr_delete_configuration(profile, service_connections, api_tokens):
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

        if not service.get_gdpr_url_for_profile(profile):
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

    _check_service_gdpr_delete_configuration(profile, service_connections, api_tokens)

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


def delete_profile_from_keycloak(profile):
    if not _keycloak_admin_client or not profile.user:
        return

    user_id = profile.user.uuid

    try:
        _keycloak_admin_client.delete_user(user_id)
    except Exception as err:
        if not isinstance(err, requests.HTTPError) or err.response.status_code != 404:
            raise ConnectedServiceDeletionFailedError("User deletion unsuccessful.")


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

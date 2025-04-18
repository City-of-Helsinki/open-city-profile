import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import cached_property
from oauthlib.oauth2 import OAuth2Error
from requests_oauthlib import OAuth2Session

from open_city_profile.exceptions import TokenExchangeError


class KeycloakTokenExchange:
    timeout = 5

    def __init__(self):
        self.check_settings()

        self.keycloak_base_url = settings.KEYCLOAK_BASE_URL
        self.keycloak_realm = settings.KEYCLOAK_REALM
        self.client_id = settings.KEYCLOAK_GDPR_CLIENT_ID
        self.client_secret = settings.KEYCLOAK_GDPR_CLIENT_SECRET
        self.callback_url = settings.GDPR_AUTH_CALLBACK_URL

        self.access_token = None

    @staticmethod
    def check_settings():
        if not (
            settings.KEYCLOAK_BASE_URL
            and settings.KEYCLOAK_REALM
            and settings.KEYCLOAK_GDPR_CLIENT_ID
            and settings.KEYCLOAK_GDPR_CLIENT_SECRET
        ):
            raise ImproperlyConfigured(
                "Required Keycloak OAuth/OIDC configuration is not set."
            )

        if not settings.GDPR_AUTH_CALLBACK_URL:
            raise ImproperlyConfigured(
                "Required GDPR API auth callback URL configuration is not set."
            )

    def fetch_access_token(self, authorization_code: str) -> dict:
        session = OAuth2Session(
            client_id=self.client_id, redirect_uri=self.callback_url
        )

        try:
            response = session.fetch_token(
                token_url=self.oidc_config["token_endpoint"],
                code=authorization_code,
                client_secret=self.client_secret,
                include_client_id=True,
                timeout=self.timeout,
            )
            self.access_token = response.get("access_token")
        except OAuth2Error as exc:
            raise TokenExchangeError("Failed to obtain an access token.") from exc

        return self.access_token

    def fetch_api_token(self, target_aud, permission):
        headers = {"Authorization": "Bearer {}".format(self.access_token)}
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:uma-ticket",
            "audience": target_aud,
            "permission": "#{}".format(permission),
        }
        response = requests.post(
            self.oidc_config["token_endpoint"],
            headers=headers,
            timeout=self.timeout,
            data=data,
        )
        response.raise_for_status()
        response_data = response.json()

        return response_data.get("access_token")

    @cached_property
    def oidc_config(self):
        well_known_url = f"{self.keycloak_base_url}/realms/{self.keycloak_realm}/.well-known/openid-configuration"  # noqa: E501

        return self.get(well_known_url).json()

    def get(self, url: str) -> requests.Response:
        headers = {"accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response

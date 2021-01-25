import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from helusers.oidc import ApiTokenAuthentication
from oauthlib.oauth2 import OAuth2Error
from requests_oauthlib import OAuth2Session

from open_city_profile.exceptions import TokenExchangeError


class GraphQLApiTokenAuthentication(ApiTokenAuthentication):
    """
    Custom wrapper for the helusers.oidc.ApiTokenAuthentication backend.
    Needed to make it work with graphql_jwt.middleware.JSONWebTokenMiddleware,
    which in turn calls django.contrib.auth.middleware.AuthenticationMiddleware.

    Authenticate function should:
    1. accept kwargs, or django's auth middleware will not call it
    2. return only the user object, or django's auth middleware will fail
    """

    def authenticate(self, request, **kwargs):
        user_auth_tuple = super().authenticate(request)
        if not user_auth_tuple:
            return None
        user, auth = user_auth_tuple
        request.user_auth = auth
        return user


class TunnistamoTokenExchange:
    """Exchanges an authorization code with Tunnistamo into API token for open-city-profile."""

    timeout = 5

    def __init__(self):
        self.check_settings()

        self.oidc_endpoint = settings.TUNNISTAMO_OIDC_ENDPOINT
        self.client_id = settings.TUNNISTAMO_CLIENT_ID
        self.client_secret = settings.TUNNISTAMO_CLIENT_SECRET
        self.callback_url = settings.GDPR_AUTH_CALLBACK_URL
        self.api_tokens_url = settings.TUNNISTAMO_API_TOKENS_URL

    @staticmethod
    def check_settings():
        if not (
            settings.TUNNISTAMO_OIDC_ENDPOINT
            and settings.TUNNISTAMO_CLIENT_ID
            and settings.TUNNISTAMO_CLIENT_SECRET
            and settings.TUNNISTAMO_API_TOKENS_URL
        ):
            raise ImproperlyConfigured(
                "Required Tunnistamo OAuth/OIDC configuration is not set."
            )

        if not settings.GDPR_AUTH_CALLBACK_URL:
            raise ImproperlyConfigured(
                "Required GDPR API auth callback URL configuration is not set."
            )

    def fetch_api_tokens(self, authorization_code: str) -> dict:
        """Exchanges the authorization code into API tokens that can access APIs using Tunnistamo."""
        oidc_conf = self.get_oidc_config()
        session = OAuth2Session(
            client_id=self.client_id, redirect_uri=self.callback_url
        )

        try:
            session.fetch_token(
                token_url=oidc_conf["token_endpoint"],
                code=authorization_code,
                client_secret=self.client_secret,
                include_client_id=True,
                timeout=self.timeout,
            )
        except OAuth2Error as exc:
            raise TokenExchangeError("Failed to obtain an access token.") from exc

        response = session.get(self.api_tokens_url, timeout=self.timeout)
        response.raise_for_status()

        api_tokens = response.json()

        return api_tokens

    def get_oidc_config(self):
        return self.get(self.oidc_endpoint + "/.well-known/openid-configuration").json()

    def get(self, url: str) -> requests.Response:
        headers = {"accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response

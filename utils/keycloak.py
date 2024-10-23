import requests
from django.utils.functional import cached_property

from utils.auth import BearerAuth


class KeycloakError(RuntimeError):
    """Base class for Keycloak errors."""


class CommunicationError(KeycloakError):
    """Communication with Keycloak server failed."""


class AuthenticationError(KeycloakError):
    """Failed authentication with Keycloak."""


class UserNotFoundError(KeycloakError):
    """User is not found from Keycloak."""


class ConflictError(KeycloakError):
    """A conflict occured in Keycloak."""


def _validate_users_response(response):
    if response.status_code == 404:
        raise UserNotFoundError("User not found in Keycloak")

    if response.status_code == 409:
        raise ConflictError("Keycloak reported a conflict")

    if not response.ok:
        raise CommunicationError(
            f"Failed communicating with Keycloak (status code {response.status_code})"
        )


class KeycloakAdminClient:
    def __init__(self, server_url, realm_name, client_id, client_secret):
        self._server_url = server_url
        self._realm_name = realm_name
        self._client_id = client_id
        self._client_secret = client_secret

        self._session = requests.Session()
        self._auth = None
        self._timeout = 10

    def _handle_request_common_errors(self, requester):
        try:
            result = requester()
        except requests.RequestException as err:
            raise CommunicationError("Failed communicating with Keycloak") from err

        if 500 <= result.status_code < 600:
            raise CommunicationError(
                f"Failed communicating with Keycloak (status code {result.status_code})"
            )

        return result

    @cached_property
    def _well_known(self):
        well_known_url = f"{self._server_url}/realms/{self._realm_name}/.well-known/openid-configuration"  # noqa: E501

        result = self._handle_request_common_errors(
            lambda: self._session.get(well_known_url, timeout=self._timeout)
        )

        if not result.ok:
            raise AuthenticationError("Couldn't get OpenID configuration")

        return result.json()

    def _get_auth(self, force_renew=False):
        if force_renew:
            self._auth = None

        if not self._auth:
            token_endpoint_url = self._well_known["token_endpoint"]
            credentials_request = {
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            }

            result = self._handle_request_common_errors(
                lambda: self._session.post(
                    token_endpoint_url, data=credentials_request, timeout=self._timeout
                )
            )

            if not result.ok:
                raise AuthenticationError("Couldn't authenticate to Keycloak")

            client_credentials = result.json()
            access_token = client_credentials["access_token"]

            self._auth = BearerAuth(access_token)

        return self._auth

    def _single_user_url(self, user_id, action: str = ""):
        if action and not action.startswith("/"):
            action = f"/{action}"
        return f"{self._server_url}/admin/realms/{self._realm_name}/users/{user_id}{action}"  # noqa: E501

    def _handle_request_with_auth(self, requester):
        def reauth_requester():
            response = requester(self._get_auth())
            if response.status_code == 401:
                response = requester(self._get_auth(force_renew=True))
            return response

        return self._handle_request_common_errors(reauth_requester)

    def request(self, method, url, validator, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", self._timeout)

        response = self._handle_request_with_auth(
            lambda auth: self._session.request(method, url, auth=auth, **kwargs)
        )

        if validator:
            validator(response)

        return response

    def get(self, url, *args, **kwargs) -> requests.Response:
        return self.request("GET", url, *args, **kwargs)

    def put(self, url, *args, **kwargs) -> requests.Response:
        return self.request("PUT", url, *args, **kwargs)

    def delete(self, url, *args, **kwargs) -> requests.Response:
        return self.request("DELETE", url, *args, **kwargs)

    def get_user(self, user_id):
        response = self.get(
            self._single_user_url(user_id), validator=_validate_users_response
        )
        return response.json()

    def update_user(self, user_id, update_data: dict):
        self.put(
            self._single_user_url(user_id),
            validator=_validate_users_response,
            json=update_data,
        )

    def delete_user(self, user_id):
        self.delete(self._single_user_url(user_id), validator=_validate_users_response)

    def send_verify_email(self, user_id):
        url = self._single_user_url(user_id, "send-verify-email")
        return self.put(
            url,
            params={"client_id": self._client_id},
            validator=_validate_users_response,
        )

    def get_user_federated_identities(self, user_id):
        url = self._single_user_url(user_id, "federated-identity")
        response = self.get(url, validator=_validate_users_response)
        return response.json()

    def get_user_credentials(self, user_id):
        url = self._single_user_url(user_id, "credentials")
        response = self.get(url, validator=_validate_users_response)
        return response.json()

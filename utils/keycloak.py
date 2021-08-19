import requests
from django.utils.functional import cached_property

from utils.auth import BearerAuth


class KeycloakAdminClient:
    def __init__(self, server_url, realm_name, client_id, client_secret):
        self._server_url = server_url
        self._realm_name = realm_name
        self._client_id = client_id
        self._client_secret = client_secret

        self._session = requests.Session()
        self._auth = None

    @cached_property
    def _well_known(self):
        well_known_url = f"{self._server_url}/auth/realms/{self._realm_name}/.well-known/openid-configuration"

        result = self._session.get(well_known_url)
        result.raise_for_status()
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
            result = self._session.post(token_endpoint_url, data=credentials_request)
            result.raise_for_status()
            client_credentials = result.json()
            access_token = client_credentials["access_token"]

            self._auth = BearerAuth(access_token)

        return self._auth

    def _single_user_url(self, user_id):
        return (
            f"{self._server_url}/auth/admin/realms/{self._realm_name}/users/{user_id}"
        )

    def _handle_request_with_auth(self, requester):
        response = requester(self._get_auth())
        if response.status_code == 401:
            response = requester(self._get_auth(force_renew=True))
        response.raise_for_status()
        return response

    def get_user(self, user_id):
        url = self._single_user_url(user_id)

        response = self._handle_request_with_auth(
            lambda auth: self._session.get(url, auth=auth)
        )
        return response.json()

    def update_user(self, user_id, update_data: dict):
        url = self._single_user_url(user_id)

        self._handle_request_with_auth(
            lambda auth: self._session.put(url, auth=auth, json=update_data)
        )

    def send_verify_email(self, user_id):
        url = self._single_user_url(user_id)
        url += f"/send-verify-email"
        return self._session.put(
            url, auth=self._get_auth(), params={"client_id": self._client_id}
        )

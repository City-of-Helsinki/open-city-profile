import requests

from utils.auth import BearerAuth


class KeycloakAdminClient:
    def __init__(self, server_url, realm_name, client_id, client_secret):
        self._server_url = server_url
        self._realm_name = realm_name
        self._client_id = client_id
        self._client_secret = client_secret

        self._session = requests.Session()

    def _get_auth(self):
        well_known_url = f"{self._server_url}/auth/realms/{self._realm_name}/.well-known/openid-configuration"
        well_known = self._session.get(well_known_url).json()

        token_endpoint_url = well_known["token_endpoint"]
        credentials_request = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        client_credentials = self._session.post(
            token_endpoint_url, data=credentials_request
        ).json()
        access_token = client_credentials["access_token"]

        return BearerAuth(access_token)

    def _single_user_url(self, user_id):
        return (
            f"{self._server_url}/auth/admin/realms/{self._realm_name}/users/{user_id}"
        )

    def get_user(self, user_id):
        url = self._single_user_url(user_id)
        auth = self._get_auth()

        return self._session.get(url, auth=auth).json()

    def update_user(self, user_id, update_data: dict):
        url = self._single_user_url(user_id)
        auth = self._get_auth()

        self._session.put(url, auth=auth, json=update_data)

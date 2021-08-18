import requests

from utils.auth import BearerAuth


class KeycloakAdminClient:
    def __init__(self, server_url, realm_name, client_id, client_secret):
        self._server_url = server_url
        self._realm_name = realm_name
        self._client_id = client_id
        self._client_secret = client_secret

        self._session = requests.Session()

    def get_user(self, user_id):
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

        url = f"{self._server_url}/auth/admin/realms/{self._realm_name}/users/{user_id}"

        return self._session.get(url, auth=BearerAuth(access_token)).json()

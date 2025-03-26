from open_city_profile.oidc import KeycloakTokenExchange
from utils.keycloak import KeycloakAdminClient

ACCESS_TOKEN = "access123"
API_TOKEN = "token123"


def patch_keycloak_token_exchange(mocker):
    mocker.patch.object(
        KeycloakTokenExchange, "fetch_access_token", return_value=ACCESS_TOKEN
    )
    mocker.patch.object(
        KeycloakTokenExchange, "fetch_api_token", return_value=API_TOKEN
    )
    mocker.patch.object(KeycloakAdminClient, "delete_user", return_value=None)

from open_city_profile.settings import *  # noqa

USE_X_FORWARDED_FOR = True

INSTALLED_APPS += ["open_city_profile.tests.app"]  # noqa: F405

OIDC_API_TOKEN_AUTH = {
    "AUDIENCE": "test_audience",
    "ISSUER": "https://test_issuer",
    "REQUIRE_API_SCOPE_FOR_AUTHENTICATION": False,
}

GDPR_AUTH_CALLBACK_URL = "https://localhost/callback"

TUNNISTAMO_OIDC_ENDPOINT = ""
TUNNISTAMO_CLIENT_ID = ""
TUNNISTAMO_CLIENT_SECRET = ""
TUNNISTAMO_API_TOKENS_URL = ""

KEYCLOAK_BASE_URL = ""
KEYCLOAK_REALM = ""
KEYCLOAK_CLIENT_ID = ""
KEYCLOAK_CLIENT_SECRET = ""
KEYCLOAK_GDPR_CLIENT_ID = ""
KEYCLOAK_GDPR_CLIENT_SECRET = ""

from open_city_profile.settings import *  # noqa

OIDC_API_TOKEN_AUTH = {
    "AUDIENCE": "test_audience",
    "ISSUER": "https://test_issuer",
    "REQUIRE_API_SCOPE_FOR_AUTHENTICATION": False,
}

GDPR_AUTH_CALLBACK_URL = "https://localhost/callback"

TUNNISTAMO_OIDC_ENDPOINT = "https://localhost"
TUNNISTAMO_CLIENT_ID = "key"
TUNNISTAMO_CLIENT_SECRET = "secret"
TUNNISTAMO_API_TOKENS_URL = "https://localhost/api-tokens"

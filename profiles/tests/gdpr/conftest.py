import pytest


@pytest.fixture(autouse=True)
def setup_keycloak_settings(settings):
    settings.KEYCLOAK_BASE_URL = "https://localhost/auth"
    settings.KEYCLOAK_REALM = "keycloak-realm"
    settings.KEYCLOAK_CLIENT_ID = "profile-keycloak-client-id"
    settings.KEYCLOAK_CLIENT_SECRET = "secret"
    settings.KEYCLOAK_GDPR_CLIENT_ID = "profile-gdpr-test"
    settings.KEYCLOAK_GDPR_CLIENT_SECRET = "secret"


@pytest.fixture
def service_1(service_factory):
    return service_factory(
        name="service-1",
        gdpr_url="https://example-1.com/",
        gdpr_query_scope="gdprquery",
        gdpr_delete_scope="gdprdelete",
        gdpr_audience="service-1-gdpr-audience",
    )


@pytest.fixture
def service_2(service_factory):
    return service_factory(
        name="service-2",
        gdpr_url="https://example-2.com/",
        gdpr_query_scope="gdprquery",
        gdpr_delete_scope="gdprdelete",
        gdpr_audience="service-2-gdpr-audience",
    )

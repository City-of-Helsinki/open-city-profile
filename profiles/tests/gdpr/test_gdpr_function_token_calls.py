from urllib.parse import parse_qs, urlparse

import pytest

from profiles.connected_services import (
    delete_connected_service_data,
    download_connected_service_data,
)
from profiles.tests.factories import ProfileFactory
from services.tests.factories import ServiceConnectionFactory

AUTHORIZATION_CODE = "keycloak_auth_code"
KEYCLOAK_API_TOKEN_MARKER = "keycloak_api_token"

KEYCLOAK_BASE_URL = "https://keycloak.example.com/auth"
KEYCLOAK_REALM = "example-realm"
KEYCLOAK_OPENID_CONFIGURATION_ENDPOINT = (
    f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}/.well-known/openid-configuration"
)
KEYCLOAK_TOKEN_ENDPOINT = (
    f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
)


def _get_param_from_body(request, param_name):
    return parse_qs(request.body).get(param_name)[0]


@pytest.fixture
def setup_services_and_mocks(
    request,
    settings,
    service_factory,
    requests_mock,
):
    profile = ProfileFactory()

    # Keycloak
    settings.KEYCLOAK_BASE_URL = KEYCLOAK_BASE_URL
    settings.KEYCLOAK_REALM = KEYCLOAK_REALM
    settings.KEYCLOAK_GDPR_CLIENT_ID = "test-gdpr-client"
    settings.KEYCLOAK_GDPR_CLIENT_SECRET = "testsecret"
    requests_mock.get(
        KEYCLOAK_OPENID_CONFIGURATION_ENDPOINT,
        json={"token_endpoint": KEYCLOAK_TOKEN_ENDPOINT},
    )

    def get_keycloak_token_response(token_request, context):
        grant_type = _get_param_from_body(token_request, "grant_type")
        if grant_type == "authorization_code":
            return {"access_token": "keycloak_access_token"}
        elif grant_type == "urn:ietf:params:oauth:grant-type:uma-ticket":
            audience = _get_param_from_body(token_request, "audience")
            return {"access_token": f"{audience}-{KEYCLOAK_API_TOKEN_MARKER}"}

    requests_mock.post(
        KEYCLOAK_TOKEN_ENDPOINT,
        json=get_keycloak_token_response,
    )

    # Services
    services = []
    service_connections = {}
    for idx in range(request.param):
        service = service_factory(
            name=f"service{idx}",
            gdpr_url=f"https://service{idx}.example.com/gdpr/",
            gdpr_query_scope="gdprquery",
            gdpr_delete_scope="gdprdelete",
            gdpr_audience=f"service{idx}-api",
        )

        service_connection = ServiceConnectionFactory(profile=profile, service=service)
        service_gdpr_url = service_connection.get_gdpr_url()
        requests_mock.get(
            service_gdpr_url,
            json={
                "key": f"SERVICE-{idx}",
                "children": [{"key": "CUSTOMERID", "value": "123"}],
            },
        )
        requests_mock.delete(service_gdpr_url, status_code=204)

        services.append(service)
        service_connections[service] = service_connection

    return {
        "profile": profile,
        "services": services,
        "service_connections": service_connections,
    }


def _get_requests_from_history_by_url(url, request_history):
    def strip_query_params(request_url):
        return urlparse(request_url)._replace(query=None).geturl()

    return [
        request for request in request_history if strip_query_params(request.url) == url
    ]


def _get_requests_from_history(endpoint, request_history):
    grant_type = None
    url = KEYCLOAK_TOKEN_ENDPOINT
    if endpoint == "token":
        grant_type = "authorization_code"
    elif endpoint == "api-token":
        grant_type = "urn:ietf:params:oauth:grant-type:uma-ticket"

    result = []
    for request in _get_requests_from_history_by_url(url, request_history):
        if not grant_type:
            result.append(request)
        else:
            request_grant_type = _get_param_from_body(request, "grant_type")
            if request_grant_type == grant_type:
                result.append(request)

    return result


def assert_correct_access_token_calls(services, request_history):
    keycloak_token_requests = _get_requests_from_history("token", request_history)
    if services:
        assert len(keycloak_token_requests) == 1, (
            "Keycloak token endpoint should be called once if there are services accepting Keycloak API tokens"
        )
        assert (
            _get_param_from_body(keycloak_token_requests[0], "code")
            == AUTHORIZATION_CODE
        ), "Keycloak token call should use Keycloak authorization code"
    else:
        assert len(keycloak_token_requests) == 0, (
            "Keycloak token endpoint should not be called if there are no connected services"
        )


def assert_correct_api_token_calls(services, request_history):
    keycoak_api_token_requests = _get_requests_from_history(
        "api-token", request_history
    )
    if services:
        assert len(keycoak_api_token_requests) == len(services), (
            "Keycloak token endpoint should be called once for every service that accepts Keycloak API tokens"
        )
    else:
        assert len(keycoak_api_token_requests) == 0, (
            "Keycloak token endpoint should not be called if there are no connected services"
        )


def assert_correct_gdpr_api_calls(services, service_connections, request_history):
    for service in services:
        service_connection = service_connections[service]

        gdpr_api_requests = _get_requests_from_history_by_url(
            service_connection.get_gdpr_url(), request_history
        )
        assert len(gdpr_api_requests) == 1, "GDPR API should be called exactly once"

        token_used = (
            gdpr_api_requests[0].headers["authorization"].replace("Bearer ", "")
        )
        assert KEYCLOAK_API_TOKEN_MARKER in token_used, (
            "Services accepting only Keycloak API tokens should be called with a Keycloak API token"
        )


service_sets = [
    pytest.param(0, id="No services"),
    pytest.param(1, id="One service"),
    pytest.param(2, id="Two services"),
]


@pytest.mark.parametrize("setup_services_and_mocks", service_sets, indirect=True)
def test_download_connected_service_data(requests_mock, setup_services_and_mocks):
    profile = setup_services_and_mocks["profile"]
    services = setup_services_and_mocks["services"]
    service_connections = setup_services_and_mocks["service_connections"]

    download_connected_service_data(
        profile,
        AUTHORIZATION_CODE,
    )

    request_history = requests_mock.request_history

    assert_correct_access_token_calls(services, request_history)
    assert_correct_api_token_calls(services, request_history)
    assert_correct_gdpr_api_calls(services, service_connections, request_history)


@pytest.mark.parametrize("setup_services_and_mocks", service_sets, indirect=True)
def test_delete_connected_service_data(requests_mock, setup_services_and_mocks):
    profile = setup_services_and_mocks["profile"]
    services = setup_services_and_mocks["services"]
    service_connections = setup_services_and_mocks["service_connections"]

    delete_connected_service_data(profile, AUTHORIZATION_CODE, dry_run=True)

    request_history = requests_mock.request_history

    assert_correct_access_token_calls(services, request_history)
    assert_correct_api_token_calls(services, request_history)
    assert_correct_gdpr_api_calls(services, service_connections, request_history)

from urllib.parse import parse_qs, urlparse

import pytest

from profiles.connected_services import (
    delete_connected_service_data,
    download_connected_service_data,
)
from profiles.tests.factories import ProfileFactory
from services.enums import ServiceIdp
from services.tests.factories import ServiceConnectionFactory

AUTHORIZATION_CODE = "tunnistamo_auth_code"
AUTHORIZATION_CODE_KEYCLOAK = "keycloak_auth_code"
TUNNISTAMO_API_TOKEN_MARKER = "tunnistamo_api_token"
KEYCLOAK_API_TOKEN_MARKER = "keycloak_api_token"

TUNNISTAMO_OIDC_ENDPOINT = "https://tunnistamo.example.com/oidc"
TUNNISTAMO_OPENID_CONFIGURATION_ENDPOINT = (
    f"{TUNNISTAMO_OIDC_ENDPOINT}/.well-known/openid-configuration"
)
TUNNISTAMO_TOKEN_ENDPOINT = f"{TUNNISTAMO_OIDC_ENDPOINT}/token"
TUNNISTAMO_API_TOKENS_URL = "https://tunnistamo.example.com/api-tokens/"

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

    # Tunnistamo
    settings.TUNNISTAMO_OIDC_ENDPOINT = TUNNISTAMO_OIDC_ENDPOINT
    settings.TUNNISTAMO_API_TOKENS_URL = TUNNISTAMO_API_TOKENS_URL
    requests_mock.get(
        TUNNISTAMO_OPENID_CONFIGURATION_ENDPOINT,
        json={"token_endpoint": TUNNISTAMO_TOKEN_ENDPOINT},
    )
    requests_mock.post(
        TUNNISTAMO_TOKEN_ENDPOINT,
        json={"access_token": "tunnistamo_access_token"},
    )

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
    tunnistamo_services = []
    for idx, idp_value in enumerate(request.param):
        if not idp_value or ServiceIdp.TUNNISTAMO in idp_value:
            service = service_factory(
                name=f"service{idx}",
                gdpr_url=f"https://service{idx}.example.com/gdpr/",
                gdpr_query_scope=f"https://auth.example.com/service{idx}.gdprquery",
                gdpr_delete_scope=f"https://auth.example.com/service{idx}.gdprdelete",
                idp=idp_value,
            )
            if idp_value and ServiceIdp.KEYCLOAK in idp_value:
                service.gdpr_audience = f"service{idx}-api"
                service.save()

            tunnistamo_services.append(service)
        else:
            service = service_factory(
                name=f"service{idx}",
                gdpr_url=f"https://service{idx}.example.com/gdpr/",
                gdpr_query_scope="gdprquery",
                gdpr_delete_scope="gdprdelete",
                idp=idp_value,
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

    # Tunnistamo API tokens
    if tunnistamo_services:
        tunnistamo_api_tokens = {}
        for tunnistamo_service in tunnistamo_services:
            scope = tunnistamo_service.gdpr_query_scope
            api_audience = scope[: scope.rfind(".")]
            tunnistamo_api_tokens[api_audience] = (
                f"{tunnistamo_service.name}-{TUNNISTAMO_API_TOKEN_MARKER}"
            )

        requests_mock.get(
            settings.TUNNISTAMO_API_TOKENS_URL,
            json=tunnistamo_api_tokens,
        )

    return {
        "profile": profile,
        "services": services,
        "service_connections": service_connections,
    }


def _group_services(services):
    tunnistamo_services = []
    keycloak_services = []
    for service in services:
        if service.is_pure_keycloak:
            keycloak_services.append(service)
        else:
            tunnistamo_services.append(service)

    return tunnistamo_services, keycloak_services


def _get_requests_from_history_by_url(url, request_history):
    def strip_query_params(request_url):
        return urlparse(request_url)._replace(query=None).geturl()

    return [
        request for request in request_history if strip_query_params(request.url) == url
    ]


def _get_requests_from_history(idp, endpoint, request_history):
    url = None
    grant_type = None
    if idp == ServiceIdp.TUNNISTAMO:
        if endpoint == "token":
            url = TUNNISTAMO_TOKEN_ENDPOINT
        elif endpoint == "api-token":
            url = TUNNISTAMO_API_TOKENS_URL
    elif idp == ServiceIdp.KEYCLOAK:
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
    tunnistamo_services, keycloak_services = _group_services(services)

    tunnistamo_token_requests = _get_requests_from_history(
        ServiceIdp.TUNNISTAMO, "token", request_history
    )
    if tunnistamo_services:
        assert (
            len(tunnistamo_token_requests) == 1
        ), "Tunnistamo token endpoint should be called once if there are services accepting Tunnistamo API tokens"
        assert (
            _get_param_from_body(tunnistamo_token_requests[0], "code")
            == AUTHORIZATION_CODE
        ), "Tunnistamo token call should use Tunnistamo authorization code"
    else:
        assert (
            len(tunnistamo_token_requests) == 0
        ), "Tunnistamo token endpoint should not be called if there are only services accepting Keycloak API tokens"

    keycloak_token_requests = _get_requests_from_history(
        ServiceIdp.KEYCLOAK, "token", request_history
    )
    if keycloak_services:
        assert (
            len(keycloak_token_requests) == 1
        ), "Keycloak token endpoint should be called once if there are services accepting Keycloak API tokens"
        assert (
            _get_param_from_body(keycloak_token_requests[0], "code")
            == AUTHORIZATION_CODE_KEYCLOAK
        ), "Keycloak token call should use Keycloak authorization code"
    else:
        assert (
            len(keycloak_token_requests) == 0
        ), "Keycloak token endpoint should not be called if there are only services accepting Tunnistamo API tokens"


def assert_correct_api_token_calls(services, request_history):
    tunnistamo_services, keycloak_services = _group_services(services)

    tunnistamo_api_token_requests = _get_requests_from_history(
        ServiceIdp.TUNNISTAMO, "api-token", request_history
    )
    if tunnistamo_services:
        assert (
            len(tunnistamo_api_token_requests) == 1
        ), "Tunnistamo API token endpoint should be called once if there are services accepting Tunnistamo API tokens"

    else:
        assert (
            len(tunnistamo_api_token_requests) == 0
        ), "Tunnistamo API token endpoint should not be called if there are only services accepting Keycloak API tokens"

    keycoak_api_token_requests = _get_requests_from_history(
        ServiceIdp.KEYCLOAK, "api-token", request_history
    )
    if keycloak_services:
        assert len(keycoak_api_token_requests) == len(
            keycloak_services
        ), "Keycloak token endpoint should be called once for every service that accepts Keycloak API tokens"
    else:
        assert (
            len(keycoak_api_token_requests) == 0
        ), "Keycloak token endpoint should not be called if there are only services accepting Tunnistamo API tokens"


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
        if service.is_pure_keycloak:
            assert (
                KEYCLOAK_API_TOKEN_MARKER in token_used
            ), "Services accepting only Keycloak API tokens should be called with a Keycloak API token"
        else:
            assert (
                TUNNISTAMO_API_TOKEN_MARKER in token_used
            ), "Services accepting Tunnistamo API tokens should be called with a Tunnistamo API token"


service_sets = [
    pytest.param([], id="No services"),
    pytest.param([None], id="One service: IDP not set"),
    pytest.param([[ServiceIdp.TUNNISTAMO]], id="One service: Tunnistamo"),
    pytest.param([[ServiceIdp.KEYCLOAK]], id="One service: Keycloak"),
    pytest.param(
        [[ServiceIdp.TUNNISTAMO, ServiceIdp.KEYCLOAK]],
        id="One service: Tunnistamo/Keycloak",
    ),
    pytest.param([None, None], id="Two services: IDP not set * 2"),
    pytest.param(
        [None, [ServiceIdp.TUNNISTAMO]], id="Two services: IDP not set, Tunnistamo"
    ),
    pytest.param(
        [None, [ServiceIdp.KEYCLOAK]], id="Two services: IDP not set, Keycloak"
    ),
    pytest.param(
        [[ServiceIdp.TUNNISTAMO], [ServiceIdp.KEYCLOAK]],
        id="Two services: Tunnistamo, Keycloak",
    ),
    pytest.param(
        [[ServiceIdp.TUNNISTAMO], [ServiceIdp.TUNNISTAMO]],
        id="Two services: Tunnistamo * 2",
    ),
    pytest.param(
        [[ServiceIdp.KEYCLOAK], [ServiceIdp.KEYCLOAK]], id="Two services: Keycloak * 2"
    ),
    pytest.param(
        [
            [ServiceIdp.TUNNISTAMO, ServiceIdp.KEYCLOAK],
            [ServiceIdp.TUNNISTAMO],
        ],
        id="Two services: Tunnistamo/Keycloak, Tunnistamo",
    ),
    pytest.param(
        [
            [ServiceIdp.TUNNISTAMO, ServiceIdp.KEYCLOAK],
            [ServiceIdp.KEYCLOAK],
        ],
        id="Two services: Tunnistamo/Keycloak, Keycloak",
    ),
    pytest.param(
        [
            [ServiceIdp.TUNNISTAMO, ServiceIdp.KEYCLOAK],
            [ServiceIdp.TUNNISTAMO, ServiceIdp.KEYCLOAK],
        ],
        id="Two services: Tunnistamo/Keycloak * 2",
    ),
]


@pytest.mark.parametrize("setup_services_and_mocks", service_sets, indirect=True)
def test_download_connected_service_data(requests_mock, setup_services_and_mocks):
    profile = setup_services_and_mocks["profile"]
    services = setup_services_and_mocks["services"]
    service_connections = setup_services_and_mocks["service_connections"]

    download_connected_service_data(
        profile,
        AUTHORIZATION_CODE,
        AUTHORIZATION_CODE_KEYCLOAK,
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

    # Test delete functionality only with dry_run as True so that the request counts
    # are the same regardless of IDP. (If the dry_run is False the
    # delete_connected_service_data would make GDPR API calls twice with dry_run as
    # True and with dry_run as False. In that case Keycloak API token would be fetched
    # twice but Tunnistamo tokens only once)
    delete_connected_service_data(
        profile, AUTHORIZATION_CODE, AUTHORIZATION_CODE_KEYCLOAK, dry_run=True
    )

    request_history = requests_mock.request_history

    assert_correct_access_token_calls(services, request_history)
    assert_correct_api_token_calls(services, request_history)
    assert_correct_gdpr_api_calls(services, service_connections, request_history)

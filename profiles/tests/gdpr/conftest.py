import pytest

_SCOPE_1 = "https://api.hel.fi/auth/api-1"
_SCOPE_2 = "https://api.hel.fi/auth/api-2"


@pytest.fixture
def api_token_1():
    return "api_token_1"


@pytest.fixture
def api_token_2():
    return "api_token_2"


@pytest.fixture
def gdpr_api_tokens(api_token_1, api_token_2):
    return {
        _SCOPE_1: api_token_1,
        _SCOPE_2: api_token_2,
    }


@pytest.fixture
def service_1(service_factory):
    return service_factory(
        name="service-1",
        gdpr_url="https://example-1.com/",
        gdpr_query_scope=f"{_SCOPE_1}.gdprquery",
        gdpr_delete_scope=f"{_SCOPE_1}.gdprdelete",
    )


@pytest.fixture
def service_2(service_factory):
    return service_factory(
        name="service-2",
        gdpr_url="https://example-2.com/",
        gdpr_query_scope=f"{_SCOPE_2}.gdprquery",
        gdpr_delete_scope=f"{_SCOPE_2}.gdprdelete",
    )

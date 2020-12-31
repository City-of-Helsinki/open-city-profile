import pytest
from django.conf import settings

from open_city_profile.exceptions import TokenExchangeError
from open_city_profile.oidc import TunnistamoTokenExchange


def test_authorization_code_exchange_successful(user, requests_mock):
    tte = TunnistamoTokenExchange()
    expected_response = {"scope": "token"}
    requests_mock.get(
        f"{settings.TUNNISTAMO_OIDC_ENDPOINT}/.well-known/openid-configuration",
        json={"token_endpoint": f"{settings.TUNNISTAMO_OIDC_ENDPOINT}/token"},
    )
    requests_mock.post(
        f"{settings.TUNNISTAMO_OIDC_ENDPOINT}/token", json={"access_token": "token"}
    )
    requests_mock.get(settings.TUNNISTAMO_API_TOKENS_URL, json=expected_response)

    response = tte.fetch_api_tokens("auth_code")

    assert response == expected_response


def test_authorization_code_exchange_failed(requests_mock):
    tte = TunnistamoTokenExchange()
    requests_mock.get(
        f"{settings.TUNNISTAMO_OIDC_ENDPOINT}/.well-known/openid-configuration",
        json={"token_endpoint": f"{settings.TUNNISTAMO_OIDC_ENDPOINT}/token"},
    )
    requests_mock.post(
        f"{settings.TUNNISTAMO_OIDC_ENDPOINT}/token", json={}, status_code=403
    )

    with pytest.raises(TokenExchangeError) as e:
        tte.fetch_api_tokens("auth_code")

    assert str(e.value) == "Failed to obtain an access token."

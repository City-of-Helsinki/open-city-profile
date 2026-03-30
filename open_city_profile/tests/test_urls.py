import pytest

from open_city_profile import __version__


def test_healthz(client):
    response = client.get("/healthz")

    assert response.status_code == 200


@pytest.mark.django_db
def test_readiness(client, settings):
    settings.SENTRY_RELEASE = "unittest"
    response = client.get("/readiness")

    assert response.status_code == 200
    data = response.json()
    assert data == {
        "status": "ok",
        "database": "ok",
        "packageVersion": __version__,
        "release": "unittest",
    }

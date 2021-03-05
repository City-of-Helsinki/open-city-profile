import pytest

from services.utils import set_service_to_request


@pytest.fixture
def req(rf):
    return rf.post("/path")


class UserAuth:
    def __init__(self, data):
        self.data = data


@pytest.mark.parametrize(
    "user_auth", [None, UserAuth({}), UserAuth({"azp": "not found"})]
)
def test_service_can_not_be_determined(req, user_auth):
    if user_auth:
        req.user_auth = user_auth
    set_service_to_request(req)
    assert not hasattr(req, "service")
    assert not hasattr(req, "service_client_id")


def test_when_client_id_is_found_then_service_is_added_to_request(
    req, service_client_id
):
    req.user_auth = UserAuth({"azp": service_client_id.client_id})
    set_service_to_request(req)

    assert req.service_client_id == service_client_id
    assert req.service == service_client_id.service

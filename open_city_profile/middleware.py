from helusers.oidc import RequestJWTAuthentication

from services.utils import set_service_to_request


class JWTAuthentication:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            try:
                authenticator = RequestJWTAuthentication()
                user_auth = authenticator.authenticate(request)
                if user_auth is not None:
                    request.user_auth = user_auth
                    request.user = user_auth.user
                    set_service_to_request(request)
            except Exception as e:
                request.auth_error = e

        return self.get_response(request)

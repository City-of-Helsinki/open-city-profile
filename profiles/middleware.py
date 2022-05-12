from .utils import clear_thread_locals, set_current_request


class SetCurrentRequest:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_request(request)

        response = self.get_response(request)

        clear_thread_locals()

        return response

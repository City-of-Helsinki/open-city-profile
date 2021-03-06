from django.utils.deprecation import MiddlewareMixin

from .utils import clear_thread_locals, set_current_request


class SetCurrentRequest(MiddlewareMixin):
    def process_request(self, request):
        set_current_request(request)

    def process_response(self, request, response):
        clear_thread_locals()
        return response

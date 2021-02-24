from django.utils.deprecation import MiddlewareMixin

from .audit_log import flush_audit_log
from .utils import clear_thread_locals, set_current_request


class SetCurrentRequest(MiddlewareMixin):
    def process_request(self, request):
        set_current_request(request)

    def process_response(self, request, response):
        flush_audit_log()
        clear_thread_locals()
        return response

from django.http import HttpResponse
import threading
import logging
from django.utils.deprecation import MiddlewareMixin
from .utils import set_current_user


class SetUser(MiddlewareMixin):
    def process_request(self, request):
        set_current_user(getattr(request, "user", None))

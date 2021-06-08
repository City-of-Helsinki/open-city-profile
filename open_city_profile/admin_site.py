from django.conf import settings
from helusers.admin_site import AdminSite as HelUsersAdminSite


class AdminSite(HelUsersAdminSite):
    index_template = "admin/admin_index.html"

    def each_context(self, request):
        context = super().each_context(request)
        context["version"] = (
            settings.VERSION if settings.VERSION is not None else "unknown"
        )
        return context

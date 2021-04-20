from services.models import ServiceClientId


def set_service_to_request(request):
    if not hasattr(request, "service"):
        request.service = None

    if request.service is None and hasattr(request, "user_auth"):
        client_id = request.user_auth.data.get("azp")
        if not client_id:
            return

        service_client_id = (
            ServiceClientId.objects.select_related("service")
            .filter(client_id=client_id)
            .first()
        )
        if not service_client_id:
            return

        request.service_client_id = service_client_id
        request.service = service_client_id.service

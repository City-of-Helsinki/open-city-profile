from django.db import transaction

from services.models import AllowedDataField, ServiceClientId


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

        request.client_id = service_client_id.client_id
        request.service = service_client_id.service


@transaction.atomic
def generate_data_fields(allowed_data_fields_spec):
    for value in allowed_data_fields_spec:
        if not AllowedDataField.objects.filter(
            field_name=value.get("field_name")
        ).exists():
            data_field = AllowedDataField.objects.create(
                field_name=value.get("field_name")
            )
            for translation in value.get("translations"):
                data_field.set_current_language(translation["code"])
                data_field.label = translation["label"]
            data_field.save()

    current_field_names = [fs["field_name"] for fs in allowed_data_fields_spec]

    AllowedDataField.objects.exclude(field_name__in=current_field_names).delete()

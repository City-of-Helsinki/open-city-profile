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
        data_field, created = AllowedDataField.objects.get_or_create(
            field_name=value.get("field_name")
        )

        for translation in value.get("translations"):
            data_field.set_current_language(translation["code"])
            data_field.label = translation["label"]

        current_lang_codes = {tr["code"] for tr in value.get("translations")}
        lang_codes_in_db = set(data_field.get_available_languages())
        for removable_lang_code in lang_codes_in_db - current_lang_codes:
            data_field.delete_translation(removable_lang_code)

        data_field.save()

    current_field_names = [fs["field_name"] for fs in allowed_data_fields_spec]

    AllowedDataField.objects.exclude(field_name__in=current_field_names).delete()

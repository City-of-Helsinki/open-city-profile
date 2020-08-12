from datetime import date

from django.core.exceptions import ValidationError
from graphql_relay import from_global_id

from open_city_profile.exceptions import InvalidEmailFormatError
from youths.models import AdditionalContactPerson, YouthProfile


def calculate_age(birth_date):
    today = date.today()
    return (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )


def create_or_update_contact_persons(youth_profile: YouthProfile, data):
    for data_input in filter(None, data):
        acp_global_id = data_input.pop("id", None)
        if acp_global_id:
            # id is required on update input
            acp_id = from_global_id(acp_global_id)[1]
            item = AdditionalContactPerson.objects.get(
                youth_profile=youth_profile, pk=acp_id
            )
        else:
            item = AdditionalContactPerson(youth_profile=youth_profile)

        for field, value in data_input.items():
            setattr(item, field, value)

        try:
            item.save()
        except ValidationError as e:
            if hasattr(e, "error_dict") and "email" in e.error_dict:
                raise InvalidEmailFormatError("Email must be in valid email format")
            else:
                raise


def delete_contact_persons(youth_profile: YouthProfile, data):
    for remove_global_id in filter(None, data):
        remove_id = from_global_id(remove_global_id)[1]
        AdditionalContactPerson.objects.get(
            youth_profile=youth_profile, pk=remove_id
        ).delete()

from unittest import mock

from profiles.tests.factories import ProfileFactory, SensitiveDataFactory
from services.tests.factories import AllowedDataFieldFactory, ServiceConnectionFactory


def test_enable_allowed_data_fields_restriction_flag_false_shows_data(
    user_gql_client, service, settings
):
    settings.ENABLE_ALLOWED_DATA_FIELDS_RESTRICTION = False
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service)
    service.allowed_data_fields.add(AllowedDataFieldFactory(field_name="name"))
    SensitiveDataFactory(profile=profile)

    query = """
        {
            myProfile {
                firstName
                sensitivedata {
                    ssn
                }
            }
        }
    """

    executed = user_gql_client.execute(query, service=service)

    assert executed["data"]["myProfile"]["firstName"] == profile.first_name
    assert (
        executed["data"]["myProfile"]["sensitivedata"]["ssn"]
        == profile.sensitivedata.ssn
    )


@mock.patch("logging.warning")
def test_enable_allowed_data_fields_restriction_flag_logs_warning_if_access_to_restricted_field(
    mock_log, user_gql_client, service, settings
):
    settings.ENABLE_ALLOWED_DATA_FIELDS_RESTRICTION = False
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service)
    service.allowed_data_fields.add(AllowedDataFieldFactory(field_name="name"))
    SensitiveDataFactory(profile=profile)

    query = """
         {
             myProfile {
                 firstName
                 sensitivedata {
                     ssn
                 }
             }
         }
     """

    user_gql_client.execute(query, service=service)

    assert mock_log.call_count == 1

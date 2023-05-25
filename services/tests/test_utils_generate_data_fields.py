import pytest

from services.models import AllowedDataField
from services.tests.factories import ServiceFactory
from services.utils import generate_data_fields


def _get_initial_spec():
    return [
        {
            "field_name": "name",
            "translations": [
                {"code": "fi", "label": "Nimi"},
                {"code": "sv", "label": "Namn"},
            ],
        },
        {
            "field_name": "email",
            "translations": [
                {"code": "en", "label": "Email"},
                {"code": "fi", "label": "Sähköposti"},
                {"code": "sv", "label": "Epost"},
            ],
        },
    ]


def _assert_fields_match_spec(spec):
    allowed_data_fields = AllowedDataField.objects.all()
    assert len(allowed_data_fields) == len(spec)

    previous_order = -1

    for value in spec:
        field = allowed_data_fields.filter(field_name=value["field_name"]).first()
        assert field is not None

        assert field.order > previous_order
        previous_order = field.order

        for translation in value["translations"]:
            field.set_current_language(translation["code"])
            assert field.label == translation["label"]

        expected_lang_codes = {tr["code"] for tr in value["translations"]}
        actual_lang_codes = set(field.get_available_languages())
        assert expected_lang_codes == actual_lang_codes


def _test_changed_spec(new_spec):
    for spec in _get_initial_spec(), new_spec:
        generate_data_fields(spec)
        _assert_fields_match_spec(spec)


def test_unchanged_configuration_changes_nothing():
    _test_changed_spec(_get_initial_spec())


def test_adding_a_new_field():
    new_spec = _get_initial_spec() + [
        {
            "field_name": "address",
            "translations": [
                {"code": "en", "label": "Address"},
                {"code": "fi", "label": "Osoite"},
                {"code": "sv", "label": "Adress"},
            ],
        }
    ]

    _test_changed_spec(new_spec)


@pytest.mark.parametrize("num_removed", [1, 2])
def test_removing_a_field(num_removed):
    new_spec = _get_initial_spec()[num_removed:]

    _test_changed_spec(new_spec)


def test_add_new_translations_to_an_existing_field():
    new_spec = _get_initial_spec()
    new_spec[0]["translations"].append({"code": "en", "label": "Name"})
    new_spec[0]["translations"].append({"code": "no", "label": "Navn"})

    _test_changed_spec(new_spec)


def test_update_translations_for_an_existing_field():
    new_spec = _get_initial_spec()
    new_spec[0]["translations"][0].update({"label": "Uusi nimi"})
    new_spec[0]["translations"][1].update({"label": "Ny namn"})

    _test_changed_spec(new_spec)


def test_remove_translations_from_an_existing_field():
    new_spec = _get_initial_spec()
    new_spec[1]["translations"].pop(2)
    new_spec[1]["translations"].pop(0)

    _test_changed_spec(new_spec)


def test_change_order_of_fields():
    new_spec = _get_initial_spec()
    new_spec.reverse()

    _test_changed_spec(new_spec)


@pytest.mark.parametrize("num_fields_to_replace", (1, 2))
def test_replace_allowed_data_fields_in_services_with_another_one_using_an_alias(
    num_fields_to_replace,
):
    allowed_fields_spec = _get_initial_spec()
    generate_data_fields(allowed_fields_spec)

    services = ServiceFactory.create_batch(2)
    for service in services:
        service.allowed_data_fields.set(AllowedDataField.objects.all())

    for field_index in range(num_fields_to_replace):
        replaceable_field = allowed_fields_spec[field_index]
        original_field_name = replaceable_field["field_name"]
        replaceable_field.update(
            {
                "field_name": original_field_name + "_new",
                "aliases": (
                    original_field_name,
                    f"another_old_name_{original_field_name}",
                ),
            }
        )

    _test_changed_spec(allowed_fields_spec)

    current_field_names = {f["field_name"] for f in allowed_fields_spec}
    for service in services:
        current_service_field_names = {
            f.field_name for f in service.allowed_data_fields.all()
        }
        assert current_field_names == current_service_field_names


def test_when_no_alias_for_a_removed_field_is_found_then_a_valueerror_is_raised():
    allowed_fields_spec = _get_initial_spec()
    generate_data_fields(allowed_fields_spec)

    service = ServiceFactory()
    service.allowed_data_fields.set(AllowedDataField.objects.all())

    allowed_fields_spec[0]["field_name"] = "new_field_name"

    with pytest.raises(ValueError):
        generate_data_fields(allowed_fields_spec)

    _assert_fields_match_spec(_get_initial_spec())

    assert set(service.allowed_data_fields.all()) == set(AllowedDataField.objects.all())

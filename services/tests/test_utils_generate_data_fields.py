from services.models import AllowedDataField
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


def _test_changed_spec(new_spec):
    for spec in _get_initial_spec(), new_spec:
        generate_data_fields(spec)

        allowed_data_fields = AllowedDataField.objects.all()
        assert len(allowed_data_fields) == len(spec)

        for value in spec:
            field = allowed_data_fields.filter(field_name=value["field_name"]).first()
            assert field is not None
            for translation in value["translations"]:
                field.set_current_language(translation["code"])
                assert field.label == translation["label"]


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

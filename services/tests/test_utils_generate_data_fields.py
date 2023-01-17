import pytest

from services.models import AllowedDataField
from services.utils import generate_data_fields


@pytest.mark.parametrize("times", [1, 2])
def test_generate_data_fields(times):
    allowed_data_fields_spec = [
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

    """Test data fields are generated and that function can be run multiple times."""
    assert AllowedDataField.objects.count() == 0
    for i in range(times):
        generate_data_fields(allowed_data_fields_spec)
    allowed_data_fields = AllowedDataField.objects.all()
    assert len(allowed_data_fields) == len(allowed_data_fields_spec)

    for value in allowed_data_fields_spec:
        field = allowed_data_fields.filter(field_name=value["field_name"]).first()
        assert field is not None
        for translation in value["translations"]:
            field.set_current_language(translation["code"])
            assert field.label == translation["label"]

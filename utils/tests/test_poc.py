from inspect import signature

from django.db.models.fields.reverse_related import ManyToOneRel
from django.db.models.fields.related_descriptors import ManyToManyDescriptor
from django.utils.module_loading import import_string

from parler.fields import TranslatedFieldDescriptor

from services.models import AllowedDataField, Service, ServiceClientId


ALLOWED_DATA_FIELD_DATA = [
    {
        "field_name": "name",
        "label": {
            "en": "Name",
            "fi": "Nimi",
            "sv": "Namn",
        },
    },
    {
        "field_name": "email",
        "label": {
            "en": "Email",
            "fi": "Sähköposti",
            "sv": "Epost",
        },
    },
    {
        "field_name": "address",
        "label": {
            "en": "Address",
            "fi": "Osoite",
            "sv": "Adress",
        },
    },
    {
        "field_name": "phone",
        "label": {
            "en": "Phone",
            "fi": "Puhelinnumero",
            "sv": "Telefonnummer",
        },
    },
    {
        "field_name": "ssn",
        "label": {
            "en": "Social Security Number",
            "fi": "Henkilötunnus",
            "sv": "Personnnumer",
        },
    },
]


SERVICE_DATA = [
    {
        "name": "berth",
        "title": {
            "en": "Boat berths",
            "fi": "Venepaikka",
            "sv": "Båtplatser",
        },
        "description": {
            "en": "Boat berths in Helsinki city boat harbours.",
            "fi": "Venepaikat helsingin kaupungin venesatamissa.",
            "sv": "Båtplatser i Helsingfors båthamnar.",
        },
        "gdpr_url": "https://berth/gdpr",
        "client_ids": [
            {
                "client_id": "berth_client_1",
            },
        ],
        "allowed_data_fields": ["name", "email", "address", "phone", "ssn"],
    },
    {
        "name": "youth_membership",
        "title": {
            "en": "Youth service membership",
            "fi": "Nuorisopalveluiden jäsenkortti",
            "sv": "Ungdomstjänstmedlemskap",
        },
        "description": {
            "en": "With youth service membership you get to participate in all activities "
                "offered by Helsinki city community centers.",
            "fi": "Nuorisopalveluiden Jäsenkortilla pääset mukaan nuorisotalojen toimintaan. "
                "Saat etuja kaupungin kulttuuritapahtumissa ja paikoissa.",
            "sv": "Med medlemskap i ungdomstjänsten får du delta i alla aktiviteter som "
                "erbjuds av Helsingfors ungdomscenter.",
        },
        "gdpr_url": "https://youth/gdpr",
        "client_ids": [
            {
                "client_id": "youth_client_1",
            },
            {
                "client_id": "youth_client_2",
            },
        ],
        "allowed_data_fields": ["name", "email", "address", "phone"],
    },
]


def partition(pred, iterable):
    trues = []
    falses = []
    for item in iterable:
        if pred(item):
            trues.append(item)
        else:
            falses.append(item)
    return trues, falses


def get_natural_key_name(model):
    sig = signature(model.objects.get_by_natural_key)
    # Supports only natural key with one field
    assert len(sig.parameters) == 1
    return list(sig.parameters.keys())[0]


def import_instances(model, data, parents=None):
    key_name = get_natural_key_name(model)

    related_types = {item.name: item for item in model._meta.related_objects}

    all_keys = []

    for datum in data:
        key_value = datum[key_name]
        all_keys.append(key_value)

        related_fields, regular_fields = partition(lambda kv: kv[0] in related_types, datum.items())
        many_to_many_fields = []

        key_data = {key_name: key_value}
        try:
            instance = model.objects.get(**key_data)
        except model.DoesNotExist:
            instance = model(**key_data)

        for field_name, field_value in regular_fields:
            field = getattr(model, field_name)

            if isinstance(field, ManyToManyDescriptor):
                # Extract many-to-many fields for later handling
                many_to_many_fields.append((field_name, field_value))
            elif isinstance(field, TranslatedFieldDescriptor):
                # Handle translated fields
                for lang, translated_value in field_value.items():
                    instance.set_current_language(lang)
                    setattr(instance, field_name, translated_value)
            else:
                # Handle regular fields
                setattr(instance, field_name, field_value)

        if parents:
            # Set "parents", that is foreign key relations
            for parent_field_name, parent_value in parents.items():
                setattr(instance, parent_field_name, parent_value)

        # TODO clean/validate before save?
        instance.save()

        # Now that the instance is in the database, many-to-many fields can be handled
        for field_name, field_value in many_to_many_fields:
            remote_model = model._meta.get_field(field_name).remote_field.model
            remote_model_key = get_natural_key_name(remote_model)
            remote_model_filter = {f"{remote_model_key}__in": field_value}
            remote_instances = set(remote_model.objects.filter(**remote_model_filter).all())
            getattr(instance, field_name).set(remote_instances)

        for field_name, field_value in related_fields:
            # Handle related objects
            if type(related_types[field_name]) == ManyToOneRel:
                parents_of_children = {related_types[field_name].field.name: instance}
                child_model = related_types[field_name].field.model
                import_instances(child_model, field_value, parents=parents_of_children)

    qs_for_delete = model.objects
    if parents:
        qs_for_delete = qs_for_delete.filter(**parents)
    qs_for_delete.exclude(**{f"{key_name}__in": all_keys}).delete()


def test_import():
    def check_translations(service, service_data):
        for lang, value in service_data["title"].items():
            service.set_current_language(lang)
            assert service.title == value
        for lang, value in service_data["description"].items():
            service.set_current_language(lang)
            assert service.description == value

    AllowedDataField.objects.create(field_name="no_longer_needed")

    Service.objects.create(name="old_service")

    berth_service = Service.objects.create(name="berth", gdpr_url="wrong_url")
    ServiceClientId.objects.create(service=berth_service, client_id="old_berth_client_id")

    import_instances(import_string("services.models.AllowedDataField"), ALLOWED_DATA_FIELD_DATA)
    import_instances(import_string("services.models.Service"), SERVICE_DATA)


    adf_field_names = [adf["field_name"] for adf in ALLOWED_DATA_FIELD_DATA]

    assert AllowedDataField.objects.count() == len(adf_field_names)
    for field_name in adf_field_names:
        assert AllowedDataField.objects.get(field_name=field_name) is not None


    assert not Service.objects.filter(name="old_service").exists()


    berth_service = Service.objects.get(name="berth")
    berth_data = SERVICE_DATA[0]

    assert berth_service.gdpr_url == "https://berth/gdpr"

    check_translations(berth_service, berth_data)

    client_id = berth_service.client_ids.get()  # There should be only one client_id left
    assert client_id.service == berth_service
    assert client_id.client_id == "berth_client_1"

    expected_berth_fields = set(AllowedDataField.objects.filter(field_name__in=berth_data["allowed_data_fields"]).all())
    assert set(berth_service.allowed_data_fields.all()) == expected_berth_fields


    youth_service = Service.objects.get(name="youth_membership")
    youth_data = SERVICE_DATA[1]

    assert youth_service.gdpr_url == "https://youth/gdpr"

    check_translations(youth_service, youth_data)

    assert youth_service.client_ids.count() == 2
    assert youth_service.client_ids.filter(client_id="youth_client_1").exists()
    assert youth_service.client_ids.filter(client_id="youth_client_2").exists()

    expected_youth_fields = set(AllowedDataField.objects.filter(field_name__in=youth_data["allowed_data_fields"]).all())
    assert set(youth_service.allowed_data_fields.all()) == expected_youth_fields

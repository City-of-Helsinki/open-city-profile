import pytest

from profiles.models import AllowedDataFieldsMixin, Profile
from services.models import Service


@pytest.mark.django_db
def test_field_allowed_when_in_always_allow_fields(monkeypatch):
    monkeypatch.setattr(AllowedDataFieldsMixin, "always_allow_fields", ["id"])
    service = Service.objects.create(name="Test Service")

    assert AllowedDataFieldsMixin.is_field_allowed_for_service("id", service) is True


def test_field_allowed_when_service_is_none_and_in_always_allow_fields(monkeypatch):
    monkeypatch.setattr(AllowedDataFieldsMixin, "always_allow_fields", ["id"])

    assert AllowedDataFieldsMixin.is_field_allowed_for_service("id", None) is True


def test_field_not_allowed_when_service_is_not_defined(monkeypatch):
    monkeypatch.setattr(AllowedDataFieldsMixin, "always_allow_fields", [])

    assert AllowedDataFieldsMixin.is_field_allowed_for_service("id", None) is False


@pytest.mark.django_db
def test_field_allowed_when_in_allowed_data_fields(monkeypatch):
    monkeypatch.setattr(Profile, "always_allow_fields", [])
    monkeypatch.setattr(Profile, "allowed_data_fields_map", {"id": ("id",)})
    service = Service.objects.create(name="Test Service")
    service.allowed_data_fields.create(field_name="id")

    assert Profile.is_field_allowed_for_service("id", service) is True


@pytest.mark.django_db
def test_field_not_allowed_when_not_in_allowed_data_fields(monkeypatch):
    monkeypatch.setattr(Profile, "always_allow_fields", [])
    monkeypatch.setattr(Profile, "allowed_data_fields_map", {})
    service = Service.objects.create(name="Test Service")

    assert Profile.is_field_allowed_for_service("id", service) is False

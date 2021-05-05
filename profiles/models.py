import os
import shutil
import uuid
from datetime import timedelta

import reversion
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import models, transaction
from django.utils import timezone
from encrypted_fields import fields
from enumfields import EnumField
from munigeo.models import AdministrativeDivision
from thesaurus.models import Concept

from services.models import ServiceConnection
from users.models import User
from utils.models import (
    NullsToEmptyStringsModel,
    SerializableMixin,
    UUIDModel,
    ValidateOnSaveModel,
)

from .enums import (
    AddressType,
    EmailType,
    PhoneType,
    RepresentationType,
    RepresentativeConfirmationDegree,
)
from .fields import CallableHashKeyEncryptedSearchField
from .validators import validate_visible_latin_characters_only


def get_user_media_folder(instance, filename):
    return "%s/profile_images/%s" % (instance.user.uuid, filename)


class OverwriteStorage(FileSystemStorage):
    """
    Custom storage that deletes previous profile images
    by deleting the /profiles_images/ folder
    """

    def get_available_name(self, name, max_length=None):
        dir_name, file_name = os.path.split(name)
        if self.exists(dir_name):
            shutil.rmtree(os.path.join(settings.MEDIA_ROOT, dir_name))
        return name


@reversion.register()
class LegalRelationship(models.Model):
    representative = models.ForeignKey(  # "parent"
        "Profile", related_name="representatives", on_delete=models.CASCADE
    )
    representee = models.ForeignKey(  # "child"
        "Profile", related_name="representees", on_delete=models.CASCADE
    )
    type = EnumField(  # ATM only "custodianship"
        RepresentationType, max_length=30, default=RepresentationType.CUSTODY
    )
    confirmation_degree = EnumField(
        RepresentativeConfirmationDegree,
        max_length=30,
        default=RepresentativeConfirmationDegree.NONE,
    )
    expiration = models.DateField(blank=True, null=True)

    def __str__(self):
        return "{} - {}".format(self.representative, self.type)

    def get_notification_context(self):
        return {"relationship": self}


@reversion.register()
class Profile(UUIDModel, SerializableMixin):
    user = models.OneToOneField(User, on_delete=models.PROTECT, null=True, blank=True)
    first_name = models.CharField(max_length=255, blank=True, db_index=True)
    last_name = models.CharField(max_length=255, blank=True, db_index=True)
    nickname = models.CharField(max_length=32, blank=True, db_index=True)
    image = models.ImageField(
        upload_to=get_user_media_folder,
        storage=OverwriteStorage(),
        null=True,
        blank=True,
    )
    language = models.CharField(
        max_length=2,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGES[0][0],
        db_index=True,
    )
    contact_method = models.CharField(
        max_length=30,
        choices=settings.CONTACT_METHODS,
        default=settings.CONTACT_METHODS[0][0],
    )
    concepts_of_interest = models.ManyToManyField(Concept, blank=True)
    divisions_of_interest = models.ManyToManyField(AdministrativeDivision, blank=True)

    legal_relationships = models.ManyToManyField(
        "self", through=LegalRelationship, symmetrical=False
    )
    serialize_fields = (
        {"name": "first_name"},
        {"name": "last_name"},
        {"name": "nickname"},
        {"name": "language"},
        {"name": "contact_method"},
        {"name": "sensitivedata"},
        {"name": "emails"},
        {"name": "phones"},
        {"name": "addresses"},
        {"name": "service_connections"},
        {"name": "subscriptions"},
    )
    audit_log = True

    def resolve_profile(self):
        return self

    def get_primary_email(self):
        return Email.objects.get(profile=self, primary=True)

    def get_primary_email_value(self):
        try:
            return self.get_primary_email().email
        except Email.DoesNotExist:
            return None

    def get_primary_phone_value(self):
        try:
            return self.phones.get(primary=True).phone
        except Phone.DoesNotExist:
            return None

    def save(self, *args, **kwargs):
        if (
            self._state.adding  # uuid pk forces us to do this, since self.pk is True
            and not (self.first_name and self.last_name)
            and self.user
        ):
            self.first_name = self.user.first_name or self.first_name
            self.last_name = self.user.last_name or self.last_name
        super().save(*args, **kwargs)

    def __str__(self):
        if self.user:
            return "{} {} ({})".format(self.first_name, self.last_name, self.user.uuid)
        elif self.first_name and self.last_name:
            return "{} {}".format(self.first_name, self.last_name)
        else:
            return str(self.id)

    @classmethod
    @transaction.atomic
    def import_customer_data(cls, data, service):
        """
        Imports list of customers of the following shape:
        {
            "customer_id": "123",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "ssn": "123456-1234",
            "address": {
                "address": "Example street 1",
                "postal_code": "12321",
                "city": "Gotham City",
            },
            "phones": [
                "040-1234567",
                "091234567"
            ]
        }
        And returns dict where key is the customer_id and value is the UUID of created profile object
        """
        result = {}
        for customer_index, item in enumerate(data):
            try:
                profile = Profile.objects.create(
                    first_name=item.get("first_name", ""),
                    last_name=item.get("last_name", ""),
                )
                ssn = item.get("ssn")
                if ssn:
                    SensitiveData.objects.create(ssn=ssn, profile=profile)
                email = item.get("email", None)
                if email:
                    profile.emails.create(
                        email=email, email_type=EmailType.PERSONAL, primary=True
                    )
                address = item.get("address", None)
                if address:
                    profile.addresses.create(
                        address=address.get("address", ""),
                        postal_code=address.get("postal_code", ""),
                        city=address.get("city", ""),
                        country_code="fi",
                        address_type=AddressType.HOME,
                        primary=True,
                    )
                phones = item.get("phones", ())
                for index, phone in enumerate(phones):
                    profile.phones.create(
                        phone=phone, phone_type=PhoneType.MOBILE, primary=index == 0
                    )
                if service:
                    ServiceConnection.objects.create(
                        profile=profile, service=service, enabled=False,
                    )
                result[item["customer_id"]] = profile.pk
            except Exception as err:
                msg = (
                    "Could not import customer_id: {}, index: {}".format(
                        item["customer_id"], customer_index
                    )
                    if "customer_id" in item
                    else "Could not import unknown customer, index: {}".format(
                        customer_index
                    )
                )
                raise Exception(msg) from err
        return result


def get_national_identification_number_hash_key():
    return settings.SALT_NATIONAL_IDENTIFICATION_NUMBER


class VerifiedPersonalInformation(ValidateOnSaveModel, NullsToEmptyStringsModel):
    profile = models.OneToOneField(
        Profile, on_delete=models.CASCADE, related_name="verified_personal_information"
    )
    first_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="First name(s).",
        validators=[validate_visible_latin_characters_only],
    )
    last_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Last name.",
        validators=[validate_visible_latin_characters_only],
    )
    given_name = fields.EncryptedCharField(
        max_length=100,
        blank=True,
        help_text="The name the person is called with.",
        validators=[validate_visible_latin_characters_only],
    )
    _national_identification_number_data = fields.EncryptedCharField(
        max_length=1024, blank=True,
    )
    national_identification_number = CallableHashKeyEncryptedSearchField(
        hash_key=get_national_identification_number_hash_key,
        encrypted_field_name="_national_identification_number_data",
        blank=True,
        help_text="Finnish national identification number.",
    )
    email = fields.EncryptedCharField(max_length=1024, blank=True, help_text="Email.")
    municipality_of_residence = fields.EncryptedCharField(
        max_length=100,
        blank=True,
        help_text="Official municipality of residence in Finland as a free form text.",
        validators=[validate_visible_latin_characters_only],
    )
    municipality_of_residence_number = fields.EncryptedCharField(
        max_length=4,
        blank=True,
        help_text="Official municipality of residence in Finland as an official number.",
    )

    audit_log = True

    class Meta:
        permissions = [
            (
                "manage_verified_personal_information",
                "Can manage verified personal information",
            ),
        ]


class EncryptedAddress(ValidateOnSaveModel, NullsToEmptyStringsModel):
    street_address = fields.EncryptedCharField(
        max_length=100, blank=True, validators=[validate_visible_latin_characters_only]
    )
    postal_code = fields.EncryptedCharField(max_length=1024, blank=True)
    post_office = fields.EncryptedCharField(
        max_length=100, blank=True, validators=[validate_visible_latin_characters_only]
    )

    class Meta:
        abstract = True

    def is_empty(self):
        return not (self.street_address or self.postal_code or self.post_office)


class VerifiedPersonalInformationPermanentAddress(EncryptedAddress):
    RELATED_NAME = "permanent_address"

    verified_personal_information = models.OneToOneField(
        VerifiedPersonalInformation,
        on_delete=models.CASCADE,
        related_name=RELATED_NAME,
    )

    audit_log = True

    def resolve_profile(self):
        return self.verified_personal_information.profile


class VerifiedPersonalInformationTemporaryAddress(EncryptedAddress):
    RELATED_NAME = "temporary_address"

    verified_personal_information = models.OneToOneField(
        VerifiedPersonalInformation,
        on_delete=models.CASCADE,
        related_name=RELATED_NAME,
    )

    audit_log = True

    def resolve_profile(self):
        return self.verified_personal_information.profile


class VerifiedPersonalInformationPermanentForeignAddress(
    ValidateOnSaveModel, NullsToEmptyStringsModel
):
    RELATED_NAME = "permanent_foreign_address"

    street_address = fields.EncryptedCharField(
        max_length=100,
        blank=True,
        help_text="Street address or whatever is the _first part_ of the address.",
        validators=[validate_visible_latin_characters_only],
    )
    additional_address = fields.EncryptedCharField(
        max_length=100,
        blank=True,
        help_text="Additional address information, perhaps town, county, state, country etc.",
        validators=[validate_visible_latin_characters_only],
    )
    country_code = fields.EncryptedCharField(
        max_length=3, blank=True, help_text="An ISO 3166-1 country code."
    )

    verified_personal_information = models.OneToOneField(
        VerifiedPersonalInformation,
        on_delete=models.CASCADE,
        related_name=RELATED_NAME,
    )

    audit_log = True

    def is_empty(self):
        return not (self.street_address or self.additional_address or self.country_code)

    def resolve_profile(self):
        return self.verified_personal_information.profile


class DivisionOfInterest(models.Model):
    division = models.OneToOneField(
        AdministrativeDivision,
        on_delete=models.CASCADE,
        related_name="division_of_interest",
    )


class SensitiveData(SerializableMixin):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE)
    ssn = fields.EncryptedCharField(max_length=11)
    serialize_fields = ({"name": "ssn"},)
    audit_log = True

    def resolve_profile(self):
        return self.profile if self.pk else None


class Contact(SerializableMixin):
    primary = models.BooleanField(default=False)

    class Meta:
        abstract = True


class Phone(Contact):
    profile = models.ForeignKey(
        Profile, related_name="phones", on_delete=models.CASCADE
    )
    phone = models.CharField(max_length=255, null=True, blank=False, db_index=True)
    phone_type = EnumField(
        PhoneType, max_length=32, blank=False, default=PhoneType.MOBILE
    )
    serialize_fields = (
        {"name": "primary"},
        {"name": "phone_type", "accessor": lambda x: getattr(x, "name")},
        {"name": "phone"},
    )


class Email(Contact):
    profile = models.ForeignKey(
        Profile, related_name="emails", on_delete=models.CASCADE
    )
    email = models.EmailField(max_length=254, blank=False, db_index=True)
    email_type = EnumField(
        EmailType, max_length=32, blank=False, default=EmailType.PERSONAL
    )
    verified = models.BooleanField(default=False)

    class Meta:
        ordering = ["-primary"]

    serialize_fields = (
        {"name": "primary"},
        {"name": "email_type", "accessor": lambda x: getattr(x, "name")},
        {"name": "email"},
    )

    def clean(self):
        super().clean()

        if not self.primary:
            return

        existing_primary_emails = Email.objects.filter(
            profile=self.profile, primary=True,
        )
        if self.pk:
            existing_primary_emails.exclude(pk=self.pk)
        if existing_primary_emails.exists():
            raise ValidationError("Primary email already exists")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Address(Contact):
    profile = models.ForeignKey(
        Profile, related_name="addresses", on_delete=models.CASCADE
    )
    address = models.CharField(max_length=128, blank=False)
    postal_code = models.CharField(max_length=32, blank=False)
    city = models.CharField(max_length=64, blank=False)
    country_code = models.CharField(max_length=2, blank=False)
    address_type = EnumField(
        AddressType, max_length=32, blank=False, default=AddressType.HOME
    )
    serialize_fields = (
        {"name": "primary"},
        {"name": "address_type", "accessor": lambda x: getattr(x, "name")},
        {"name": "address"},
        {"name": "postal_code"},
        {"name": "city"},
        {"name": "country_code"},
    )


class ClaimToken(models.Model):
    profile = models.ForeignKey(
        Profile, related_name="claim_tokens", on_delete=models.CASCADE
    )
    token = models.CharField(
        max_length=36, blank=True, default=uuid.uuid4, editable=False
    )
    expires_at = models.DateTimeField(null=True, blank=True)


def _default_temporary_read_access_token_validity_duration():
    return timedelta(
        minutes=settings.TEMPORARY_PROFILE_READ_ACCESS_TOKEN_VALIDITY_MINUTES
    )


class TemporaryReadAccessToken(models.Model):
    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="read_access_tokens"
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(default=timezone.now, blank=False)
    validity_duration = models.DurationField(
        default=_default_temporary_read_access_token_validity_duration, blank=False
    )

    def expires_at(self):
        return self.created_at + self.validity_duration

    def __str__(self):
        return f"{self.token} ({self.expires_at()})"

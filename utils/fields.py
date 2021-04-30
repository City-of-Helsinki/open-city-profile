import hashlib

from django.db import models
from encrypted_fields.fields import (
    EncryptedCharField,
    is_hashed_already,
    SEARCH_HASH_PREFIX,
    SearchField,
)


class NoneToEmptyValueMixin(models.Field):
    def clean(self, value, model_instance):
        if value is None:
            value = ""  # TODO should this insert the new value to the model?
        return super().clean(value, model_instance)

    def pre_save(self, model_instance, add):
        value = super().pre_save(model_instance, add)
        if value is None:
            value = ""  # TODO should this insert the new value to the model?
        return value


class NonNullCharField(models.CharField, NoneToEmptyValueMixin):
    """CharField that automatically turns nulls into empty strings"""


class NonNullEncryptedCharField(EncryptedCharField, NoneToEmptyValueMixin):
    """EncryptedCharField that automatically turns nulls into empty strings"""


class CallableHashKeyEncryptedSearchField(SearchField):
    """encrypted_fields.fields.SearchField but modified to support callable hash_key"""

    def get_prep_value(self, value):
        if value is None:
            return value
        # coerce to str before encoding and hashing
        # NOTE: not sure what happens when the str format for date/datetime is changed??
        value = str(value)

        if is_hashed_already(value):
            # if we have hashed this previously, don't do it again
            return value

        # Callable hash key custom code start
        if callable(self.hash_key):
            hash_key = self.hash_key()
        else:
            hash_key = self.hash_key
        # Callable hash key custom code end

        v = value + hash_key
        return SEARCH_HASH_PREFIX + hashlib.sha256(v.encode()).hexdigest()


class NonNullCallableHashKeyEncryptedSearchField(
    CallableHashKeyEncryptedSearchField, NoneToEmptyValueMixin
):
    """CallableHashKeyEncryptedSearchField that automatically turns nulls into empty strings"""

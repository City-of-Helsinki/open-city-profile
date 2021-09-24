import hashlib

from django.db import models
from encrypted_fields import fields


class NullToEmptyValueMixin(models.Field):
    def to_python(self, value):
        value = super().to_python(value)
        if value is None:
            value = ""
        return value

    def pre_save(self, model_instance, add):
        value = super().pre_save(model_instance, add)
        if value is None:
            value = ""
            setattr(model_instance, self.attname, value)
        return value


class CallableHashKeyEncryptedSearchField(fields.SearchField):
    """encrypted_fields.fields.SearchField but modified to support callable hash_key"""

    def get_prep_value(self, value):
        if value is None:
            return value
        # coerce to str before encoding and hashing
        # NOTE: not sure what happens when the str format for date/datetime is changed??
        value = str(value)

        if fields.is_hashed_already(value):
            # if we have hashed this previously, don't do it again
            return value

        # Callable hash key custom code start
        if callable(self.hash_key):
            hash_key = self.hash_key()
        else:
            hash_key = self.hash_key
        # Callable hash key custom code end

        v = value + hash_key
        return fields.SEARCH_HASH_PREFIX + hashlib.sha256(v.encode()).hexdigest()


class NullToEmptyCharField(NullToEmptyValueMixin, models.CharField):
    """CharField with automatic null-to-empty-string functionality"""


class NullToEmptyEncryptedCharField(NullToEmptyValueMixin, fields.EncryptedCharField):
    """EncryptedCharField with automatic null-to-empty-string functionality"""


class NullToEmptyEncryptedSearchField(
    NullToEmptyValueMixin, CallableHashKeyEncryptedSearchField
):
    """EncryptedSearchField with automatic null-to-empty-string functionality"""

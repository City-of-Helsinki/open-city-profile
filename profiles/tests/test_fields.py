from encrypted_fields.fields import SearchField

from profiles.fields import CallableHashKeyEncryptedSearchField


def test_callable_hash_key():
    """Test that the custom get_prep_value returns the same result
    with a string and with a callable hash_key"""
    test_hash_key = "testing"

    def get_test_hash_key():
        return test_hash_key

    test_value = "test value"

    return_values = [
        SearchField(
            encrypted_field_name="insignificant", hash_key=test_hash_key
        ).get_prep_value(test_value),
        CallableHashKeyEncryptedSearchField(
            encrypted_field_name="insignificant", hash_key=test_hash_key
        ).get_prep_value(test_value),
        CallableHashKeyEncryptedSearchField(
            encrypted_field_name="insignificant", hash_key=get_test_hash_key
        ).get_prep_value(test_value),
    ]

    assert len(set(return_values)) == 1, f"Values should be the same {return_values}"

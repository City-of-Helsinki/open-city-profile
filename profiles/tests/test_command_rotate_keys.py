import io
import math

import pytest
from django.core.management import CommandError, call_command
from django.db.models import Model

from profiles.management.commands.rotate_keys import Command as RotateKeysCommand
from profiles.models import (
    ClaimToken,
    EncryptedAddress,
    SensitiveData,
    VerifiedPersonalInformation,
    VerifiedPersonalInformationPermanentAddress,
    VerifiedPersonalInformationPermanentForeignAddress,
    VerifiedPersonalInformationTemporaryAddress,
)
from profiles.tests.factories import (
    SensitiveDataFactory,
    VerifiedPersonalInformationFactory,
)

OLD_ENCRYPTION_KEY = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
NEW_ENCRYPTION_KEY = "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"


@pytest.fixture(autouse=True)
def setup(settings):
    # Need at least two encryption keys for the checks to pass.
    settings.FIELD_ENCRYPTION_KEYS = [NEW_ENCRYPTION_KEY, OLD_ENCRYPTION_KEY]


@pytest.fixture
def all_encrypted_models() -> list[Model]:
    # NOTE: Not meant to be an exhaustive list of all models with encryption
    # fields on them, but should include everything that we test against.
    return [
        SensitiveData,
        VerifiedPersonalInformation,
        VerifiedPersonalInformationPermanentAddress,
        VerifiedPersonalInformationPermanentForeignAddress,
        VerifiedPersonalInformationTemporaryAddress,
    ]


@pytest.fixture
def reset_field_encryption_keys(settings, all_encrypted_models):
    """
    Set the FIELD_ENCRYPTION_KEYS and reset the encryption keys for all
    encrypted models' encrypted fields.

    The encryption keys are set at field level on a cached property, so
    they need to forcefully reset to apply any encryption key changes.
    """

    def _func(*keys):
        settings.FIELD_ENCRYPTION_KEYS = list(keys)
        keys = None
        for model in all_encrypted_models:
            for field in model._meta.get_fields(include_parents=True):
                if hasattr(field, "keys") and field.keys:
                    # Delete the cached keys
                    del field.keys
                    # Cache the keys again and store it.
                    # NOTE: If a model has more than one encrypted field,
                    # this will be overwritten. This should be good enough
                    # for our purposes; we mainly want to get the encryption
                    # keys from *a* field.
                    keys = field.keys
        return keys

    return _func


@pytest.fixture
def assert_all_encryption_keys_equals(all_encrypted_models):
    """
    Assert that encryption keys on all encrypted fields on models
    defined in all_encrypted_models match with the expected value.
    """

    def _func(expected_keys: list[str]):
        for model in all_encrypted_models:
            for field in model._meta.get_fields(include_parents=True):
                if hasattr(field, "keys"):
                    assert field.keys
                    assert field.keys == expected_keys

    return _func


@pytest.fixture
def command():
    """
    Set up rotate keys command.

    NOTE: This fixture doesn't work with capsys, has to do with
    how stdout/stderr is handled in Django management commands.
    If you need to capture the output, capture it using command's
    stdout/stderr. For example:

        command.stdout = io.StringIO()
        command.stderr = io.StringIO()
        # ... do stuff ...
        out = command.stdout.getvalue()
        err = command.stderr.getvalue()
        assert "foo" in out
        assert "bar" in err
    """
    command = RotateKeysCommand()
    command.dry_run = False
    return command


@pytest.fixture
def auto_yes(monkeypatch):
    """Just say yes to any user prompts."""
    monkeypatch.setattr("builtins.input", lambda *_, **__: "y")


@pytest.mark.django_db(transaction=True)
def test_command_happy_day(
    auto_yes,
    reset_field_encryption_keys,
    assert_all_encryption_keys_equals,
    all_encrypted_models,
):
    """
    A happy day scenario with transaction operations enabled.
    """

    # Create some encrypted data.
    reset_field_encryption_keys(OLD_ENCRYPTION_KEY)
    SensitiveDataFactory.create_batch(50)
    VerifiedPersonalInformationFactory.create_batch(101)

    # Add a new key.
    new_keys = reset_field_encryption_keys(
        NEW_ENCRYPTION_KEY,
        OLD_ENCRYPTION_KEY,
    )

    assert_all_encryption_keys_equals(new_keys)

    # Call the command with a batch size that better matches our sample size (default is 1000).
    call_command("rotate_keys", batch_size=10)

    # Delete the old key, leaving only the new key.
    new_keys = reset_field_encryption_keys(NEW_ENCRYPTION_KEY)
    assert_all_encryption_keys_equals(new_keys)

    # These should NOT cause any errors.
    for model in all_encrypted_models:
        list(model.objects.all())

    # Try the other way around and use the old key instead.
    new_keys = reset_field_encryption_keys(OLD_ENCRYPTION_KEY)
    assert_all_encryption_keys_equals(new_keys)

    # These SHOULD cause a ValueError.
    for model in all_encrypted_models:
        with pytest.raises(ValueError, match="AES Key incorrect or data is corrupted"):
            list(model.objects.all())


@pytest.mark.django_db
def test_command_dry_run_mode(
    auto_yes,
    reset_field_encryption_keys,
    all_encrypted_models,
):
    """
    A happy day scenario with dry run enabled.
    """

    # Create some encrypted data.
    reset_field_encryption_keys(OLD_ENCRYPTION_KEY)
    SensitiveDataFactory.create_batch(50)
    VerifiedPersonalInformationFactory.create_batch(101)

    # Add a new key.
    reset_field_encryption_keys(
        NEW_ENCRYPTION_KEY,
        OLD_ENCRYPTION_KEY,
    )

    # Call the command with a smaller batch size, dry run enabled and capture stdout.
    out = io.StringIO()
    call_command("rotate_keys", batch_size=10, dry_run=True, stdout=out)

    # Should inform the user that we're running in dry run mode.
    assert "Running with --dry-run option - no changes will be made" in out.getvalue()

    # No changes should've been made, so only the old encryption key should work.
    reset_field_encryption_keys(OLD_ENCRYPTION_KEY)
    for model in all_encrypted_models:
        list(model.objects.all())
    reset_field_encryption_keys(NEW_ENCRYPTION_KEY)
    for model in all_encrypted_models:
        with pytest.raises(ValueError, match="AES Key incorrect or data is corrupted"):
            list(model.objects.all())


@pytest.mark.django_db
def test_command_non_interactive_mode(monkeypatch):
    """
    Non-interactive mode (--no-input/--noinput) skips prompts and
    attempts to rotate the keys.
    """

    # Mock out the actual rotation.
    def mock_rotate_keys_for_model(*_, **__):
        mock_rotate_keys_for_model.call_count += 1

    mock_rotate_keys_for_model.call_count = 0
    monkeypatch.setattr(
        RotateKeysCommand, "rotate_keys_for_model", mock_rotate_keys_for_model
    )

    out = io.StringIO()
    call_command("rotate_keys", "--no-input", stdout=out)

    assert mock_rotate_keys_for_model.call_count > 0
    assert "Do you want to continue? (y/N)" not in out.getvalue()


@pytest.mark.django_db
def test_command_force_mode(monkeypatch, settings, auto_yes):
    """
    Skip non-mission critical checks (i.e. field encryption keys)
    when force mode is enabled and attempt to rotate the keys.

    Note that the model check is *not* skipped on force mode;
    we need to have *something* to update.
    """

    # Mock out the key rotation and the check; don't care what
    # happens inside these, just care whether they're called or not.
    def mock_rotate_keys_for_model(*_, **__):
        mock_rotate_keys_for_model.call_count += 1

    def mock_check_field_encryption_keys(*_, **__):
        mock_check_field_encryption_keys.call_count += 1

    mock_rotate_keys_for_model.call_count = 0
    mock_check_field_encryption_keys.call_count = 0
    monkeypatch.setattr(
        RotateKeysCommand, "rotate_keys_for_model", mock_rotate_keys_for_model
    )
    monkeypatch.setattr(
        RotateKeysCommand,
        "check_field_encryption_keys",
        mock_check_field_encryption_keys,
    )

    # Set FIELD_ENCRYPTION_KEYS empty, this should cause issues if something
    # isn't mocked out properly.
    settings.FIELD_ENCRYPTION_KEYS = []

    call_command("rotate_keys", force=True)

    assert mock_check_field_encryption_keys.call_count == 0
    assert mock_rotate_keys_for_model.call_count > 0


@pytest.mark.django_db
def test_rotate_keys_for_model(reset_field_encryption_keys, command):
    reset_field_encryption_keys(OLD_ENCRYPTION_KEY)
    SensitiveDataFactory.create_batch(50)

    # Rotate keys
    reset_field_encryption_keys(
        NEW_ENCRYPTION_KEY,
        OLD_ENCRYPTION_KEY,
    )

    command.rotate_keys_for_model(SensitiveData, batch_size=1000)

    reset_field_encryption_keys(NEW_ENCRYPTION_KEY)

    # This should NOT cause any errors.
    list(SensitiveData.objects.all())

    reset_field_encryption_keys(OLD_ENCRYPTION_KEY)

    # This SHOULD cause a ValueError.
    with pytest.raises(ValueError, match="AES Key incorrect or data is corrupted"):
        list(SensitiveData.objects.all())


@pytest.mark.parametrize("batch_size", [1, 7, 10, 100])
@pytest.mark.django_db
def test_rotate_keys_for_model_batch_size(
    monkeypatch, reset_field_encryption_keys, command, batch_size
):
    # Mock out the actual batch processing, we're only concerned with batching in this test.
    def mock_process_batch(self, model, ids, *_, **__):
        mock_process_batch.call_count += 1
        mock_process_batch.ids.extend(ids)
        return 1

    mock_process_batch.ids = []
    mock_process_batch.call_count = 0
    monkeypatch.setattr(RotateKeysCommand, "process_batch", mock_process_batch)

    # Create some data.
    reset_field_encryption_keys(OLD_ENCRYPTION_KEY)
    obj_count = 10
    SensitiveDataFactory.create_batch(obj_count)
    expected = list(SensitiveData.objects.all().values_list("pk", flat=True))

    reset_field_encryption_keys(
        NEW_ENCRYPTION_KEY,
        OLD_ENCRYPTION_KEY,
    )
    command.rotate_keys_for_model(SensitiveData, batch_size=batch_size)

    assert mock_process_batch.call_count == math.ceil(obj_count / batch_size)
    assert len(mock_process_batch.ids) == len(expected)
    assert set(mock_process_batch.ids) == set(expected)


@pytest.mark.django_db
def test_process_batch(reset_field_encryption_keys, command):
    # Create some data with the old encryption key.
    reset_field_encryption_keys(OLD_ENCRYPTION_KEY)
    SensitiveDataFactory.create_batch(5)
    ids = list(SensitiveData.objects.all().values_list("pk", flat=True))
    ids_to_process = ids[:3]
    ids_to_ignore = ids[3:]

    # Rotate the keys and process the first three items.
    reset_field_encryption_keys(
        NEW_ENCRYPTION_KEY,
        OLD_ENCRYPTION_KEY,
    )
    objects_processed = command.process_batch(SensitiveData, ids_to_process)

    assert objects_processed == len(ids_to_process)

    # The processed objects should decrypt just fine with the new encryption key
    # while the non-processed ones should cause an error.
    reset_field_encryption_keys(NEW_ENCRYPTION_KEY)
    list(SensitiveData.objects.filter(pk__in=ids_to_process))
    with pytest.raises(ValueError, match="AES Key incorrect or data is corrupted"):
        list(SensitiveData.objects.filter(pk__in=ids_to_ignore))

    # Do the same assertion but inverted, with the old encryption key.
    reset_field_encryption_keys(OLD_ENCRYPTION_KEY)
    list(SensitiveData.objects.filter(pk__in=ids_to_ignore))
    with pytest.raises(ValueError, match="AES Key incorrect or data is corrupted"):
        list(SensitiveData.objects.filter(pk__in=ids_to_process))


@pytest.mark.django_db
def test_process_batch_dry_run(reset_field_encryption_keys, command):
    # Enable dry run mode.
    command.dry_run = True

    # Create some data with the old encryption key.
    reset_field_encryption_keys(OLD_ENCRYPTION_KEY)
    SensitiveDataFactory.create_batch(5)
    ids = list(SensitiveData.objects.all().values_list("pk", flat=True))

    # Rotate the keys and process all items.
    reset_field_encryption_keys(
        NEW_ENCRYPTION_KEY,
        OLD_ENCRYPTION_KEY,
    )
    objects_processed = command.process_batch(SensitiveData, ids)

    assert objects_processed == len(ids)

    # No changes should've been made, to the processed objects should
    # decrypt with the old encryption key only.
    reset_field_encryption_keys(OLD_ENCRYPTION_KEY)
    list(SensitiveData.objects.filter(pk__in=ids))

    reset_field_encryption_keys(NEW_ENCRYPTION_KEY)
    with pytest.raises(ValueError, match="AES Key incorrect or data is corrupted"):
        list(SensitiveData.objects.filter(pk__in=ids))


@pytest.mark.parametrize(
    "model",
    (
        SensitiveData,
        VerifiedPersonalInformation,
        VerifiedPersonalInformationPermanentAddress,
        VerifiedPersonalInformationPermanentForeignAddress,
        VerifiedPersonalInformationTemporaryAddress,
    ),
)
def test_find_models_with_encryption_inclusion(command, model):
    """
    Models that find_models_with_encryption should find.

    NOTE: Not an exhaustive list of all the models that should be included.
    """
    models = command.find_models_with_encryption()

    assert model in models


@pytest.mark.parametrize(
    "model",
    (
        ClaimToken,  # No encrypted fields
        EncryptedAddress,  # Abstract model with encrypted fields
    ),
)
def test_find_models_with_encryption_exclusion(command, model):
    """
    Models that find_models_with_encryption should *not* find.

    NOTE: Not an exhaustive list of all the models that should be excluded.
    """
    models = command.find_models_with_encryption()

    assert model not in models


def test_check_field_encryption_keys_raises_error_if_no_keys_set(settings, command):
    settings.FIELD_ENCRYPTION_KEYS = []

    with pytest.raises(CommandError, match="FIELD_ENCRYPTION_KEYS is not set."):
        command.check_field_encryption_keys()


def test_check_field_encryption_keys_raises_error_if_only_single_key_is_set(
    settings, command
):
    settings.FIELD_ENCRYPTION_KEYS = [OLD_ENCRYPTION_KEY]

    with pytest.raises(
        CommandError,
        match="FIELD_ENCRYPTION_KEYS only has a single key; nothing to rotate.",
    ):
        command.check_field_encryption_keys()


def test_check_models_lists_models_in_stdout(command):
    command.stdout = io.StringIO()
    command.check_models([SensitiveData, VerifiedPersonalInformation])

    out = command.stdout.getvalue()
    assert "- SensitiveData" in out
    assert "- VerifiedPersonalInformation" in out


def test_check_models_raises_error_if_no_models_found(command):
    with pytest.raises(CommandError, match="No models with encrypted fields found."):
        command.check_models([])


@pytest.mark.parametrize("input_val", ("y", "Y"))
def test_ask_for_confirmation_passes_on_y(monkeypatch, command, input_val):
    monkeypatch.setattr("builtins.input", lambda *_, **__: input_val)

    command.ask_for_confirmation()


@pytest.mark.parametrize("input_val", ("n", "N", "yes", ""))
def test_ask_for_confirmation_raises_error_on_non_y(monkeypatch, command, input_val):
    monkeypatch.setattr("builtins.input", lambda *_, **__: input_val)

    with pytest.raises(CommandError, match="Operation cancelled"):
        command.ask_for_confirmation()

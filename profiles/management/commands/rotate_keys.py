import itertools

from django.apps import apps
from django.conf import settings
from django.core.management import CommandError
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Model
from encrypted_fields.fields import EncryptedFieldMixin


class Command(BaseCommand):
    help = "Rotate the encryption keys for models with encrypted fields."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making actual changes.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Ignore the checks and force the operation.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Number of records to process in each batch (default: 1000).",
        )
        parser.add_argument(
            "--no-input",
            "--noinput",
            action="store_false",
            dest="interactive",
            help="Tells Django to NOT prompt the user for input of any kind.",
        )

    def handle(self, *args, **options):
        # Set options.
        batch_size = options["batch_size"]
        force = options["force"]
        interactive = options["interactive"]
        self.dry_run = options["dry_run"]

        if self.dry_run:
            self.stdout.write(
                "Running with --dry-run option - no changes will be made",
                self.style.WARNING,
            )

        # Perform checks.
        if not force:
            self.check_field_encryption_keys()
        models = self.find_models_with_encryption()
        self.check_models(models)
        if interactive:
            self.ask_for_confirmation()

        # Do the actual key rotation.
        self.stdout.write("Starting key rotation process...")
        for model in models:
            self.rotate_keys_for_model(model, batch_size=batch_size)

        self.stdout.write(self.style.SUCCESS("Command finished."))

    def check_field_encryption_keys(self):
        if not settings.FIELD_ENCRYPTION_KEYS:
            raise CommandError(
                "FIELD_ENCRYPTION_KEYS is not set. Re-run the command with "
                "--force to run the operation anyway."
            )
        if len(settings.FIELD_ENCRYPTION_KEYS) == 1:
            raise CommandError(
                "FIELD_ENCRYPTION_KEYS only has a single key; nothing to "
                "rotate. Run the command with --force to run the operation "
                "anyway."
            )

    def check_models(self, models: list[Model]):
        if not models:
            raise CommandError("No models with encrypted fields found.")

        self.stdout.write("Found the following models with encrypted fields:")
        for model in models:
            self.stdout.write(f"  - {model.__qualname__}")

    def ask_for_confirmation(self):
        self.stdout.write(
            "This command will rotate all keys, i.e. save each model instance "
            "one by one for the aforementioned models. This can take a while."
        )
        self.stdout.write("Do you want to continue? (y/N): ", ending="")
        confirm = input()
        if confirm.lower() != "y":
            raise CommandError("Operation cancelled.", returncode=0)

    def find_models_with_encryption(self):
        models: list[Model] = list(apps.get_app_config("profiles").get_models())
        models_with_encryption: list[Model] = []
        for model in models:
            # Need to include fields derived from inheritance since some of the
            # models do not have encrypted fields on their own but inherit them instead.
            for field in model._meta.get_fields(include_parents=True):
                if issubclass(type(field), EncryptedFieldMixin):
                    models_with_encryption.append(model)
                    break
        return models_with_encryption

    def rotate_keys_for_model(self, model: Model, *, batch_size: int):
        self.stdout.write(f"Rotating keys for {model.__name__}...")

        # Get all of the current model instance IDs to get a snapshot of all the
        # current rows in the database so we know for sure what needs updating.
        all_ids = list(model.objects.all().values_list("pk", flat=True))
        objects_processed = 0

        for ids in itertools.batched(all_ids, batch_size):
            objects_processed += self.process_batch(model, ids)

            self.stdout.write(
                f"  {objects_processed}/{len(all_ids)} {model.__name__} "
                "instances processed"
            )

    def process_batch(self, model: Model, ids: list):
        qs = model.objects.select_for_update().filter(id__in=ids)
        objects_processed = 0
        with transaction.atomic():
            for obj in qs:
                if not self.dry_run:
                    obj.save()
                objects_processed += 1
        return objects_processed

from django.db import models
from parler.models import TranslatableModel, TranslatedFields


class TranslatedModel(TranslatableModel):
    non_translated_field = models.CharField(max_length=100)
    translations = TranslatedFields(translated_field=models.CharField(max_length=100))


class NonTranslatedModel(models.Model):
    non_translated_field = models.CharField(max_length=100)

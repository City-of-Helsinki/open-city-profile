from datetime import date

import reversion
from django import forms
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.forms import SelectMultiple

from profiles.models import Profile

from .consts import GENDERS, ILLNESSES, LANGUAGES


def calculate_expiration():
    # Membership always expires at the end of the season (30.6.).
    # Signups before May expire in the summer of the same year, others next year.
    today = date.today()
    return date(year=today.year + 1 if today.month > 4 else today.year, month=6, day=30)


class ChoiceArrayField(ArrayField):
    """
    A field that allows us to store an array of choices.
    Uses Django's Postgres ArrayField and a MultipleChoiceField for its formfield.
    Adapted from https://gist.github.com/danni/f55c4ce19598b2b345ef
    """

    def formfield(self, **kwargs):
        defaults = {
            "form_class": forms.MultipleChoiceField,
            "choices": self.base_field.choices,
            "widget": SelectMultiple,
        }
        defaults.update(kwargs)
        return super(ArrayField, self).formfield(**defaults)


@reversion.register()
class YouthProfile(models.Model):
    # Required info
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE)
    ssn = models.CharField(max_length=11)  # TODO ssn validation?
    school_name = models.CharField(max_length=128)
    school_class = models.CharField(max_length=10)
    expiration = models.DateField(default=calculate_expiration)

    # Optional info
    preferred_language = models.CharField(
        max_length=32, choices=LANGUAGES, default=LANGUAGES[0][0]
    )
    volunteer_info = models.TextField(blank=True)
    gender = models.CharField(max_length=32, choices=GENDERS, blank=True)
    illnesses = ChoiceArrayField(
        base_field=models.CharField(max_length=32, choices=ILLNESSES),
        size=4,
        null=True,
        blank=True,
    )
    allergies = models.TextField(blank=True)
    notes = models.TextField(
        blank=True
    )  # For documenting e.g. restrictions on gaming or premises

    def __str__(self):
        return "{} {} ({})".format(
            self.profile.user.first_name,
            self.profile.user.last_name,
            self.profile.user.uuid,
        )

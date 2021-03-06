from django.forms.models import inlineformset_factory
from django.urls import reverse

from ..admin import EmailFormSet
from ..enums import EmailType
from ..models import Email, Profile
from .factories import ProfileFactory


def test_profile_should_have_exactly_one_primary_email(profile):
    email_formset = inlineformset_factory(
        Profile, Email, formset=EmailFormSet, fields=["email", "email_type", "primary"]
    )
    data = {
        "emails-TOTAL_FORMS": "1",
        "emails-INITIAL_FORMS": "0",
        "emails-MAX_NUM_FORMS": "",
        "emails-0-email": "test@example.com",
        "emails-0-email_type": EmailType.NONE,
        "emails-0-primary": True,
    }
    formset = email_formset(data, prefix="emails", instance=profile)
    assert formset.is_valid()


def test_profile_should_be_valid_with_no_primary_email(profile):
    email_formset = inlineformset_factory(
        Profile, Email, formset=EmailFormSet, fields=["email", "email_type", "primary"]
    )
    data = {
        "emails-TOTAL_FORMS": "1",
        "emails-INITIAL_FORMS": "0",
        "emails-MAX_NUM_FORMS": "",
        "emails-0-email": "test@example.com",
        "emails-0-email_type": EmailType.NONE,
        "emails-0-primary": False,
    }
    formset = email_formset(data, prefix="emails", instance=profile)
    assert formset.is_valid()


def test_profile_should_not_be_valid_with_two_or_more_primary_emails(profile):
    email_formset = inlineformset_factory(
        Profile, Email, formset=EmailFormSet, fields=["email", "email_type", "primary"]
    )
    data = {
        "emails-TOTAL_FORMS": "2",
        "emails-INITIAL_FORMS": "0",
        "emails-MAX_NUM_FORMS": "",
        "emails-0-email": "test1@example.com",
        "emails-0-email_type": EmailType.NONE,
        "emails-0-primary": True,
        "emails-1-email": "test2@example.com",
        "emails-1-email_type": EmailType.NONE,
        "emails-1-primary": True,
    }
    formset = email_formset(data, prefix="emails", instance=profile)
    assert not formset.is_valid()


def test_admin_profile_change_view_query_count_not_too_big(
    admin_client, django_assert_max_num_queries, profile
):
    view_profile_url = reverse("admin:profiles_profile_change", args=(profile.pk,))

    with django_assert_max_num_queries(50):
        admin_client.get(view_profile_url)

    # Add 100 profiles
    ProfileFactory.create_batch(100)

    with django_assert_max_num_queries(50):
        admin_client.get(view_profile_url)

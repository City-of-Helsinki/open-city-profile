from django.db import transaction
from subscriptions.models import SubscriptionType, SubscriptionTypeCategory

SUBSCRIPTION_TYPE_CATEGORIES = (
    {
        "code": "COVID_COMMUNICATION",
        "translations": (
            {"locale": "fi", "value": "Viestintä"},
            {"locale": "sv", "value": "Viestintä_SV"},
            {"locale": "en", "value": "Viestintä_EN"},
        ),
        "subscription_types": (
            {
                "code": "COVID_OFFICIAL_NOTIFICATIONS",
                "translations": (
                    {
                        "locale": "fi",
                        "value": "Haluan virallisia tiedotteita viimeisimmästä covid19-tilanteesta",
                    },
                    {
                        "locale": "sv",
                        "value": "Haluan virallisia tiedotteita viimeisimmästä covid19-tilanteesta_SV",
                    },
                    {
                        "locale": "en",
                        "value": "Haluan virallisia tiedotteita viimeisimmästä covid19-tilanteesta_EN",
                    },
                ),
            },
            {
                "code": "COVID_UNOFFICIAL_NOTIFICATIONS",
                "translations": (
                    {
                        "locale": "fi",
                        "value": "Haluan epävirallisia tiedotteita viimeisimmästä covid19-tilanteesta",
                    },
                    {
                        "locale": "sv",
                        "value": "Haluan epävirallisia tiedotteita viimeisimmästä covid19-tilanteesta_SV",
                    },
                    {
                        "locale": "en",
                        "value": "Haluan epävirallisia tiedotteita viimeisimmästä covid19-tilanteesta_EN",
                    },
                ),
            },
        ),
    },
    {
        "code": "COVID_VOLUNTEERING",
        "translations": (
            {"locale": "fi", "value": "Vapaaehtoistyö"},
            {"locale": "sv", "value": "Vapaaehtoistyö_SV"},
            {"locale": "en", "value": "Vapaaehtoistyö_EN"},
        ),
        "subscription_types": (
            {
                "code": "COVID_VOLUNTEERING",
                "translations": (
                    {
                        "locale": "fi",
                        "value": "Olen halukas tekemään vapaaehtoistyötä liittyen kehittyvään tilanteeseen",
                    },
                    {
                        "locale": "sv",
                        "value": "Olen halukas tekemään vapaaehtoistyötä liittyen kehittyvään tilanteeseen_SV",
                    },
                    {
                        "locale": "en",
                        "value": "Olen halukas tekemään vapaaehtoistyötä liittyen kehittyvään tilanteeseen_EN",
                    },
                ),
            },
        ),
    },
)


@transaction.atomic
def generate_subscription_types():
    """Generates subscription types and categories if needed."""
    for cat in SUBSCRIPTION_TYPE_CATEGORIES:
        category = SubscriptionTypeCategory.objects.filter(code=cat["code"]).first()
        if not category:
            category = SubscriptionTypeCategory.objects.create(code=cat["code"])
            for translation in cat["translations"]:
                category.set_current_language(translation["locale"])
                category.label = translation["value"]
            category.save()

        for sub_type in cat["subscription_types"]:
            subscription_type = SubscriptionType.objects.filter(
                code=sub_type["code"]
            ).first()
            if not subscription_type:
                subscription_type = SubscriptionType.objects.create(
                    subscription_type_category=category, code=sub_type["code"]
                )
                for translation in sub_type["translations"]:
                    subscription_type.set_current_language(translation["locale"])
                    subscription_type.label = translation["value"]
                subscription_type.save()

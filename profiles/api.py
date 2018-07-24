import logging

from django.http import Http404
from django.utils.translation import ugettext_lazy as _
from parler_rest.serializers import TranslatableModelSerializer, TranslatedFieldsField
from rest_framework import serializers, generics, viewsets, permissions
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.relations import RelatedField
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from thesaurus.models import Concept

from profiles.models import Profile

logger = logging.getLogger(__name__)


class TranslatedModelSerializer(TranslatableModelSerializer):
    translations = TranslatedFieldsField()

    def to_representation(self, obj):
        ret = super(TranslatedModelSerializer, self).to_representation(obj)
        if obj is None:
            return ret
        return self.translated_fields_to_representation(obj, ret)

    def translated_fields_to_representation(self, obj, ret):
        translated_fields = {}

        for lang_key, trans_dict in ret.pop('translations', {}).items():

            for field_name, translation in trans_dict.items():
                if not field_name in translated_fields:
                    translated_fields[field_name] = {lang_key: translation}
                else:
                    translated_fields[field_name].update({lang_key: translation})

        ret.update(translated_fields)

        return ret


class ConceptRelatedField(RelatedField):
    default_error_messages = {
        'required': _('This field is required.'),
        'does_not_exist': _('Invalid prefix and/or code in "{value}" - object does not exist.'),
        'incorrect_type': _('Incorrect type. Expected concept string in format "prefix:code", received {data_type}.'),
    }
    queryset = Concept.objects.all()

    def to_representation(self, value):
        return '{}:{}'.format(value.vocabulary.prefix, value.code)

    def to_internal_value(self, data):
        (prefix, code) = data.split(':')

        if not prefix or not code:
            self.fail('incorrect_type')

        try:
            return Concept.objects.get(vocabulary__prefix=prefix, code=code)
        except Concept.DoesNotExist:
            self.fail('does_not_exist', value=data)
        except (TypeError, ValueError):
            self.fail('incorrect_type', data_type=type(data).__name__)


class ProfileSerializer(serializers.ModelSerializer):
    concepts_of_interest = ConceptRelatedField(many=True)

    class Meta:
        exclude = ['id', 'user']
        model = Profile


class ProfileViewSet(generics.RetrieveUpdateAPIView, viewsets.ModelViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    renderer_classes = [JSONRenderer, BrowsableAPIRenderer]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def get_object(self):
        try:
            profile = self.get_queryset().get(user=self.request.user)
        except Profile.DoesNotExist:
            # TODO: create profiles when the user is created, not here.
            profile = Profile.objects.create(user=self.request.user)
        except (TypeError, ValueError):
            raise Http404

        return profile


class InterestConceptSerializer(TranslatedModelSerializer):
    vocabulary = serializers.SlugRelatedField(
        read_only=True,
        slug_field='prefix'
    )

    class Meta:
        model = Concept
        fields = ['vocabulary', 'code', 'translations',]


class InterestConceptViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Concept.objects.all()
    serializer_class = InterestConceptSerializer

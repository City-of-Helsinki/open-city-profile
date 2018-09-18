import logging

from django.utils.translation import ugettext_lazy as _
from munigeo.models import AdministrativeDivision
from parler_rest.serializers import TranslatableModelSerializer, TranslatedFieldsField
from rest_framework import serializers, generics, viewsets, permissions
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.exceptions import APIException
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


class ProfileAlreadyExists(APIException):
    status_code = 409
    default_detail = _('The profile for this user already exists.')
    default_code = 'profile_already_exists'


class ProfileSerializer(serializers.ModelSerializer):
    concepts_of_interest = ConceptRelatedField(many=True)
    divisions_of_interest = serializers.SlugRelatedField(
        queryset=AdministrativeDivision.objects.all(),
        many=True, slug_field='ocd_id'
    )

    class Meta:
        exclude = ['id', 'user']
        model = Profile


class ProfileViewSet(generics.RetrieveUpdateAPIView, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    lookup_field = 'user__uuid'
    renderer_classes = [JSONRenderer, BrowsableAPIRenderer]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        queryset = Profile.objects.filter(user=self.request.user)

        if queryset.exists():
            raise ProfileAlreadyExists()

        serializer.save(user=self.request.user)


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


class GeoDivisionSerializer(TranslatedModelSerializer):
    type = serializers.SlugRelatedField(read_only=True, slug_field='type')
    children = serializers.SerializerMethodField()

    class Meta:
        model = AdministrativeDivision
        fields = ('type', 'children', 'translations', 'origin_id', 'ocd_id', 'municipality')

    def get_children(self, obj):
        children = obj.children.filter(type__type='sub_district')
        if children.count() <= 1:
            return ''
        serializer = GeoDivisionSerializer(children, many=True, context=self.context)
        return serializer.data


class GeoDivisionViewSet(viewsets.ModelViewSet):
    queryset = AdministrativeDivision.objects.filter(division_of_interest__isnull=False)
    serializer_class = GeoDivisionSerializer

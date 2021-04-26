import uuid

from django.db import models
from django.db.models.fields.reverse_related import OneToOneRel


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class SerializableMixin(models.Model):
    """
    Mixin to add custom serialization for django models in order to get the desired tree of models to
    the downloadable JSON form. It detects relationships automatically (many to many not yet fully
    supported). Check for the example for more details about the structure.

    Attributes need to be defined in the extending model:

    - serialize_fields (required)
        - tuple of dicts:
            - name (required), name of the field or relation that's going to be added to the serialized object
            - accessor (optional), function that is called when value of the field is resolved and it takes the
              actual field value as argument

    Example usage and output:

    class Post(SerializableMixin):
        serialize_fields = (
            { "name": "title" },
            { "name": "content" },
            {
                "name": "created_at",
                "accessor": lambda x: x.strftime("%Y-%m-%d")
            }
            { "name": "comments" },
        )

    class Comment(SerializableMixin):
        serialize_fields = (
            { "name": "text" },
            { "name": "author" },
        )

    Calling serialize() on a single post object generates:

    {
        "key": "POST",
        "children": [
            { "key": "TITLE", "value": "Post about serialization" },
            { "key": "CONTENT", "value": "This is the content of the post" },
            { "key": "CREATED_AT", "value": "2020-02-03" },
            { "key": "COMMENTS", "children": [
                {
                    "key": "COMMENT"
                    "children": [
                        { "key": "TEXT", "value": "I really like this post" },
                        { "key": "AUTHOR", "value": "Mike" }
                    ]
                },
                {
                    "key": "COMMENT"
                    "children": [
                        { "key": "TEXT", "value": "I don't agree with this 100%" },
                        { "key": "AUTHOR", "value": "Maria" }
                    ]
                }
            ]}
        ]
    }
    """

    class SerializableManager(models.Manager):
        def serialize(self):
            return [
                obj.serialize() if hasattr(obj, "serialize") else []
                for obj in self.get_queryset().all()
            ]

    class Meta:
        abstract = True

    objects = SerializableManager()

    def _resolve_field(self, model, field):
        def _resolve_value(data, field):
            if "accessor" in field:
                # call the accessor with value as an argument
                return field["accessor"](getattr(data, field.get("name")))
            else:
                # no accessor, return the value
                return getattr(data, field.get("name"))

        related_types = {item.name: type(item) for item in model._meta.related_objects}
        if field.get("name") in related_types.keys():
            value = (
                getattr(model, field.get("name")).serialize()
                if hasattr(model, field.get("name"))
                and hasattr(getattr(model, field.get("name")), "serialize")
                else None
            )
            # field is a related object, let's serialize more
            if related_types[field.get("name")] == OneToOneRel:
                # do not wrap one-to-one relations into list
                return value
            else:
                return {
                    "key": field.get("name").upper(),
                    "children": value,
                }
        else:
            # concrete field, let's just add the value
            return {
                "key": field.get("name").upper(),
                "value": _resolve_value(model, field),
            }

    def serialize(self):
        return {
            "key": self._meta.model_name.upper(),
            "children": [
                self._resolve_field(self, field)
                for field in self.serialize_fields
                if self._resolve_field(self, field) is not None
            ],
        }


class ValidateOnSaveModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

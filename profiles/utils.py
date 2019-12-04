from graphql_relay.node.node import from_global_id


def create_nested(model, profile, data):
    for add_input in data:
        item = model(profile=profile)
        for field, value in add_input.items():
            if field == "primary" and value is True:
                model.objects.filter(profile=profile).update(primary=False)
            setattr(item, field, value)
        item.save()


def update_nested(model, profile, data):
    for update_input in data:
        id = update_input.pop("id")
        item = model.objects.get(profile=profile, pk=from_global_id(id)[1])
        for field, value in update_input.items():
            if field == "primary" and value is True:
                model.objects.filter(profile=profile).update(primary=False)
            setattr(item, field, value)
        item.save()


def delete_nested(model, profile, data):
    for remove_id in data:
        model.objects.get(profile=profile, pk=from_global_id(remove_id)[1]).delete()

from graphql.pyutils import did_you_mean

_original_max_length = None


def enable_graphql_query_suggestion(enable: bool):
    """Enable or disable graphql query suggestions.

    Adapted from: https://github.com/graphql-python/graphql-core/issues/97#issuecomment-642967670
    """
    global _original_max_length

    if not _original_max_length:
        # Original value is stored mainly to be able to toggle it in tests.
        _original_max_length = did_you_mean.__globals__["MAX_LENGTH"]

    if enable:
        did_you_mean.__globals__["MAX_LENGTH"] = _original_max_length
    else:
        did_you_mean.__globals__["MAX_LENGTH"] = 0

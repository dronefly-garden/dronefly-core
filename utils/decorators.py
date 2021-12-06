"""Decorator utilities."""
from functools import wraps

from ..formatters.discord import MAX_EMBED_NAME_LEN


def make_decorator(function):
    """Make a decorator that has arguments."""

    @wraps(function)
    def wrap_make_decorator(*args, **kwargs):
        if len(args) == 1 and (not kwargs) and callable(args[0]):
            # i.e. called as @make_decorator
            return function(args[0])
        # i.e. called as @make_decorator(*args, **kwargs)
        return lambda wrapped_function: function(wrapped_function, *args, **kwargs)

    return wrap_make_decorator


# Deprecated:


@make_decorator
def format_items_for_embed(function, max_len=MAX_EMBED_NAME_LEN):
    """Format items as delimited list not exceeding Discord length limits."""

    @wraps(function)
    def wrap_format_items_for_embed(*args, **kwargs):
        kwargs["max_len"] = max_len
        return function(*args, **kwargs)

    return wrap_format_items_for_embed

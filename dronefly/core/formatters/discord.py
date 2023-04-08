"""Discord formatters."""
import re

from pyinaturalist.models import Taxon, User

from dronefly.core.formatters.constants import WWW_BASE_URL
from dronefly.core.formatters.generic import format_taxon_name

EMBED_COLOR = 0x90EE90
# From https://discordapp.com/developers/docs/resources/channel#embed-limits
MAX_EMBED_TITLE_LEN = MAX_EMBED_NAME_LEN = 256
MAX_EMBED_DESCRIPTION_LEN = 2048
MAX_EMBED_FIELDS = 25
MAX_EMBED_VALUE_LEN = 1024
MAX_EMBED_FOOTER_LEN = 2048
MAX_EMBED_AUTHOR_LEN = 256
MAX_EMBED_LEN = 6000
# It's not exactly 2**23 due to overhead, but how much less, we can't determine.
# This is a safe value that works for others.
MAX_EMBED_FILE_LEN = 8000000

# TODO: the seed idea here is to act on & render spoilered commands and displays,
#   e.g. `,obs my ||gory observation taxon||`
#   - images would be fetched, then uploaded with spoilers
# SPOILER_PAT = re.compile(r"\|\|")
# DOUBLE_BAR_LIT = "\\|\\|"

_MARKDOWN_ESCAPE_SUBREGEX = "|".join(
    r"\{0}(?=([\s\S]*((?<!\{0})\{0})))".format(c) for c in ("*", "`", "_", "~", "|")
)
_MARKDOWN_ESCAPE_COMMON = r"^>(?:>>)?\s|\[.+\]\(.+\)"
_MARKDOWN_ESCAPE_REGEX = re.compile(
    rf"(?P<markdown>{_MARKDOWN_ESCAPE_SUBREGEX}|{_MARKDOWN_ESCAPE_COMMON})",
    re.MULTILINE,
)
_URL_REGEX = r"(?P<url><[^: >]+:\/[^ >]+>|(?:https?|steam):\/\/[^\s<]+[^<.,:;\"\'\]\s])"
_MARKDOWN_STOCK_REGEX = rf"(?P<markdown>[_\\~|\*`]|{_MARKDOWN_ESCAPE_COMMON})"


def escape_markdown(
    text: str, *, as_needed: bool = False, ignore_links: bool = True
) -> str:
    r"""A helper function that escapes Discord's markdown.

    Parameters
    -----------
    text: :class:`str`
        The text to escape markdown from.
    as_needed: :class:`bool`
        Whether to escape the markdown characters as needed. This
        means that it does not escape extraneous characters if it's
        not necessary, e.g. ``**hello**`` is escaped into ``\*\*hello**``
        instead of ``\*\*hello\*\*``. Note however that this can open
        you up to some clever syntax abuse. Defaults to ``False``.
    ignore_links: :class:`bool`
        Whether to leave links alone when escaping markdown. For example,
        if a URL in the text contains characters such as ``_`` then it will
        be left alone. This option is not supported with ``as_needed``.
        Defaults to ``True``.

    Returns
    --------
    :class:`str`
        The text with the markdown special characters escaped with a slash.

    Taken from https://github.com/Rapptz/discord.py/blob/master/discord/utils.py
    """

    if not as_needed:

        def replacement(match):
            groupdict = match.groupdict()
            is_url = groupdict.get("url")
            if is_url:
                return is_url
            return "\\" + groupdict["markdown"]

        regex = _MARKDOWN_STOCK_REGEX
        if ignore_links:
            regex = f"(?:{_URL_REGEX}|{regex})"
        return re.sub(regex, replacement, text, 0, re.MULTILINE)
    else:
        text = re.sub(r"\\", r"\\\\", text)
        return _MARKDOWN_ESCAPE_REGEX.sub(r"\\\1", text)


def format_taxon_image_embed(
    taxon: Taxon,
):
    """Format taxon as Discord embed dict."""
    embed = {
        "color": EMBED_COLOR,
        "title": taxon.name,
        "url": taxon.url,
        "description": format_taxon_name(taxon),
    }
    default_photo = taxon.default_photo
    if default_photo:
        medium_url = default_photo.medium_url
        if medium_url:
            embed["image"] = {
                "url": medium_url,
            }
            embed["footer"] = {
                "text": default_photo.attribution,
            }
    return embed


def format_user_name(user: User):
    """Format user's display name with Markdown special characters escaped."""
    if user.name:
        return f"{escape_markdown(user.name)} ({escape_markdown(user.login)})"
    return escape_markdown(user.login)


def format_user_url(user: User):
    """Format user's profile url using their login name instead of user id."""
    return f"{WWW_BASE_URL}/people/{user.login}" if user.login else ""


def format_user_link(user: User):
    """Format user's profile link as Markdown."""
    return f"[{format_user_name(user)}]({format_user_url(user)})"

"""Discord formatters."""
from typing import List

from .generic import format_taxon_names as generic_format_taxon_names
from ..models.taxon import Taxon

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


def format_taxon_names(
    taxa: List[Taxon],
    with_term=False,
    names_format="%s",
    max_len=MAX_EMBED_NAME_LEN,
    hierarchy=False,
):
    return generic_format_taxon_names(taxa, with_term, names_format, max_len, hierarchy)

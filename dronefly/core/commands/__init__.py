from enum import Enum
import re
from pyinat import iNatClient
from rich.markdown import Markdown

from ..parsers import NaturalParser
from ..formatters.discord import format_taxon_title, format_taxon_names

RICH_BQ_NEWLINE_PAT = re.compile(r'^(\>.*?)(\n)', re.MULTILINE)

class Format(Enum):
    discord_markdown = 1
    rich = 2

INAT_DEFAULTS = {'locale': 'en', 'preferred_place_id': 1}
# TODO: everything below needs to be broken down into different layers
# handling each thing:
# - Context
#   - user, channel, etc.
#   - affects which settings are passed to inat (e.g. home place for conservation status)
# - Formatters
#    - anything relating to the format belongs down in formatters, not here
#    - e.g. title is marked up right now for console output, but for Discord
#      needs to be put in embed.title and embed.url
#    - being locked into Markdown in the formatters is turning out to be not
#      so great, as rich can only handle CommonMark, leaving us with no way
#      to do strikethrough, etc.
#      - consider using Rich's own markup, e.g. [strike]Invalid name[/strike]
class Commands:
    def __init__(
        self,
        inat_client=iNatClient(default_params=INAT_DEFAULTS),
        format=Format.discord_markdown,
    ):
        self.inat_client = inat_client
        self.parser = NaturalParser()
        self.format = format

    def _parse(self, query_str):
        return self.parser.parse(query_str)

    def taxon(self, *args):
        query = self._parse(' '.join(args))
        # TODO: Handle all query clauses, not just main.terms
        # TODO: Doesn't do any ranking or filtering of results
        main_query_str = " ".join(query.main.terms)
        taxon = self.inat_client.taxa.autocomplete(q=main_query_str, all_names=True).one()
        if taxon:
            taxon.load_full_record()
            taxon_title = '[{title}]({url})'.format(
                title=format_taxon_title(taxon, lang=INAT_DEFAULTS['locale']),
                url=taxon.url,
            )
            taxon_hierarchy = format_taxon_names(taxon.ancestors, hierarchy=True)
            response = ' '.join([taxon_title, taxon_hierarchy])
            if (self.format == Format.rich):
              rich_markdown = re.sub(RICH_BQ_NEWLINE_PAT, r'\1\\\n', response)
              response = Markdown(rich_markdown)
            return response
        return "Nothing found"

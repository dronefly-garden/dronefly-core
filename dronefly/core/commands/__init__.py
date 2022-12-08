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
class Commands:
    # TODO: apply any ctx-specific parameters that may override client defaults
    # - we need a Context class of our own for all of this
    #   - the defaults belong in that class, not here
    #   - the client would be associated with the context, not the command
    def __init__(self, inat_client=iNatClient(default_params=INAT_DEFAULTS), format=Format.discord_markdown):
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
            taxon_name = format_taxon_title(taxon, lang=INAT_DEFAULTS['locale'])
            taxon.load_full_record()
            taxon_hierarchy = format_taxon_names(taxon.ancestors, hierarchy=True)
            response = ' '.join([taxon_name, taxon_hierarchy])
            # TODO: refactor for reuse in other commands
            if (self.format == Format.rich):
              rich_markdown = re.sub(RICH_BQ_NEWLINE_PAT, r'\1\\\n', response)
              response = Markdown(rich_markdown)
            return response
        return "Nothing found"

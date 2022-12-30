from enum import Enum
import re
from rich.markdown import Markdown

from ..clients.inat import iNatClient
from ..parsers import NaturalParser
from ..formatters.discord import format_taxon
from ..models.user import User

RICH_BQ_NEWLINE_PAT = re.compile(r'^(\>.*?)(\n)', re.MULTILINE)

class Format(Enum):
    discord_markdown = 1
    rich = 2

INAT_DEFAULTS = {'locale': 'en', 'preferred_place_id': 1}

class Context:
    author: User = User()

# TODO: everything below needs to be broken down into different layers
# handling each thing:
# - Context
#   - user, channel, etc.
#   - affects which settings are passed to inat (e.g. home place for conservation status)
class Commands:
    # TODO: platform: dronefly.Platform
    # - e.g. discord, commandline, web
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

    def taxon(self, ctx: Context, *args):
        def _pyinat_workarounds(client, taxon, **kwargs):
            # - https://github.com/pyinat/pyinaturalist/issues/447
            status = taxon.conservation_status
            status_name = None
            if status:
                status_name = status.status_name
            # - https://github.com/pyinat/pyinaturalist/issues/448
            matched_term = taxon.matched_term

            # - https://github.com/pyinat/pyinaturalist/issues/446
            # taxon.load_full_record()
            taxon = client.taxa(taxon.id, **kwargs)
            return (taxon, status_name, matched_term)

        query = self._parse(' '.join(args))
        # TODO: Handle all query clauses, not just main.terms
        # TODO: Doesn't do any ranking or filtering of results
        # TODO: Remove workarounds for issues linked below
        main_query_str = " ".join(query.main.terms)
        # - https://github.com/pyinat/pyinaturalist/issues/446
        #   - all_names can be provided via default_params after #446 is fixed
        kwargs = {'all_names': True}

        with self.inat_client.set_ctx(ctx) as client:
            taxon = client.taxa.autocomplete(q=main_query_str, **kwargs).one()
            if not taxon:
                return "Nothing found"
            (
                taxon,
                status_name,
                matched_term,
            ) = _pyinat_workarounds(client, taxon, **kwargs)

        response = format_taxon(
            taxon,
            lang=INAT_DEFAULTS['locale'],
            matched_term=matched_term,
            status_name=status_name,
            with_url=True,
        )
        if (self.format == Format.rich):
            rich_markdown = re.sub(RICH_BQ_NEWLINE_PAT, r'\1\\\n', response)
            response = Markdown(rich_markdown)

        return response

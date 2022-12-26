from enum import Enum
import re
from pyinat import iNatClient
from rich.markdown import Markdown

from ..parsers import NaturalParser
from ..formatters.discord import format_taxon_title, format_taxon_names
from ..formatters.generic import format_taxon_conservation_status, format_taxon_establishment_means
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
# - Formatters
#    - anything relating to the format belongs down in formatters, not here
#    - e.g. title is marked up right now for console output, but for Discord
#      needs to be put in embed.title and embed.url
#    - being locked into Markdown in the formatters is turning out to be not
#      so great, as rich can only handle CommonMark, leaving us with no way
#      to do strikethrough, etc.
#      - consider using Rich's own markup, e.g. [strike]Invalid name[/strike]
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
        query = self._parse(' '.join(args))
        # TODO: Handle all query clauses, not just main.terms
        # TODO: Doesn't do any ranking or filtering of results
        # TODO: Remove workarounds for issues linked below
        main_query_str = " ".join(query.main.terms)
        user = ctx.author
        # - https://github.com/pyinat/pyinaturalist/issues/446
        #   - all_names and preferred_place_id can be provided
        #     via default_params after #446 is fixed
        #   - we'll also need to supplement any default params
        #     on the client with default params from the ctx.user
        params = {'all_names': True}
        if user and user.inat_place_id:
            params['preferred_place_id'] = user.inat_place_id

        taxon = self.inat_client.taxa.autocomplete(q=main_query_str, **params).one()

        if not taxon:
            return "Nothing found"

        # - https://github.com/pyinat/pyinaturalist/issues/447
        status = taxon.conservation_status
        status_name = None
        if status:
            status_name = status.status_name
        # - https://github.com/pyinat/pyinaturalist/issues/448
        matched_term = taxon.matched_term

        # - https://github.com/pyinat/pyinaturalist/issues/446
        # taxon.load_full_record()
        taxon = self.inat_client.taxa(taxon.id, **params)

        # TODO: move the following into formatters as format_taxon_embed()
        # - kept here for now, as we have temporarily complicated the
        #   call signatures to pass extra arugments for the various
        #   outstanding pyinat issues
        taxon_title = format_taxon_title(taxon, lang=INAT_DEFAULTS['locale'], matched_term=matched_term, with_url=True)
        response = taxon_title
        if status:
            response += ' \\\n' + format_taxon_conservation_status(status, brief=True, status_name=status_name)
        means = taxon.establishment_means
        if means:
            response += ' \\\n' + format_taxon_establishment_means(means)
        response += ' ' + format_taxon_names(taxon.ancestors, hierarchy=True)
        if (self.format == Format.rich):
            rich_markdown = re.sub(RICH_BQ_NEWLINE_PAT, r'\1\\\n', response)
            response = Markdown(rich_markdown)

        return response

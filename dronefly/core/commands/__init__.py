from enum import Enum
import re

from attrs import define
from rich.markdown import Markdown

from ..clients.inat import iNatClient
from ..constants import INAT_DEFAULTS, INAT_USER_DEFAULT_PARAMS
from ..parsers import NaturalParser
from ..formatters.generic import ObservationFormatter, TaxonFormatter
from ..models.user import User


RICH_BQ_NEWLINE_PAT = re.compile(r"^(\>.*?)(\n)", re.MULTILINE)
RICH_NEWLINE = " \\\n"


class Format(Enum):
    discord_markdown = 1
    rich = 2


@define
class Context:
    """A Dronefly command context."""

    author: User = User()

    def get_inat_user_default(self, inat_param: str):
        """Return iNat API default for user param default, if any, otherwise global default."""
        if inat_param not in INAT_USER_DEFAULT_PARAMS:
            return None
        if self.author:
            default = getattr(self.author, inat_param, None) or INAT_DEFAULTS.get(
                inat_param
            )
        else:
            default = INAT_DEFAULTS.get(inat_param)
        return default

    def get_inat_defaults(self):
        """Return all iNat API defaults."""
        defaults = {**INAT_DEFAULTS}
        for user_param, inat_param in INAT_USER_DEFAULT_PARAMS.items():
            default = self.get_inat_user_default(user_param)
            if default is not None:
                defaults[inat_param] = default
        return defaults


# TODO: everything below needs to be broken down into different layers
# handling each thing:
# - Context
#   - user, channel, etc.
#   - affects which settings are passed to inat (e.g. home place for conservation status)
@define
class Commands:
    """A Dronefly command processor."""

    # TODO: platform: dronefly.Platform
    # - e.g. discord, commandline, web

    inat_client: iNatClient = iNatClient()
    parser: NaturalParser = NaturalParser()
    format: Format = Format.discord_markdown

    def _parse(self, query_str):
        return self.parser.parse(query_str)

    def taxon(self, ctx: Context, *args):
        query = self._parse(" ".join(args))
        # TODO: Handle all query clauses, not just main.terms
        # TODO: Doesn't do any ranking or filtering of results
        if not query.main or not query.main.terms:
            return "Not a taxon"
        main_query_str = " ".join(query.main.terms)

        with self.inat_client.set_ctx(ctx) as client:
            taxon = client.taxa.autocomplete(q=main_query_str).one()
            if not taxon:
                return "Nothing found"
            taxon = client.taxa.populate(taxon)

        formatter = TaxonFormatter(
            taxon,
            lang=ctx.get_inat_user_default("inat_lang"),
            with_url=True,
            newline=RICH_NEWLINE,
        )
        response = formatter.format()

        if self.format == Format.rich:
            rich_markdown = re.sub(RICH_BQ_NEWLINE_PAT, r"\1\\\n", response)
            response = Markdown(rich_markdown)

        return response

    def obs(self, ctx: Context, *args):
        query = self._parse(" ".join(args))
        # TODO: Handle all query clauses, not just main.terms
        # TODO: Doesn't do any ranking or filtering of results
        if not query.main or not query.main.terms:
            return "Not a taxon"

        main_query_str = " ".join(query.main.terms)
        with self.inat_client.set_ctx(ctx) as client:
            taxon = client.taxa.autocomplete(q=main_query_str).one()
            if not taxon:
                return "No taxon found"
            obs = client.observations.search(
                user_id=ctx.author.inat_user_id,
                taxon_id=taxon.id,
                limit=1,
                reverse=True,
            ).one()
            if not obs:
                return f"No observations by you found for: {taxon.full_name}"

        taxon_summary = client.observations.taxon_summary(obs.id)
        if obs.community_taxon_id and obs.community_taxon_id != obs.taxon.id:
            community_taxon = client.taxa.from_ids(obs.taxon.id, limit=1).one()
            community_taxon_summary = client.observations.taxon_summary(
                obs.id, community=1
            )
        else:
            community_taxon = taxon
            community_taxon_summary = taxon_summary

        formatter = ObservationFormatter(
            obs,
            taxon_summary=taxon_summary,
            community_taxon=community_taxon,
            community_taxon_summary=community_taxon_summary,
            with_link=True,
        )
        response = formatter.format()

        if self.format == Format.rich:
            rich_markdown = re.sub(RICH_BQ_NEWLINE_PAT, r"\1\\\n", response)
            response = Markdown(rich_markdown)

        return response

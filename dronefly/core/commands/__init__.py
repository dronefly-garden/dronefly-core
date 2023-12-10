from enum import Enum
import re
from typing import Union

from attrs import define
from rich.markdown import Markdown

from ..clients.inat import iNatClient
from ..constants import INAT_DEFAULTS, INAT_USER_DEFAULT_PARAMS, RANK_KEYWORDS

from ..parsers import NaturalParser
from ..formatters.generic import (
    BaseFormatter,
    LifeListFormatter,
    ListFormatter,
    ObservationFormatter,
    TaxonFormatter,
)
from ..models.user import User
from ..query.query import get_base_query_args, QueryResponse


RICH_BQ_NEWLINE_PAT = re.compile(r"^(\> .*?)\n(?=\> )", re.MULTILINE)
RICH_BQ_END_PAT = re.compile(r"^((\> .*?\n)+)(?!> )", re.MULTILINE)
RICH_NO_BQ_NEWLINE_PAT = re.compile(r"^(?!\> )(.+?)(\n)(?!$|\> )", re.MULTILINE)
RICH_NEWLINE = " \\\n"


class ArgumentError(ValueError):
    """Command arguments are not valid."""


class CommandError(NameError):
    """Command is not known."""


class Format(Enum):
    discord_markdown = 1
    rich = 2


@define
class Context:
    """A Dronefly command context."""

    author: User = User()
    # Optional page formatter and current page:
    # - Provides support for next & prev commands to navigate through
    #   paged command results.
    # - Every command providing paged results must:
    #   - Set page_formatter to the formatter for the new results.
    #   - Set page to the initial page number (default: 0).
    # - Therefore, only a single command providing paged results can
    #   be active at a time.
    page_formatter: Union[BaseFormatter, ListFormatter] = None
    page: int = 0
    per_page: int = 0
    selected: int = 0

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

    def _get_formatted_page(self, formatter, page: int = 0, selected: int = 0):
        if getattr(formatter, "format_page", None):
            markdown_text = formatter.format_page(page, selected)
            last_page = formatter.last_page()
            if last_page > 0:
                markdown_text = "\n\n".join(
                    [markdown_text, f"Page {page + 1}/{last_page + 1}"]
                )
        else:
            markdown_text = formatter.format()
        return self._format_markdown(markdown_text)

    def _format_markdown(self, markdown_text: str):
        if self.format == Format.rich:
            # Richify the markdown:
            # - In Discord markdown, all newlines are rendered as line breaks
            # - In Rich:
            #   - Before every newline, emit " \" to force a line break, except
            #     for these exceptions to handle blockquotes:
            #     - Don't do this for a line preceding a blockquote
            #     - Also don't do this on the last line of a blockquote
            #     - Ensure the last line of each blockquote has two newlines to
            #       end it

            # Replace all but last newline of blockquote with line break sequence:
            rich_markdown = re.sub(RICH_BQ_NEWLINE_PAT, r"\1 \\\n", markdown_text)
            # Add extra newline at end of blockquote so following text won't be
            # tacked on:
            rich_markdown = re.sub(RICH_BQ_END_PAT, r"\1\n\n", rich_markdown)
            # Finally, on any line that isn't part of a blockquote, isn't empty,
            # and isn't at the end of the string, emit a line break:
            rich_markdown = re.sub(RICH_NO_BQ_NEWLINE_PAT, r"\1 \\\n", rich_markdown)
            response = Markdown(rich_markdown)
        else:
            # Return the literal markdown for Discord to render
            response = markdown_text
        return response

    def life(self, ctx: Context, *args):
        _args = " ".join(args) or "by me"
        query = self._parse(_args)
        per_rank = query.per or "main"
        if per_rank not in [*RANK_KEYWORDS, "leaf", "main", "any"]:
            return "Specify `per <rank-or-keyword>`"

        query_args = get_base_query_args(query)
        with self.inat_client.set_ctx(ctx) as client:
            # Handle a useful subset of query args in a simplistic way for now
            # (i.e. no config table lookup yet) to model full query in bot
            if query.user == "me":
                query_args["user"] = client.users.from_ids(
                    ctx.author.inat_user_id, limit=1
                ).one()
            else:
                users = client.users.autocomplete(q=query.user, limit=1)
                if users:
                    query_args["user"] = users[0]
            if query and query.main and query.main.terms:
                main_query_str = " ".join(query.main.terms)
                taxon = client.taxa.autocomplete(q=main_query_str, limit=1).one()
                query_args["taxon"] = taxon
            if query.place:
                place = client.places.autocomplete(q=query.place, limit=1).one()
                query_args["place"] = place
            if query.project:
                project = client.projects.search(q=query.project, limit=1).one()
                query_args["project"] = project
            query_response = QueryResponse(**query_args)
            obs_args = query_response.obs_args()
            life_list = client.observations.life_list(**obs_args)

        if not life_list:
            return f"No life list {query_response.obs_query_description()}"

        per_page = ctx.per_page
        with_index = self.format == Format.rich
        formatter = LifeListFormatter(
            life_list,
            per_rank,
            query_response,
            with_indent=True,
            per_page=per_page,
            with_index=with_index,
        )
        ctx.page_formatter = formatter
        ctx.page = 0
        ctx.selected = 0
        title = formatter.format_title()
        first_page = formatter.get_first_page() or ""
        if first_page:
            # TODO: Provide a method in the formatter to set the title:
            formatter.pages[0]["header"] = title
        return self._get_formatted_page(formatter, 0, 0)

    def next(self, ctx: Context):
        if not ctx.page_formatter:
            return "Type a command that has pages first"
        ctx.page += 1
        if ctx.page > ctx.page_formatter.last_page():
            ctx.page = 0
        ctx.selected = 0
        return self._get_formatted_page(ctx.page_formatter, ctx.page, ctx.selected)

    def page(self, ctx: Context, page: int = 1):
        if not ctx.page_formatter:
            return "Type a command that has pages first"
        last_page = ctx.page_formatter.last_page() + 1
        if page > last_page or page < 1:
            msg = "Specify page 1"
            if last_page > 1:
                msg += f" through {last_page}"
            return msg
        ctx.page = page - 1
        ctx.selected = 0
        return self._get_formatted_page(ctx.page_formatter, ctx.page, ctx.selected)

    def sel(self, ctx: Context, sel: int = 1):
        if not ctx.page_formatter:
            return "Type a command that has pages first"
        _page = ctx.page_formatter.get_page_of_taxa(ctx.page)
        page_len = len(_page)
        if sel > page_len or sel < 1:
            msg = "Specify entry 1"
            if page_len > 1:
                msg += f" through {page_len}"
            return msg
        ctx.selected = sel - 1
        return self._get_formatted_page(ctx.page_formatter, ctx.page, ctx.selected)

    def prev(self, ctx: Context):
        if not ctx.page_formatter:
            return "Type a command that has pages first"
        ctx.page -= 1
        if ctx.page < 0:
            ctx.page = ctx.page_formatter.last_page()
        ctx.selected = 0
        return self._get_formatted_page(ctx.page_formatter, ctx.page, ctx.selected)

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
        )
        response = self._get_formatted_page(formatter)

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
                community_taxon = client.taxa.from_ids(
                    obs.community_taxon_id, limit=1
                ).one()
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
        response = self._get_formatted_page(formatter)

        return response

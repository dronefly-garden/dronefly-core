from enum import Enum
import re
from typing import Union

from attrs import define
from requests import HTTPError
from rich.markdown import Markdown

from ..clients.inat import iNatClient
from ..constants import (
    CONFIG_PATH,
    INAT_DEFAULTS,
    INAT_USER_DEFAULT_PARAMS,
    RANK_EQUIVALENTS,
    RANKS_FOR_LEVEL,
    RANK_KEYWORDS,
    RANK_LEVELS,
)

from ..parsers import NaturalParser
from ..formatters.generic import (
    BaseFormatter,
    TaxonListFormatter,
    ListFormatter,
    ObservationFormatter,
    TaxonFormatter,
    UserFormatter,
    p,
)
from ..models.config import Config
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
        default = None
        if self.author:
            default = getattr(self.author, inat_param, None)
        if not default:
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
    config: Config = Config()

    def _parse(self, query_str):
        return self.parser.parse(query_str)

    def _get_formatted_page(
        self,
        formatter,
        page: int = 0,
        selected: int = 0,
        header: str = None,
        footer: str = None,
    ):
        if getattr(formatter, "format_page", None):
            markdown_text = formatter.format_page(page, selected)
            last_page = formatter.last_page()
            if last_page > 0:
                markdown_text = "\n\n".join(
                    [markdown_text, f"Page {page + 1}/{last_page + 1}"]
                )
        else:
            markdown_text = formatter.format()
        if header or footer:
            markdown_text = "\n\n".join(
                [item for item in (header, markdown_text, footer) if item is not None]
            )
        return self._format_markdown(markdown_text)

    def _format_markdown(self, markdown_text: str):
        """Format Rich vs. Discord markdown."""
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

    def _simple_format_markdown(self, markdown_text: str):
        """Simplified formatter for Rich vs. Discord markdown.

        Discord vs. Rich linebreak rendering is harder than we thought, e.g.
        `_format_markdown()` doesn't give correct results with point-form
        or numbered lists. If special handling of newlines isn't needed, then
        use this helper instead.
        """
        if self.format == Format.rich:
            # Richify the markdown
            response = Markdown(markdown_text)
        else:
            # Return the literal markdown for Discord to render
            response = markdown_text
        return response

    def life(self, ctx: Context, *args):
        _args = " ".join(args) or "by me"
        query = self._parse(_args)
        per_rank = query.per or "main"
        if per_rank not in [*RANK_KEYWORDS, "leaf", "child", "main", "any"]:
            return "Specify `per <rank-or-keyword>`"
        sort_by = query.sort_by or None
        if sort_by not in [None, "obs", "name"]:
            return "Specify `sort by obs` or `sort by name` (default)"
        order = query.order or None
        if order not in [None, "asc", "desc"]:
            return "Specify `order asc` or `order desc`"

        query_args = get_base_query_args(query)
        with self.inat_client.set_ctx(ctx) as client:
            # Handle a useful subset of query args in a simplistic way for now
            # (i.e. no config table lookup yet) to model full query in bot
            if query.user == "me":
                if ctx.author.inat_user_id:
                    query_args["user"] = client.users.from_ids(
                        ctx.author.inat_user_id
                    ).one()
                else:
                    return "Your iNat user is not known"
            elif query.user == "any":
                # i.e. override default "by me" when no arguments are given
                pass
            else:
                user = client.users.autocomplete(q=query.user).one()
                if user:
                    query_args["user"] = user
            if query and query.main and query.main.terms:
                main_query_str = " ".join(query.main.terms)
                taxon = client.taxa.autocomplete(q=main_query_str).one()
                query_args["taxon"] = taxon
            if query.place:
                place = client.places.autocomplete(q=query.place).one()
                query_args["place"] = place
            if query.project:
                project = client.projects.search(q=query.project).one()
                query_args["project"] = project
            query_response = QueryResponse(**query_args)
            obs_args = query_response.obs_args()
            life_list = client.observations.life_list(**obs_args)

        if not life_list:
            return f"No life list {query_response.obs_query_description()}"

        per_page = ctx.per_page
        with_index = self.format == Format.rich
        taxon_list = life_list.data
        formatter = TaxonListFormatter(
            taxon_list,
            per_rank,
            query_response,
            with_indent=True,
            per_page=per_page,
            with_index=with_index,
            sort_by=sort_by,
            order=order,
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

    def taxon_list(self, ctx: Context, *args):
        query = self._parse(" ".join(args))
        per_rank = query.per or "child"
        if per_rank not in [*RANK_KEYWORDS, "child"]:
            return "Specify `per <rank>` or `per child` (default)"
        _per_rank = per_rank
        rank_level = None
        sort_by = query.sort_by or None
        if sort_by not in [None, "obs", "name"]:
            return "Specify `sort by obs` or `sort by name` (default)"
        order = query.order or None
        if order not in [None, "asc", "desc"]:
            return "Specify `order asc` or `order desc`"

        query_args = get_base_query_args(query)
        taxon = None
        taxon_list = []
        short_description = ""
        msg = None
        with self.inat_client.set_ctx(ctx) as client:
            # Handle a useful subset of query args in a simplistic way for now
            # (i.e. no config table lookup yet) to model full query in bot
            if query and query.main and query.main.terms:
                main_query_str = " ".join(query.main.terms)
                taxon = client.taxa.autocomplete(q=main_query_str).one()
                if taxon:
                    taxon = client.taxa.populate(taxon)
                query_args["taxon"] = taxon
            query_response = QueryResponse(**query_args)
            taxon = query_response.taxon
            if not taxon:
                return f"No taxon {query_response.obs_query_description()}"

            _taxon_list = [
                taxon,
                *[_taxon for _taxon in taxon.children if _taxon.is_active],
            ]
            if per_rank == "child":
                short_description = "Children"
                taxon_list = _taxon_list
            else:
                _per_rank = RANK_EQUIVALENTS.get(per_rank) or per_rank
                rank_level = RANK_LEVELS[_per_rank]
                if rank_level >= taxon.rank_level:
                    return self._format_markdown(
                        "\N{WARNING SIGN}  "
                        f"**The rank `{per_rank}` is not lower than "
                        "the taxon rank: `{taxon.rank}`.**"
                    )
                short_description = p.plural(_per_rank).capitalize()
                _children = [
                    child for child in _taxon_list if child.rank_level == rank_level
                ]
                _without_rank_ids = [
                    child.id for child in _taxon_list if child not in _children
                ]
                if len(_without_rank_ids) > 0:
                    # One chance at retrieving the remaining children, i.e. if the
                    # remainder (direct children - those at the specified rank level)
                    # don't constitute a single page of results, then show children
                    # instead.
                    _descendants = client.taxa.search(
                        taxon_id=_without_rank_ids,
                        rank_level=rank_level,
                        is_active=True,
                        per_page=500,
                    )
                    # The choice of 2500 as our limit is arbitrary:
                    # - will take 5 more API calls to satisfy
                    # - encompasses the largest genera (e.g. Astragalus)
                    # - meant to limit unreasonable sized queries so they don't make
                    #   excessive API demands
                    # - TODO: switch to using a local DB built from full taxonomy dump
                    #   so we can lift this restriction
                    if _descendants.count() > 2500:
                        short_description = "Children"
                        msg = (
                            f"\N{WARNING SIGN}  **Too many {p.plural(_per_rank)}. "
                            "Listing children instead:**"
                        )
                        _per_rank = "child"
                        taxon_list = _taxon_list
                    else:
                        taxon_list = [*_children, *_descendants.all()]
                else:
                    taxon_list = _children
                # List all ranks at the same level, not just the specified rank
                if _per_rank != "child":
                    _per_rank = RANKS_FOR_LEVEL[rank_level]

        per_page = ctx.per_page
        with_index = self.format == Format.rich
        formatter = TaxonListFormatter(
            taxon_list,
            per_rank=_per_rank,
            query_response=query_response,
            with_indent=True,
            per_page=per_page,
            with_index=with_index,
            sort_by=sort_by,
            order=order,
            short_description=short_description,
        )
        ctx.page_formatter = formatter
        ctx.page = 0
        ctx.selected = 0
        title = formatter.format_title()
        first_page = formatter.get_first_page() or ""
        if first_page:
            # TODO: Provide a method in the formatter to set the title:
            formatter.pages[0]["header"] = title
        page = self._get_formatted_page(formatter, 0, 0, header=msg)
        return page

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
        taxon = None
        if len(args) == 0 or args[0] == "sel":
            formatter = ctx.page_formatter
            if formatter and getattr(formatter, "get_page_of_taxa", None):
                page = formatter.get_page_of_taxa(ctx.page)
                with self.inat_client.set_ctx(ctx) as client:
                    taxon = client.taxa.populate(page[ctx.selected])
            else:
                return "Select a taxon first"
        else:
            query = self._parse(" ".join(args))
            # TODO: Handle all query clauses, not just main.terms
            # TODO: Doesn't do any ranking or filtering of results
            if not query.main or not query.main.terms:
                return "Not a taxon"

            with self.inat_client.set_ctx(ctx) as client:
                main_query_str = " ".join(query.main.terms)
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
                reverse=True,
            ).one()
            if not obs:
                return f"No observations by you found for: {taxon.full_name}"

            taxon_summary = client.observations.taxon_summary(obs.id)
            if obs.community_taxon_id and obs.community_taxon_id != obs.taxon.id:
                community_taxon = client.taxa.from_ids(obs.community_taxon_id).one()
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

    def user(self, ctx: Context, user_id: str):
        with self.inat_client.set_ctx(ctx) as client:
            user = None
            try:
                user = client.users(user_id)
            except HTTPError as err:
                if err.response.status_code == 404:
                    pass
            if not user:
                return "User not found."

            return self._format_markdown(UserFormatter(user).format())

    def user_add(self, ctx: Context, user_abbrev: str, user_id: str):
        if user_abbrev != "me":
            return "Only `user add me <user-id>` is supported at this time."
        user_config = self.config.user(ctx.author.id)
        configured_user_id = None
        if user_config:
            configured_user_id = user_config.get("inat_user_id")

        with self.inat_client.set_ctx(ctx) as client:
            user = None
            try:
                user = client.users(user_id)
            except HTTPError as err:
                if err.response.status_code == 404:
                    pass
            if not user:
                return "User not found."

            response = ""
            redefining = False
            if configured_user_id:
                if configured_user_id == user.id:
                    return "User already added."
                configured_user = None
                try:
                    configured_user = client.users(configured_user_id)
                except HTTPError as err:
                    if err.response.status_code == 404:
                        pass
                if configured_user:
                    configured_user_str = UserFormatter(configured_user).format()
                else:
                    configured_user_str = f"User id not found: {configured_user_id}"
                redefining = True
                response += (
                    f"- Already defined as another user: {configured_user_str}\n"
                )
                response += "- To change to the specified user:\n"

            response += f"1. Confirm this is you: {UserFormatter(user).format()}\n"
            add_or_mod = "modify" if redefining else "add"
            response += f"2. Edit `{CONFIG_PATH}` and {add_or_mod}:\n"
            response += (
                f"```toml\n[users.{ctx.author.id}]\ninat_user_id = {user.id}\n```\n"
            )
            response += "3. Restart dronefly-cli."

            return self._simple_format_markdown(response)

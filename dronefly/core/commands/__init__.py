import asyncio
from enum import Enum
import re
from typing import Union

from requests import HTTPError
from rich.markdown import Markdown

from ..clients.inat import iNatClient
from ..constants import (
    CONFIG_PATH,
    RANK_EQUIVALENTS,
    RANKS_FOR_LEVEL,
    RANK_KEYWORDS,
    RANK_LEVELS,
)

from ..parsers import NaturalParser
from ..parsers.constants import VALID_OBS_SORT_BY
from ..query import prepare_query
from ..formatters.generic import (
    ObservationFormatter,
    TaxonListFormatter,
    TaxonFormatter,
    UserFormatter,
    p,
)
from ..menus.taxon_list import TaxonListSource
from ..models import BaseFormatter, Config, Context, ListFormatter


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


def _check_obs_query_fields(query_response):
    sort_by = query_response.sort_by
    if sort_by is not None and sort_by not in VALID_OBS_SORT_BY:
        raise ArgumentError(
            f"Invalid `sort by`. Must be one of: `{', '.join(VALID_OBS_SORT_BY.keys())}`"
        )


# TODO: everything below needs to be broken down into different layers
# handling each thing:
# - Context
#   - user, channel, etc.
#   - affects which settings are passed to inat (e.g. home place for conservation status)
class Commands:
    """A Dronefly command processor."""

    def __init__(
        self,
        loop: asyncio.BaseEventLoop,
        format: Format = Format.discord_markdown,
    ):
        self.loop = loop
        # TODO: platform: dronefly.Platform
        # - e.g. discord, commandline, web
        self.format = format
        self.inat_client = iNatClient(loop=loop)
        self.parser = NaturalParser()
        self.dronefly_config = Config()

    def _parse(self, query_str):
        return self.parser.parse(query_str)

    async def _get_formatted_page(
        self,
        formatter: Union[ListFormatter, BaseFormatter],
        page_number: int = 0,
        selected: int = 0,
        header: str = None,
        footer: str = None,
    ):
        source = getattr(formatter, "source", None)
        if getattr(formatter, "format_page", None):
            if source:
                page = await source.get_page(page_number)
                markdown_text = formatter.format_page(page, page_number, selected)
            else:
                markdown_text = formatter.format_page(page_number, selected)
            last_page = formatter.last_page()
            if last_page > 0:
                markdown_text = "\n\n".join(
                    [markdown_text, f"Page {page_number + 1}/{last_page + 1}"]
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

    async def life(self, ctx: Context, *args):
        _args = " ".join(args) or "by me"
        query = self._parse(_args)
        per_rank = query.per or "main"
        if per_rank not in [*RANK_KEYWORDS, "leaf", "child", "main", "any"]:
            raise ArgumentError("Specify `per <rank-or-keyword>`")
        sort_by = query.sort_by or None
        if sort_by not in [None, "obs", "name"]:
            raise ArgumentError("Specify `sort by obs` or `sort by name` (default)")
        order = query.order or None
        if order not in [None, "asc", "desc"]:
            raise ArgumentError("Specify `order asc` or `order desc`")

        with self.inat_client.set_ctx(ctx) as client:
            query_response = await prepare_query(client, self.dronefly_config, query)
            obs_args = query_response.obs_args()
            life_list = await client.observations.life_list(**obs_args)

        if not life_list:
            raise LookupError(f"No life list {query_response.obs_query_description()}")

        per_page = ctx.per_page
        with_index = self.format == Format.rich
        taxon_list = life_list.data
        formatter = TaxonListFormatter(
            with_indent=True,
            with_index=with_index,
        )
        source = TaxonListSource(
            entries=taxon_list,
            query_response=query_response,
            formatter=formatter,
            per_page=per_page,
            per_rank=per_rank,
            sort_by=sort_by,
            order=order,
        )
        formatter.source = source
        ctx.page_formatter = formatter
        ctx.page_number = 0
        ctx.selected = 0
        title = formatter.format_title() if source.meta.taxon_count > 0 else None
        return await self._get_formatted_page(
            ctx.page_formatter, ctx.page_number, ctx.selected, header=title
        )

    async def taxon_list(self, ctx: Context, *args):
        query = self._parse(" ".join(args))
        per_rank = query.per or "child"
        if per_rank not in [*RANK_KEYWORDS, "child"]:
            raise ArgumentError("Specify `per <rank>` or `per child` (default)")
        _per_rank = per_rank
        rank_level = None
        sort_by = query.sort_by or None
        if sort_by not in [None, "obs", "name"]:
            raise ArgumentError("Specify `sort by obs` or `sort by name` (default)")
        order = query.order or None
        if order not in [None, "asc", "desc"]:
            raise ArgumentError("Specify `order asc` or `order desc`")

        taxon = None
        taxon_list = []
        short_description = ""
        msg = None
        with self.inat_client.set_ctx(ctx) as client:
            query_response = await prepare_query(client, self.dronefly_config, query)
            taxon = query_response.taxon
            if not taxon:
                raise LookupError(f"No taxon {query_response.obs_query_description()}")

            taxon = await client.taxa.populate(taxon)
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
                    raise ArgumentError(
                        "\N{WARNING SIGN}  "
                        f"**The rank `{per_rank}` is not lower than "
                        f"the taxon rank: `{taxon.rank}`.**"
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
                    descendants_paginator = client.taxa.search(
                        taxon_id=_without_rank_ids,
                        rank_level=rank_level,
                        is_active=True,
                        per_page=500,
                    )
                    descendants_aiter = aiter(descendants_paginator)
                    # The choice of 2500 as our limit is arbitrary:
                    # - will take 5 more API calls to satisfy
                    # - encompasses the largest genera (e.g. Astragalus)
                    # - meant to limit unreasonable sized queries so they don't make
                    #   excessive API demands
                    # - TODO: switch to using a local DB built from full taxonomy dump
                    #   so we can lift this restriction
                    first_descendant = await anext(descendants_aiter, None)
                    if descendants_paginator.count() > 2500:
                        short_description = "Children"
                        msg = (
                            f"\N{WARNING SIGN}  **Too many {p.plural(_per_rank)}. "
                            "Listing children instead:**"
                        )
                        _per_rank = "child"
                        taxon_list = _taxon_list
                    else:
                        # Now we can get the remaining descendants:
                        taxon_list = [*_children, first_descendant]
                        async for taxon in descendants_aiter:
                            taxon_list.append(taxon)
                else:
                    taxon_list = _children
                # List all ranks at the same level, not just the specified rank
                if _per_rank != "child":
                    _per_rank = RANKS_FOR_LEVEL[rank_level]

        per_page = ctx.per_page
        with_index = self.format == Format.rich
        formatter = TaxonListFormatter(
            with_indent=True,
            with_index=with_index,
            short_description=short_description,
        )
        source = TaxonListSource(
            entries=taxon_list,
            query_response=query_response,
            formatter=formatter,
            per_page=per_page,
            per_rank=_per_rank,
            sort_by=sort_by,
            order=order,
        )
        formatter.source = source
        title = formatter.format_title() if source.meta.taxon_count > 0 else None
        ctx.page_formatter = formatter
        ctx.page_number = 0
        ctx.selected = 0
        title_lines = [msg] if msg else []
        if title:
            title_lines.append(title)
        title = "\n".join(title_lines)
        return await self._get_formatted_page(
            ctx.page_formatter, ctx.page_number, ctx.selected, header=title
        )

    async def next(self, ctx: Context):
        if not ctx.page_formatter:
            raise CommandError("Type a command that has pages first")
        ctx.page_number += 1
        if ctx.page_number > ctx.page_formatter.last_page():
            ctx.page_number = 0
        ctx.selected = 0
        return await self._get_formatted_page(
            ctx.page_formatter, ctx.page_number, ctx.selected
        )

    async def page(self, ctx: Context, page_number: int = 1):
        if not ctx.page_formatter:
            raise CommandError("Type a command that has pages first")
        last_page = ctx.page_formatter.last_page() + 1
        if page_number > last_page or page_number < 1:
            msg = "Specify page 1"
            if last_page > 1:
                msg += f" through {last_page}"
            raise ArgumentError(msg)
        ctx.page_number = page_number - 1
        ctx.selected = 0
        return await self._get_formatted_page(
            ctx.page_formatter, ctx.page_number, ctx.selected
        )

    async def sel(self, ctx: Context, sel: int = 1):
        if not ctx.page_formatter:
            raise CommandError("Type a command that has pages first")
        _page = await ctx.page_formatter.source.get_page(ctx.page_number)
        page_len = len(_page)
        if sel > page_len or sel < 1:
            msg = "Specify entry 1"
            if page_len > 1:
                msg += f" through {page_len}"
            raise ArgumentError(msg)
        ctx.selected = sel - 1
        return await self._get_formatted_page(
            ctx.page_formatter, ctx.page_number, ctx.selected
        )

    async def prev(self, ctx: Context):
        if not ctx.page_formatter:
            raise CommandError("Type a command that has pages first")
        ctx.page_number -= 1
        if ctx.page_number < 0:
            ctx.page_number = ctx.page_formatter.last_page()
        ctx.selected = 0
        return await self._get_formatted_page(
            ctx.page_formatter, ctx.page_number, ctx.selected
        )

    async def taxon(self, ctx: Context, *args):
        taxon = None
        if len(args) == 0 or args[0] == "sel":
            formatter = ctx.page_formatter
            if formatter and getattr(formatter, "source", None):
                page = await formatter.source.get_page(ctx.page_number)
                with self.inat_client.set_ctx(ctx) as client:
                    taxon = await client.taxa.populate(page[ctx.selected])
            else:
                raise CommandError("Select a taxon first")
        else:
            query = self._parse(" ".join(args))
            # TODO: Handle all query clauses, not just main.terms
            # TODO: Doesn't do any ranking or filtering of results
            if not query.main or not query.main.terms:
                raise ArgumentError("Not a taxon")

            with self.inat_client.set_ctx(ctx) as client:
                query_response = await prepare_query(
                    client, self.dronefly_config, query
                )
                if not query_response.taxon:
                    raise LookupError("Nothing found")
                taxon = await client.taxa.populate(query_response.taxon)

        formatter = TaxonFormatter(
            taxon,
            lang=ctx.get_inat_user_default("inat_lang"),
            with_url=True,
        )
        response = await self._get_formatted_page(formatter)

        return response

    async def obs(self, ctx: Context, *args):
        query = self._parse(" ".join(args))

        with self.inat_client.set_ctx(ctx) as client:
            query_response = await prepare_query(client, self.dronefly_config, query)
            _check_obs_query_fields(query_response)
            if query_response.taxon:
                query_response.taxon = await client.taxa.populate(query_response.taxon)
            obs_args = query_response.obs_args()
            obs_args["reverse"] = True
            obs_args["limit"] = 1
            obs = await anext(aiter(client.observations.search(**obs_args)), None)
            if not obs:
                raise LookupError(
                    f"No observation found {query_response.obs_query_description()}"
                )

            taxon_summary = await client.observations.taxon_summary(obs.id)
            if obs.community_taxon_id and obs.community_taxon_id != obs.taxon.id:
                community_taxon = await anext(
                    aiter(client.taxa.from_ids(obs.community_taxon_id)), None
                )
                community_taxon_summary = await client.observations.taxon_summary(
                    obs.id, community=1
                )
            else:
                community_taxon = query_response.taxon
                community_taxon_summary = taxon_summary

        formatter = ObservationFormatter(
            obs,
            taxon_summary=taxon_summary,
            community_taxon=community_taxon,
            community_taxon_summary=community_taxon_summary,
            with_link=True,
        )
        response = await self._get_formatted_page(formatter)

        return response

    async def user(self, ctx: Context, user_id: str):
        with self.inat_client.set_ctx(ctx) as client:
            user = None
            try:
                user = await anext(aiter(client.users.from_ids(user_id)), None)
            except HTTPError as err:
                if err.response.status_code == 404:
                    pass
            if not user:
                raise LookupError("User not found.")

            return self._format_markdown(UserFormatter(user).format())

    async def user_add(self, ctx: Context, user_abbrev: str, user_id: str):
        if user_abbrev != "me":
            raise ArgumentError(
                "Only `user add me <user-id>` is supported at this time."
            )
        user_config = self.dronefly_config.user(ctx.author.id)
        configured_user_id = None
        if user_config:
            configured_user_id = user_config.get("inat_user_id")

        with self.inat_client.set_ctx(ctx) as client:
            user = None
            try:
                user = await anext(aiter(client.users.from_ids(user_id)), None)
            except HTTPError as err:
                if err.response.status_code == 404:
                    pass
            if not user:
                raise LookupError("User not found.")

            response = ""
            redefining = False
            if configured_user_id:
                if configured_user_id == user.id:
                    raise ArgumentError("User already added.")
                configured_user = None
                try:
                    configured_user = await anext(
                        aiter(client.users.from_ids(configured_user_id)), None
                    )
                except HTTPError as err:
                    if err.response.status_code == 404:
                        pass
                if configured_user:
                    configured_user_str = UserFormatter(configured_user).format()
                else:
                    configured_user_str = f"User id not found: {configured_user_id}"
                    raise LookupError(configured_user_str)
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

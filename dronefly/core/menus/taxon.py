from typing import Any

from pyinaturalist import User

from dronefly.core.clients.inat import iNatClient
from dronefly.core.formatters.generic import CountsFormatter
from dronefly.core.menus.counts import CountsSource
from dronefly.core.query.query import get_user_count

from .menu import BaseMenu
from .source import ListPageSource
from ..formatters import TaxonFormatter
from ..formatters.constants import WWW_BASE_URL
from ..query import QueryResponse


class TaxonSource(ListPageSource):
    def __init__(self, taxon_formatter: TaxonFormatter, with_ancestors: bool = True):
        self._taxon_formatter = taxon_formatter
        self._url = f"{WWW_BASE_URL}/taxon/{self.query_response.taxon.id}"
        self.with_ancestors = with_ancestors
        pages = [self.formatter.format(with_ancestors=with_ancestors)]
        super().__init__(pages, per_page=1)

    def is_paginating(self):
        return False

    @property
    def formatter(self) -> TaxonFormatter:
        return self._taxon_formatter

    @property
    def query_response(self) -> QueryResponse:
        return self.formatter.query_response

    def toggle_ancestors(self):
        self.with_ancestors = not self.with_ancestors
        self.update_page()

    def format_page(self):
        return self.formatter.format(with_ancestors=self.with_ancestors)

    def update_page(self):
        self.entries[0] = self.format_page()

    @property
    def counts_formatter(self) -> CountsFormatter:
        return self.formatter.counts_formatter

    @property
    def counts_page(self) -> str:
        return self.formatter.counts_page

    @counts_formatter.setter
    def counts_formatter(self, formatter):
        self.formatter.counts_formatter = formatter

    @counts_page.setter
    def counts_page(self, page):
        self.formatter.counts_page = page

    @property
    def counts_source(self) -> CountsSource:
        return self.counts_formatter.source if self.counts_formatter else None

    async def toggle_user_count(self, inat_client: iNatClient, user: User):
        query_response = self.query_response
        counts_formatter = self.counts_formatter
        user_count = None
        if self.counts_source:
            user_count = next(
                (count for count in self.counts_source.entries if count.id == user.id),
                None,
            )
        if user_count is not None:
            self.counts_source.entries.remove(user_count)
        else:
            user_count = await get_user_count(inat_client, query_response, user)
            if self.counts_source:
                # A source already exists. Just append the count:
                self.counts_source.entries.append(user_count)
            else:
                # Create both a new source and formatter for counts
                # with the user count as its only entry and link them
                # back to the taxon formatter:
                counts_formatter = CountsFormatter()
                counts_source = CountsSource(
                    entries=[user_count],
                    query_response=query_response,
                    counts_formatter=counts_formatter,
                    per_page=15,  # FIXME: magic number!
                )
                counts_formatter.source = counts_source
                self.counts_formatter = counts_formatter
        # One way or the other, we now have a counts formatter attached. All that remains
        # is to populate it with new content and regenerate the formatted taxon page
        # to include it:
        counts_page = await self.counts_source.get_page(page_number=0)
        self.formatter.counts_page = counts_page
        self.update_page()


class TaxonMenu(BaseMenu):
    def __init__(
        self,
        inat_client: iNatClient,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.inat_client = inat_client

    @property
    def dronefly_ctx(self):
        return self.inat_client.ctx

    @property
    def dronefly_author(self):
        return self.dronefly_ctx.author

    @property
    def author_inat_user_id(self):
        return self.dronefly_ctx.author.inat_user_id if self.dronefly_author else None

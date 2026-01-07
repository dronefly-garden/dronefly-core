from typing import Union

from pyinaturalist import Place, User, UserCount

from dronefly.core.clients.inat import iNatClient
from dronefly.core.query.query import get_place_count, get_user_count

from ..models import PlaceCount
from .source import ListPageSource
from ..formatters import CountsFormatter
from ..query import QueryResponse


class CountsSource(ListPageSource):
    def __init__(
        self,
        entries: Union[list[PlaceCount], list[UserCount]],
        query_response: QueryResponse,
        counts_formatter: CountsFormatter,
        **kwargs
    ):
        self.query_response = query_response
        self._counts_formatter = counts_formatter
        super().__init__(entries, **kwargs)

    def is_paginating(self):
        return True

    @property
    def formatter(self) -> CountsFormatter:
        return self._counts_formatter

    def format_page(self, page):
        return self.formatter.format_page(page)


class CountsSourceMixin(ListPageSource):
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

    async def toggle_place_count(self, inat_client: iNatClient, place: Place):
        query_response = self.query_response
        counts_formatter = self.counts_formatter
        place_count = None
        if self.counts_source:
            place_count = next(
                (count for count in self.counts_source.entries if count.id == place.id),
                None,
            )
        if place_count is not None:
            self.counts_source.entries.remove(place_count)
        else:
            place_count = await get_place_count(inat_client, query_response, place)
            if self.counts_source:
                # A source already exists. Just append the count:
                self.counts_source.entries.append(place_count)
            else:
                # Create both a new source and formatter for counts
                # with the user count as its only entry and link them
                # back to the taxon formatter:
                counts_formatter = CountsFormatter()
                counts_source = CountsSource(
                    entries=[place_count],
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

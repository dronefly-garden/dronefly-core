from pyinaturalist import UserCounts

from .source import ListPageSource
from ..formatters import UserCountsFormatter
from ..query import QueryResponse


class UserCountsSource(ListPageSource):
    def __init__(
        self,
        entries: UserCounts,
        query_response: QueryResponse,
        user_counts_formatter: UserCountsFormatter,
        **kwargs
    ):
        self.query_response = query_response
        self._user_counts_formatter = user_counts_formatter
        super().__init__(entries, **kwargs)

    def is_paginating(self):
        return False

    @property
    def formatter(self) -> UserCountsFormatter:
        return self._user_counts_formatter

    def format_page(self, page):
        return self.formatter.format_page(page)

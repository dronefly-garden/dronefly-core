from pyinaturalist import UserCount

from .source import ListPageSource
from ..formatters import CountsFormatter
from ..query import QueryResponse


class CountsSource(ListPageSource):
    def __init__(
        self,
        entries: list[UserCount],
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

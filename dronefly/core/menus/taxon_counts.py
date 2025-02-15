from .source import ListPageSource
from ..formatters import TaxonCountsFormatter
from ..query import QueryResponse


class TaxonCountsSource(ListPageSource):
    def __init__(
        self,
        query_response: QueryResponse,
        taxon_counts_formatter: TaxonCountsFormatter,
        **kwargs
    ):
        self.query_response = query_response
        self._taxon_counts_formatter = taxon_counts_formatter
        super().__init__(**kwargs)

    def is_paginating(self):
        return False

    @property
    def formatter(self) -> TaxonCountsFormatter:
        return self._taxon_counts_formatter

    def format_page(self, page):
        return self.formatter.format_page(page)

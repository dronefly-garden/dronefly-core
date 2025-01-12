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
        self.entries[0] = self.format_page()

    def format_page(self):
        return self.formatter.format(with_ancestors=self.with_ancestors)

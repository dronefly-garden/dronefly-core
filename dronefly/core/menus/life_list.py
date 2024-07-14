from .source import ListPageSource
from .menu import BaseMenu
from ..formatters import LifeListFormatter
from ..query import QueryResponse
from ..utils import lifelists_url_from_query_response


class LifeListSource(ListPageSource):
    def __init__(self, life_list_formatter: LifeListFormatter):
        self._life_list_formatter = life_list_formatter
        self._url = (
            lifelists_url_from_query_response(self.query_response)
            if self.query_response.user
            else None
        )
        pages = list(page for page in self._life_list_formatter.generate_pages())
        super().__init__(pages, per_page=1)

    def is_paginating(self):
        return True

    @property
    def formatter(self) -> LifeListFormatter:
        return self._life_list_formatter

    @property
    def query_response(self) -> QueryResponse:
        return self.formatter.query_response

    def format_page(self, menu: BaseMenu, page):
        return self.formatter.format()

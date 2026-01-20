from typing import Any

from dronefly.core.clients.inat import iNatClient
from dronefly.core.menus.counts import CountsSourceMixin

from .menu import BaseMenu
from ..formatters import TaxonFormatter
from ..formatters.constants import WWW_BASE_URL
from ..query import QueryResponse


class TaxonSource(CountsSourceMixin):
    def __init__(self, taxon_formatter: TaxonFormatter, with_ancestors: bool = True):
        self._taxon_formatter = taxon_formatter
        self._url = f"{WWW_BASE_URL}/taxon/{self.query_response.taxon.id}"
        self.with_ancestors = with_ancestors
        super().__init__()

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

    def format_page(self):
        return self.formatter.format(with_ancestors=self.with_ancestors)


class TaxonMenu(BaseMenu):
    def __init__(
        self,
        inat_client: iNatClient,
        source: TaxonSource,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.inat_client = inat_client
        self.source = source

    @property
    def dronefly_ctx(self):
        return self.inat_client.ctx

    @property
    def dronefly_author(self):
        return self.dronefly_ctx.author

    @property
    def author_inat_user_id(self):
        return self.dronefly_ctx.author.inat_user_id if self.dronefly_author else None

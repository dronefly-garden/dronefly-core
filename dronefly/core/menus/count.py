from typing import Any, Union

from pyinaturalist import UserCount

from dronefly.core.models.place_count import PlaceCount

from .counts import CountsSourceMixin
from .menu import BaseMenu
from ..clients.inat import iNatClient
from ..formatters.generic import CountFormatter
from ..query.query import QueryResponse
from ..utils import obs_url_from_v1


class CountSource(CountsSourceMixin):
    def __init__(self, count: Union[UserCount, PlaceCount], formatter: CountFormatter):
        self.count = count
        self.formatter = formatter
        super().__init__()

    def is_paginating(self):
        return False

    @property
    def formatter(self) -> CountFormatter:
        return self._formatter

    @formatter.setter
    def formatter(self, value):
        self._formatter = value

    @property
    def query_response(self) -> QueryResponse:
        return self.formatter.query_response

    @property
    def url(self) -> str:
        return obs_url_from_v1(self.query_response.obs_args())

    def format_page(self):
        return self.formatter.format()


class CountMenu(BaseMenu):
    def __init__(
        self,
        source: CountSource,
        inat_client: iNatClient,
        **kwargs: Any,
    ) -> None:
        self.source = source
        self.inat_client = inat_client
        super().__init__(**kwargs)

    @property
    def dronefly_ctx(self):
        return self.inat_client.ctx

    @property
    def dronefly_author(self):
        return self.dronefly_ctx.author

    @property
    def author_inat_user_id(self):
        return self.dronefly_ctx.author.inat_user_id if self.dronefly_author else None

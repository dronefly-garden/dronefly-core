from typing import Any, Union

from pyinaturalist import Observation
from pyinaturalist.paginator import Paginator

from dronefly.core.utils import obs_url_from_v1

from .source import AsyncIteratorPageSource
from .menu import BaseSearchMenu
from ..formatters import ObservationSearchFormatter
from ..query import QueryResponse


class ObservationSearchSource(AsyncIteratorPageSource):
    """
    Attributes
    ----------
    iterator: Paginator[Observation]
        A list of observations matching the query parameters.
    """

    entries: list[Observation]

    def __init__(
        self,
        iterator: Paginator[Observation],
        query_response: QueryResponse,
        formatter: ObservationSearchFormatter,
        per_page: int = 20,
        sort_by: str = None,
        order: str = None,
        **kwargs,
    ):
        """
        Parameters
        ----------
        iterator: Paginator[Observation]
            Raw list of observations.

        query_response: QueryResponse
            The query response contains all iNat objects in the query
            except for the source itself (e.g. user, place, etc.)

        formatter: ObservationSearchFormatter
            Helper class that formats pages from the source.

        per_page: int, optional
            The number of taxa to include in each page.

        sort_by: str, optional
            If specified, sort descending by `added` (default), `observed`, or `votes`.

        order: str, optional
            If specified, use `asc` (ascending) or `desc` (descending) as the order for the
            `sort_by` key.
        """
        self._observation_search_formatter = formatter
        self.query_response = query_response
        self._url = obs_url_from_v1(query_response.obs_args())
        self.sort_by = sort_by
        self.order = order
        self._iterator = iterator
        super().__init__(iterator, per_page=per_page, **kwargs)
        self.formatter.source = self

    def is_paginating(self):
        return True

    @property
    def formatter(self) -> ObservationSearchFormatter:
        return self._observation_search_formatter

    def format_page(
        self,
        page: Union[Observation, list[Observation]],
        page_number: int = 0,
        selected: int = 0,
    ):
        return self.formatter.format(
            self,
            page=page,
            page_number=page_number,
            selected=selected,
        )


class ObservationSearchMenu(BaseSearchMenu):
    def __init__(
        self,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

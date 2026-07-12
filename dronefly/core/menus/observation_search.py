from typing import Any, Union

from pyinaturalist import Observation, Paginator

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

    def get_max_pages(self):
        return int(self._iterator.count() / self.per_page) + 1

    def format_page(
        self,
        page: Union[Observation, list[Observation]],
        page_number: int = 0,
        selected: int = 0,
    ):
        def format_page_of_observations(page: list[Observation]):
            formatted_observations = []
            for observation in page:
                if observation.taxon:
                    taxon_name = observation.taxon.full_name
                else:
                    taxon_name = "Unknown"
                formatted_observation = {"taxon_name": taxon_name}
                formatted_observations.append(formatted_observation)
            return formatted_observations

        def make_page_content(page: list[Observation]):
            """Format all parts of the page content."""
            structured_page = {
                "header": None,
                "entries_header": None,
                "entries": [],
                "footer": None,
            }
            if page and self.with_taxa:
                formatted_observations = format_page_of_observations(page)
                structured_page["entries"] = formatted_observations
            return structured_page

        def assemble_page(content: dict, selected: int = 0):
            """Assemble page content into a formatted page."""
            sections = []
            if content["header"]:
                sections.append(content["header"])
            if content["entries_header"]:
                sections.append(content["entries_header"])
            if content["entries"]:
                entries = []
                for (index, entry) in enumerate(content["entries"]):
                    _i = f"**`{str(index + 1).zfill(2)}) `**" if self.with_index else ""
                    if selected == index:
                        _s = ">"
                        _n = "**__"
                        _e = "__**"
                    else:
                        _s = "\N{EN SPACE}"
                        _n = ""
                        _e = ""
                    entries.append(
                        f"{_i}`{entry['count']}{entry['direct']}`"
                        f"{_s}{entry['indent']}{_n}{entry['name']}{_e}"
                    )
                sections.append("\n".join(entries))
            if content["footer"]:
                sections.append(content["footer"])
            return "\n\n".join(sections)

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

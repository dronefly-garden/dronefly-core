import functools
from typing import Union

import inflect
from pyinaturalist import (
    Taxon,
    TaxonCount,
    RANK_EQUIVALENTS,
    RANK_LEVELS,
    ROOT_TAXON_ID,
    make_tree,
)

from .source import ListPageSource
from .menu import BaseMenu
from ..models.taxon_list import TaxonListMetadata
from ..constants import RANKS_FOR_LEVEL, RANK_LEVEL_NAMES
from ..formatters import TaxonListFormatter
from ..query import QueryResponse
from ..utils import included_ranks, lifelists_url_from_query_response


p = inflect.engine()
p.defnoun("phylum", "phyla")
p.defnoun("subphylum", "subphyla")
p.defnoun("subgenus", "subgenera")


def _sort_rank_name(order):
    """Generate a sort key in `order` by rank and name."""

    def reverse_taxon_name(taxon):
        reverse_key = functools.cmp_to_key(lambda a, b: (a < b) - (a > b))
        return reverse_key(taxon.name)

    def sort_key(taxon):
        taxon_name_key = reverse_taxon_name(taxon) if order == "desc" else taxon.name
        return (taxon.rank_level or 0) * -1, taxon_name_key

    return sort_key


def _sort_rank_obs_name(order):
    """Generate a sort key in `order` by rank, descendant obs count, and name."""

    def sort_key(taxon):
        _order = 1 if order == "asc" else -1
        if getattr(taxon, "descendant_obs_count", None):
            obs_count = taxon.descendant_obs_count
        else:
            obs_count = taxon.observations_count
        return (
            (taxon.rank_level or 0) * -1,
            obs_count * _order,
            taxon.name,
        )

    return sort_key


def taxa_per_rank(
    taxon_list: list[Union[Taxon, TaxonCount]],
    ranks_to_count: Union[list[str], str],
    root_taxon_id: int = None,
    sort_by: str = None,
    order: str = None,
):
    """Generate taxa matching ranks to count in treewise order."""
    include_leaves = False
    include_ranks = None
    max_depth = 0
    if isinstance(ranks_to_count, list):
        include_ranks = ranks_to_count
    else:
        if ranks_to_count == "leaf":
            include_leaves = True
            include_ranks = None
        elif ranks_to_count == "child":
            # TODO: support make_tree(max_depth=#) in pyinat instead of the following kludge
            # TODO: support max_depth > 1 for children & grandchildren, etc.
            max_depth = 1
            # include all ranks in the tree so that ancestry isn't broken. later, we
            # filter out any taxa that aren't children. moving support for max_depth
            # into
            include_ranks = included_ranks("any")
        else:
            # single rank case:
            include_ranks = [ranks_to_count]

    # generate a sort key that uses the specified order:
    sort_key = (
        _sort_rank_obs_name(order) if sort_by == "obs" else _sort_rank_name(order)
    )

    tree = make_tree(
        taxon_list,
        include_ranks=include_ranks,
        root_id=root_taxon_id,
        sort_key=sort_key,
        # max_depth=max_depth,
    )
    root_taxon = None
    if max_depth == 1:
        if root_taxon_id:
            root_taxon = next(
                (taxon for taxon in taxon_list if taxon.id == root_taxon_id),
                taxon_list[0],
            )
        else:
            root_taxon = taxon_list[0]
    hide_root = tree.id == ROOT_TAXON_ID or include_ranks and len(include_ranks) == 1
    for taxon in tree.flatten(hide_root=hide_root):
        included = True
        # TODO: determine if the taxon is a leaf some other way if the object
        # doesn't have both both a direct & descendant count
        if include_leaves and getattr(taxon, "descendant_obs_count", None):
            included = taxon.count == taxon.descendant_obs_count
        elif max_depth == 1:
            if getattr(taxon, "ancestors", None):
                included = taxon.ancestors and taxon.ancestors[-1].id == root_taxon.id
            else:
                included = (
                    taxon.ancestor_ids and taxon.ancestor_ids[-1] == root_taxon.id
                )
        if included:
            yield taxon


def filter_taxon_list(
    taxon_list: list[Taxon],
    per_rank: Union[list[str], str],
    taxon: Taxon,
    root_taxon_id: int = None,
    sort_by: str = None,
    order: str = None,
):
    """Return filtered and ordered list supplemented with metadata.

    Parameters:
    -----------
    taxon_list: list[Taxon]
        A list of taxa.
    per_rank: Union[list[str], str]
        A rank, keyword representing a set of ranks, or list of ranks to include.
    taxon: Taxon
        The root taxon of the unfiltered, unordered list.
    root_taxon_id: int
        The optional root id of a subtree of taxa to output.
    sort_by: str
        An optional string keyword indicating the desired sort key.
    order: str
        An optional string keyword indicating the desired sort order.

    Returns
    -------
    (sorted_taxa: list[Taxon], meta: TaxonListMetadata)
        The filtered, ordered list and accumulated metadata.
        - In addition to counting and listing aspects of the result set, the taxon
          indent_levels are adjusted to flatten the list if a treewise per_rank
          was not indicated, otherwise reduce the root taxon to 0 and lower all
          taxa beneath it by the same amount.
    """
    ranks = None
    rank_totals = {}
    if per_rank in ("main", "any"):
        ranks_to_count = included_ranks(per_rank)
        if taxon:
            if per_rank == "main" and taxon.rank not in ranks_to_count:
                rank_level = RANK_LEVELS[taxon.rank]
                ranks_to_count = [
                    rank for rank in ranks_to_count if RANK_LEVELS[rank] < rank_level
                ]
                ranks_to_count.append(taxon.rank)
            else:
                ranks_to_count = ranks_to_count[: ranks_to_count.index(taxon.rank) + 1]
        ranks = "main ranks" if per_rank == "main" else "ranks"
        generate_taxa = taxa_per_rank(
            taxon_list, ranks_to_count, root_taxon_id, sort_by, order
        )
    elif per_rank in ("leaf", "child"):
        ranks = "leaf taxa" if per_rank == "leaf" else "child taxa"
        if per_rank == "child" and not root_taxon_id:
            # `per child` is only meaningful when the taxon list is for a
            # single root taxon. Otherwise, default to the first taxon (usually
            # 'Life')
            _root_taxon_id = taxon.id if taxon else taxon_list[0].id
        else:
            _root_taxon_id = root_taxon_id
        generate_taxa = taxa_per_rank(
            taxon_list, per_rank, _root_taxon_id, sort_by, order
        )
    else:
        _per_rank = per_rank
        _ranks = []
        if isinstance(per_rank, str):
            _per_rank = [per_rank]
        per_rank = []
        for _rank in _per_rank:
            rank = RANK_EQUIVALENTS[_rank] if _rank in RANK_EQUIVALENTS else _rank
            rank_name = p.plural_noun(RANK_LEVEL_NAMES[RANK_LEVELS[_rank]])
            # Add all ranks at the same level to the filter, described as
            # the most commonly used rank at that level,
            # - e.g. "genus" =>
            #   per_rank = ["genus", "genushybrid"]
            #   described as "genera"
            if rank not in per_rank:
                per_rank += RANKS_FOR_LEVEL[RANK_LEVELS[_rank]]
                _ranks.append(rank_name)
        # List of arbitrary ranks (e.g. "subfamily/species"):
        ranks = "/".join(_ranks)
        generate_taxa = taxa_per_rank(
            taxon_list, per_rank, root_taxon_id, sort_by, order
        )
    # Count ranks, # of obs/spp, and adjust indent levels:
    counted_taxa = []
    tot = {}
    max_taxon_count_digits = 1
    max_direct_count_digits = 1
    root_indent_level = None
    no_indent = per_rank not in ("main", "any")
    for _taxon in generate_taxa:
        if no_indent:
            _taxon.indent_level = 0
        else:
            if root_indent_level is None:
                root_indent_level = _taxon.indent_level
            _taxon.indent_level = _taxon.indent_level - root_indent_level
        if getattr(_taxon, "descendant_obs_count", None):
            taxon_count_digits = len(str(_taxon.descendant_obs_count))
            direct_count_digits = len(str(_taxon.count))
            if direct_count_digits > max_direct_count_digits:
                max_direct_count_digits = direct_count_digits
            if taxon_count_digits > max_taxon_count_digits:
                max_taxon_count_digits = taxon_count_digits
        else:
            taxon_count_digits = len(str(_taxon.observations_count))
            if taxon_count_digits > max_taxon_count_digits:
                max_taxon_count_digits = taxon_count_digits
        counted_taxa.append(_taxon)
        rank = _taxon.rank
        tot[rank] = tot.get(_taxon.rank, 0) + 1
    max_rank_digits = len(str(max(tot.values()))) if tot else 1
    rank_totals = {
        rank: f"`{str(tot[rank]).rjust(max_rank_digits)}` {p.plural_noun(rank, tot[rank])}"
        for rank in tot
    }
    if per_rank in ("leaf", "child"):
        # generate a sort key that uses the specified order:
        sort_key = (
            _sort_rank_obs_name(order) if sort_by == "obs" else _sort_rank_name(order)
        )
        counted_taxa.sort(key=sort_key)
    meta = TaxonListMetadata(
        ranks,
        rank_totals,
        max_taxon_count_digits,
        max_direct_count_digits,
        len(counted_taxa),
    )
    return (counted_taxa, meta)


class TaxonListSource(ListPageSource):
    """
    Attributes
    ----------
    entries: list[Taxon]
        A subset of _entries filtered and sorted according to the current
        root Taxon, filter and sort parameters.
    """

    entries: list[Taxon]

    def __init__(
        self,
        entries: list[Taxon],
        query_response: QueryResponse,
        formatter: TaxonListFormatter,
        per_page: int = 20,
        per_rank: Union[list[str], str] = "main",
        root_taxon_id: int = None,
        sort_by: str = None,
        order: str = None,
        **kwargs,
    ):
        """
        Parameters
        ----------
        entries: list[Taxon]
            Raw list of taxa including ancestors, enabling arrangement
            into a tree. This can be a life list other list of descendants
            of a common root taxon.

        query_response: QueryResponse
            The query response contains all iNat objects in the query
            except for the source itself (e.g. user, place, etc.)

        formatter: TaxonListFormatter
            Helper class that formats pages from the source.

        per_page: int, optional
            The number of taxa to include in each page.

        per_rank: list[str], str
            Rank(s) to include in list of taxa, or one of the special values:
                - 'leaf' (default) = leaf taxa
                - 'child' = all child taxa regardless of rank
                - 'main' = any of the most commonly used ranks
                - 'any' = every rank in the taxon list

        root_taxon_id: int, optional
            If specified, make the taxon with this ID the root. The taxon with
            this ID must be in the taxon list data.

        sort_by: str, optional
            If specified, sort ascending by `name` (default) or descending by number of `obs`.

        order: str, optional
            If specified, use `asc` (ascending) or `desc` (descending) as the order for the
            `sort_by` key.
        """
        self._taxon_list_formatter = formatter
        self.query_response = query_response
        self._url = (
            lifelists_url_from_query_response(self.query_response)
            if self.query_response.user
            else None
        )
        self.per_rank = per_rank
        self.root_taxon_id = root_taxon_id
        self.sort_by = sort_by
        self.order = order
        self._entries = entries
        (_entries, self.meta,) = filter_taxon_list(
            self._entries,
            self.per_rank,
            self.query_response.taxon,
            self.root_taxon_id,
            self.sort_by,
            self.order,
        )
        super().__init__(_entries, per_page=per_page, **kwargs)
        self.formatter.source = self

    def is_paginating(self):
        return True

    @property
    def formatter(self) -> TaxonListFormatter:
        return self._taxon_list_formatter

    def format_page(
        self,
        page: Union[Taxon, list[Taxon]],
        page_number: int = 0,
        selected: int = 0,
        with_summary: bool = False,
    ):
        return self.formatter.format(
            self,
            page=page,
            page_number=page_number,
            selected=selected,
            with_summary=with_summary,
        )


class TaxonListMenu(BaseMenu):
    pass

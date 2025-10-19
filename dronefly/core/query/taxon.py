import re
from typing import NamedTuple, Optional

from dronefly.core.constants import RANK_EQUIVALENTS, RANK_LEVELS
from dronefly.core.formatters.generic import format_taxon_name
from pyinaturalist.models import Taxon

from ..clients.inat import iNatClient
from .base import TaxonQuery, Query


class NameMatch(NamedTuple):
    """Match for each name field in Taxon matching a pattern."""

    term: Optional[re.match]
    name: Optional[re.match]
    common: Optional[re.match]


NO_NAME_MATCH = NameMatch(None, None, None)


def match_pat(taxon: Taxon, pat, scientific_name=False, locale=None):
    """Match specified pattern.

    Parameters
    ----------
    taxon: Taxon
        A candidate taxon to match.

    pat: re.Pattern or str
        A pattern to match against each name field in the record.

    scientific_name: bool
        Only search scientific name

    locale: str
        Only search common names matching locale

    Returns
    -------
    NameMatch
        A tuple of search results for the pat for each name in the record.
    """
    if scientific_name:
        return NameMatch(
            None,
            re.search(pat, taxon.name),
            None,
        )
    if locale:
        names = [
            name["name"]
            for name in sorted(
                [
                    name
                    for name in taxon.names
                    if name["is_valid"] and re.match(locale, name["locale"], re.I)
                ],
                key=lambda x: x["position"],
            )
        ]
        for name in names:
            mat = re.search(pat, name)
            if mat:
                return NameMatch(
                    mat,
                    None,
                    mat,
                )
        return NO_NAME_MATCH
    return NameMatch(
        re.search(pat, taxon.matched_term),
        re.search(pat, taxon.name),
        re.search(pat, taxon.preferred_common_name)
        if taxon.preferred_common_name
        else None,
    )


def match_pat_list(taxon: Taxon, pat_list, scientific_name=False, locale=None):
    """Match all of a list of patterns.

    Parameters
    ----------
    record: Taxon
        A candidate taxon to match.

    exact: list
        A list of patterns to match.

    Returns
    -------
    NameMatch
        A tuple of ORed search results for every pat for each name in
        the record, i.e. each name in the tuple is the match result from
        the first matching pattern.
    """
    matched = NO_NAME_MATCH
    try:
        for pat in pat_list:
            this_match = match_pat(taxon, pat, scientific_name, locale)
            if this_match == NO_NAME_MATCH:
                matched = this_match
                raise ValueError("At least one field must match.")
            matched = NameMatch(
                matched.term or this_match.term,
                matched.name or this_match.name,
                matched.common or this_match.common,
            )
    except ValueError:
        pass

    return matched


def score_match(
    taxon_query: TaxonQuery,
    taxon: Taxon,
    all_terms,
    pat_list=None,
    scientific_name=False,
    locale=None,
):
    """Score a matched record. A higher score is a better match.
    Parameters
    ----------
    taxon_query: TaxonQuery
        The query for the matched record being scored.

    taxon: Taxon
        A candidate taxon to match.

    all_terms: re.Pattern
        A pattern matching all terms.

    pat_list: list
        A list of patterns to match.

    Returns
    -------
    int
        score < 0 indicates the match is not a valid candidate.
        score >= 0 and score < 200 indicates a non-exact match
        score >= 200 indicates an exact match either on a phrase or the whole query
    """
    score = 0

    if taxon_query.taxon_id:
        return 1000  # An id is always the best match

    matched = (
        match_pat_list(taxon, pat_list, scientific_name, locale)
        if pat_list
        else NO_NAME_MATCH
    )
    all_matched = (
        match_pat(taxon, all_terms, scientific_name, locale)
        if taxon_query.taxon_id
        else NO_NAME_MATCH
    )

    if scientific_name:
        if matched.name:
            score = 200
        else:
            score = -1
    elif locale:
        if matched.term:
            score = 200
        else:
            score = -1
    else:
        if taxon_query.code and (taxon_query.code == taxon.matched_term):
            score = 300
        elif matched.name or matched.common:
            score = 210
        elif matched.term:
            score = 200
        elif all_matched.name or all_matched.common:
            score = 120
        elif all_matched.term:
            score = 110
        else:
            score = 100

    return score


def match_taxon_query(
    taxon_query: TaxonQuery, records, scientific_name=False, locale=None
):
    """Match a single taxon for the given query among records returned by API."""
    if taxon_query.ranks and not taxon_query.terms:
        return records[0] if records else None
    pat_list = []
    all_terms = re.compile(r"^%s$" % re.escape(" ".join(taxon_query.terms)), re.I)
    if taxon_query.phrases:
        for phrase in taxon_query.phrases:
            pat = re.compile(r"\b%s\b" % re.escape(" ".join(phrase)), re.I)
            pat_list.append(pat)
    elif scientific_name or locale:
        for term in taxon_query.terms:
            pat = re.compile(r"\b%s" % re.escape(term), re.I)
            pat_list.append(pat)
    scores = [0] * len(records)

    for num, record in enumerate(records, start=0):
        scores[num] = score_match(
            taxon_query,
            record,
            all_terms=all_terms,
            pat_list=pat_list,
            scientific_name=scientific_name,
            locale=locale,
        )

    best_score = max(scores)
    best_record = records[scores.index(best_score)]
    min_score_met = (best_score >= 0) and (
        (not taxon_query.phrases) or (best_score >= 200)
    )

    return best_record if min_score_met else None


async def get_taxon(client: iNatClient, taxon_id: int, **kwargs):
    """Get taxon by id."""
    return await anext(
        aiter(client.taxa.from_ids(taxon_id)),
        None,
    ).one()


async def get_taxon_ancestor(client: iNatClient, taxon: Taxon, rank):
    """Get Taxon ancestor for specified rank from a Taxon object.

    Parameters
    ----------
    taxon: Taxon
        The taxon for which the ancestor at the specified rank is requested.
    rank: str
        The rank of the ancestor to return.

    Returns
    -------
    Taxon
        A Taxon object for the matching ancestor, if any, else None.
    """

    def taxon_ancestor_ranks(taxon: Taxon):
        return (
            ["stateofmatter"] + [ancestor.rank for ancestor in taxon.ancestors]
            if taxon.ancestors
            else []
        )

    rank = RANK_EQUIVALENTS.get(rank) or rank
    ranks = taxon_ancestor_ranks(taxon)
    if rank in ranks:
        rank_index = ranks.index(rank)
        ancestor = await get_taxon(client, taxon.ancestor_ids[rank_index])
        return ancestor
    return None


async def _match_taxon(
    client: iNatClient,
    taxon_query: TaxonQuery,
    ancestor_id: int = None,
    preferred_place_id: int = None,
    scientific_name: bool = False,
    locale: str = None,
):
    """Get taxon and return a match, if any."""
    kwargs = {}
    taxon = None
    records_read = 0
    total_records = 0

    if locale:
        kwargs["locale"] = locale
    if preferred_place_id:
        kwargs["preferred_place_id"] = int(preferred_place_id)
    if taxon_query.taxon_id:
        taxon = await get_taxon(client, taxon_query.taxon_id)
    else:
        if taxon_query.terms:
            kwargs["q"] = " ".join(taxon_query.terms)
        if taxon_query.ranks:
            kwargs["rank"] = ",".join(taxon_query.ranks)
        if ancestor_id:
            kwargs["taxon_id"] = ancestor_id
        for page in range(11):
            if page == 0:
                per_page = 30
                endpoint = client.taxa.autocomplete
            else:
                # restart numbering, as we are using a different endpoint
                # now with different page size:
                if page == 1:
                    records_read = 0
                kwargs["page"] = page
                per_page = 200
                endpoint = client.taxa.search
            kwargs["per_page"] = per_page
            paginator = endpoint(limit=per_page, **kwargs)
            if paginator:
                records = await paginator.async_all()
                total_records = paginator.count()
            if not records:
                break
            records_read += len(records)
            taxon = match_taxon_query(
                taxon_query,
                records,
                scientific_name=scientific_name,
                locale=locale,
            )
            if taxon:
                break
            if records_read >= total_records:
                break

    if not taxon:
        if records_read >= total_records:
            raise LookupError("No matching taxon found.")

        raise LookupError(
            f"No {'exact ' if taxon_query.phrases else ''}match "
            f"found in {'scientific name of ' if scientific_name else ''}{records_read}"
            f" of {total_records} total records containing those terms."
        )

    return taxon


async def match_taxon(
    client: iNatClient,
    query: Query,
    preferred_place_id=None,
    scientific_name=False,
    locale=None,
):
    """Get one or more taxa and return a match, if any.

    Currently the grammar supports only one ancestor taxon
    and one child taxon.
    """
    if query.ancestor:
        ancestor = None
        try:
            ancestor = await _match_taxon(
                client,
                query.ancestor,
                preferred_place_id=preferred_place_id,
                scientific_name=scientific_name,
                locale=locale,
            )
            if ancestor:
                if query.main.ranks:
                    max_query_rank_level = max(
                        [RANK_LEVELS[rank] for rank in query.main.ranks]
                    )
                    ancestor_rank_level = RANK_LEVELS[ancestor.rank]
                    if max_query_rank_level >= ancestor_rank_level:
                        raise LookupError(
                            "Child rank%s: `%s` must be below ancestor rank: `%s`"
                            % (
                                "s" if len(query.main.ranks) > 1 else "",
                                ",".join(query.main.ranks),
                                ancestor.rank,
                            )
                        )
                taxon = await _match_taxon(
                    client,
                    query.main,
                    ancestor_id=ancestor.id,
                    preferred_place_id=preferred_place_id,
                    scientific_name=scientific_name,
                    locale=locale,
                )
        except LookupError as err:
            reason = (
                str(err) + "\nPerhaps instead of `in` (ancestor), you meant\n"
                "`from` (place) or `in prj` (project)?"
            )
            if ancestor:
                reason = (
                    f"{reason}\n\n"
                    f"Ancestor taxon: {format_taxon_name(ancestor, with_term=True)}"
                )
            else:
                reason = f"{reason}\n\nAncestor taxon not found."
            raise LookupError(reason) from err
    else:
        taxon = await _match_taxon(
            client,
            query.main,
            preferred_place_id=preferred_place_id,
            scientific_name=scientific_name,
            locale=locale,
        )

    return taxon

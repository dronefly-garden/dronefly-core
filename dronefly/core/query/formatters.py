import copy

from dronefly.core.formatters.generic import (
    CountFormatter,
    CountsFormatter,
    QualifiedTaxonFormatter,
)
from dronefly.core.menus.count import CountSource
from dronefly.core.menus.counts import CountsSource
from dronefly.core.query.query import get_query_count


async def get_query_counts_formatter(client, query_response, count):
    counts_formatter = None
    counts_page = None
    if count:
        counts_formatter = CountsFormatter()
        counts_source = CountsSource(
            entries=[count],
            query_response=query_response,
            inat_client=client,
            counts_formatter=counts_formatter,
            per_page=15,  # FIXME: magic number!
        )
        counts_formatter.source = counts_source
        counts_page = await counts_source.get_page(page_number=0)
    return (counts_formatter, counts_page)


async def get_query_count_formatter(client, query_response):
    """Populate count formatter with iNat entities supplying additional details."""
    formatter_params = {}
    # Supplement the summary count with optional counts if specified
    # in the query (e.g. `from`, `by`, `by id`, etc.)
    counts_formatter = None
    counts_page = None
    count = await get_query_count(client, query_response)
    # adds first count from the query to the first page
    (counts_formatter, counts_page) = await get_query_counts_formatter(
        client, query_response, count
    )
    formatter_params["counts_formatter"] = counts_formatter
    formatter_params["counts_page"] = counts_page
    title_query_response = copy.copy(query_response)
    setattr(title_query_response, query_response.countable_attr, None)
    title_count = await get_query_count(client, title_query_response, summary=True)
    count_formatter = CountFormatter(
        title_query_response,
        **formatter_params,
    )
    count_source = CountSource(title_count, count_formatter)
    count_formatter.source = count_source
    return count_formatter


async def get_query_taxon_formatter(client, query_response, **formatter_params):
    """Populate taxon formatter with iNat entities supplying additional details."""
    _formatter_params = formatter_params
    place = query_response.place
    if place:
        taxon = await client.taxa.populate(
            query_response.taxon, preferred_place_id=place.id
        )
    else:
        taxon = await client.taxa.populate(query_response.taxon)
    _formatter_params["taxon"] = taxon
    user = query_response.user
    counts_formatter = None
    counts_page = None
    if query_response.countable:
        count = await get_query_count(client, query_response)
        if count:
            # adds first count from the query to the first page
            (counts_formatter, counts_page) = await get_query_counts_formatter(
                client, query_response, count
            )
            _formatter_params["counts_formatter"] = counts_formatter
            _formatter_params["counts_page"] = counts_page
    title_query_response = copy.copy(query_response)
    if user:
        title_query_response.user = None
    elif place:
        title_query_response.place = None
    obs_args = title_query_response.obs_args()
    # i.e. any args other than the ones accounted for in taxon.observations_count
    if [arg for arg in obs_args if arg != "taxon_id"]:
        _formatter_params["observations"] = client.observations.search(
            per_page=0, **obs_args
        )
    taxon_formatter = QualifiedTaxonFormatter(
        title_query_response,
        **_formatter_params,
    )
    return taxon_formatter

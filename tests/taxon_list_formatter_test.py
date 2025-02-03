import pytest
from unittest.mock import Mock
from dronefly.core.formatters.generic import TaxonListFormatter
from dronefly.core.menus.taxon_list import TaxonListMetadata
from dronefly.core.query import QueryResponse
from pyinaturalist import Taxon, User, ROOT_TAXON_ID


@pytest.fixture
def mock_query_response(mock_taxa):
    params = {
        "obs_args.return_value": {"user": 1},
        "obs_query_description.return_value": "of taxa by test_user",
    }
    query_response = Mock(spec=QueryResponse, **params)
    query_response.taxon = mock_taxa[0]
    query_response.user = Mock(spec=User)
    query_response.user.id = 1
    query_response.user.login = "test_user"
    return query_response


@pytest.fixture
def mock_taxa():
    taxa = []
    for i in range(50):
        rank = [
            "stateofmatter",
            "kingdom",
            "phylum",
            "class",
            "order",
            "family",
            "genus",
            "species",
        ][min(i, 7)]
        count = 1 if rank == "species" else 43
        params = {
            "id": ROOT_TAXON_ID if i == 0 else i,
            "name": "Life" if i == 0 else f"Taxon {i}",
            "rank": rank,
            "ancestor_ids": [taxon.id for taxon in taxa],
            "parent_id": taxa[-1].id if taxa else None,
            "partial": True,
            "observations_count": count,
            "is_active": True,
        }
        taxa.append(Taxon(**params))
    return taxa


@pytest.fixture
def mock_meta():
    return TaxonListMetadata(
        ranks="main ranks",
        rank_totals={
            "stateofmatter": 1,
            "kingdom": 1,
            "phylum": 1,
            "class": 1,
            "order": 1,
            "family": 1,
            "genus": 1,
            "species": 43,
        },
        count_digits=2,
        direct_digits=2,
        taxon_count=50,
    )


@pytest.fixture
def mock_source(mock_taxa, mock_query_response, mock_meta):
    params = {"get_max_pages.return_value": 3}
    source = Mock(**params)
    source.entries = mock_taxa
    source.query_response = mock_query_response
    source.meta = mock_meta
    source.per_page = 10
    return source


@pytest.fixture
def mock_menu():
    menu = Mock()
    return menu


def test_initialization(mock_query_response, mock_taxa):
    formatter = TaxonListFormatter(
        with_url=True,
        with_taxa=True,
        with_indent=False,
        with_index=False,
        with_direct=False,
        with_common=False,
        short_description="Life list",
    )
    assert formatter.with_url is True
    assert formatter.with_taxa is True
    assert formatter.with_indent is False
    assert formatter.with_index is False
    assert formatter.with_direct is False
    assert formatter.with_common is False
    assert formatter.short_description == "Life list"


def test_format(mock_source):
    formatter = TaxonListFormatter()
    formatter.source = mock_source
    page = mock_source.entries[:10]
    formatted_page = formatter.format(page, 1, 0)
    expected_output = """[Life list of taxa by test_user](https://www.inaturalist.org/lifelists/test_user)

`43`>**__[Stateofmatter Life](https://www.inaturalist.org/observations?user=1&taxon_id=48460)__**
`43` └ [Kingdom Taxon 1](https://www.inaturalist.org/observations?user=1&taxon_id=1)
`43`     └ [Phylum Taxon 2](https://www.inaturalist.org/observations?user=1&taxon_id=2)
`43`         └ [Class Taxon 3](https://www.inaturalist.org/observations?user=1&taxon_id=3)
`43`             └ [Order Taxon 4](https://www.inaturalist.org/observations?user=1&taxon_id=4)
`43`                 └ [Family Taxon 5](https://www.inaturalist.org/observations?user=1&taxon_id=5)
`43`                     └ [Genus *Taxon 6*](https://www.inaturalist.org/observations?user=1&taxon_id=6)
` 1`                         └ [*Taxon 7*](https://www.inaturalist.org/observations?user=1&taxon_id=7)
` 1`                         └ [*Taxon 8*](https://www.inaturalist.org/observations?user=1&taxon_id=8)
` 1`                         └ [*Taxon 9*](https://www.inaturalist.org/observations?user=1&taxon_id=9)"""  # noqa: E501
    assert formatted_page == expected_output

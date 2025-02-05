import pytest
from unittest.mock import Mock
from dronefly.core.menus.taxon_list import TaxonListSource
from dronefly.core.formatters import TaxonListFormatter
from dronefly.core.query import QueryResponse
from pyinaturalist import Taxon, User, ROOT_TAXON_ID


@pytest.fixture
def mock_taxa():
    taxa = []
    for i in range(50):
        max_rank_index = min(i, 7)
        if i == 0:
            id = ROOT_TAXON_ID
            name = "Life"
            parent_id = None
            ancestor_ids = []
        else:
            id = i
            name = f"Taxon {i:02}"
            max_ancestor_index = max_rank_index - 1
            parent_id = taxa[max_ancestor_index].id
            ancestor_ids = [taxon.id for taxon in taxa[:max_rank_index]]
        rank = [
            "stateofmatter",
            "kingdom",
            "phylum",
            "class",
            "order",
            "family",
            "genus",
            "species",
        ][max_rank_index]
        params = {
            "id": id,
            "name": name,
            "rank": rank,
            "ancestor_ids": ancestor_ids,
            "parent_id": parent_id,
            "partial": True,
            "is_active": True,
        }
        taxa.append(Taxon(**params))
    return taxa


@pytest.fixture
def mock_query_response(mock_taxa):
    query_response = Mock(spec=QueryResponse)
    query_response.taxon = mock_taxa[0]
    query_response.user = Mock(spec=User)
    query_response.user.id = 1
    query_response.user.login = "test_user"
    return query_response


@pytest.fixture
def mock_formatter(mock_taxa, mock_query_response):
    attrs = {"format.return_value": "Formatted Page"}
    formatter = Mock(spec=TaxonListFormatter, **attrs)
    return formatter


def test_initialization(mock_formatter, mock_query_response, mock_taxa):
    source = TaxonListSource(mock_taxa, mock_query_response, mock_formatter)
    assert len(source.entries) == len(mock_taxa)
    assert [entry.name for entry in source.entries] == [
        taxon.name for taxon in mock_taxa
    ]
    assert source.query_response == mock_query_response
    assert source.formatter == mock_formatter


@pytest.mark.asyncio
async def test_pagination(mock_formatter, mock_query_response, mock_taxa):
    source = TaxonListSource(mock_taxa, mock_query_response, mock_formatter)
    page = await source.get_page(0)
    assert len(page) == 20
    assert page[0].id == 48460
    assert page[-1].id == 19

    page = await source.get_page(1)
    assert len(page) == 20
    assert page[0].id == 20
    assert page[-1].id == 39


@pytest.mark.asyncio
async def test_formatting(mock_formatter, mock_query_response, mock_taxa):
    source = TaxonListSource(mock_taxa, mock_query_response, mock_formatter)
    page = await source.get_page(0)
    formatted_page = source.format_page(page=page, page_number=0, selected=0)
    assert formatted_page == "Formatted Page"
    source.formatter.format.assert_called_once_with(
        source, page=page, page_number=0, selected=0, with_summary=False
    )

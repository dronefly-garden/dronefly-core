import pytest
from unittest.mock import Mock
from dronefly.core.menus.menu import BaseMenu
from dronefly.core.menus.taxon_list import TaxonListSource
from dronefly.core.formatters import TaxonListFormatter
from dronefly.core.query import QueryResponse
from pyinaturalist import Taxon, User, ROOT_TAXON_ID


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
        params = {
            "id": ROOT_TAXON_ID if i == 0 else i,
            "name": f"Taxon {i}",
            "rank": rank,
            "ancestor_ids": [taxon.id for taxon in taxa],
            "parent_id": taxa[-1].id if taxa else None,
            "partial": True,
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
    assert source.entries == mock_taxa
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
    menu = Mock(spec=BaseMenu, source=source)
    page = await source.get_page(0)
    formatted_page = source.format_page(menu=menu, page=page)
    assert formatted_page == "Formatted Page"
    source.formatter.format.assert_called_once_with(
        source, menu=menu, page=page, summary=False
    )

import pytest
from unittest.mock import Mock
from dronefly.core.menus.user_counts import UserCountsSource
from dronefly.core.formatters import UserCountsFormatter
from dronefly.core.query import QueryResponse
from pyinaturalist import UserCount


@pytest.fixture
def mock_user_counts():
    return [
        UserCount.from_json(
            {
                "user_id": i,
                "user": {
                    "id": i,
                    "login": f"user{i}",
                    "name": f"User {i}",
                    "observation_count": i,
                    "species_count": i,
                },
            }
        )
        for i in range(1, 50)
    ]


@pytest.fixture
def mock_query_response(mock_user_counts):
    query_response = Mock(spec=QueryResponse)
    query_response.taxon = mock_user_counts[0]
    return query_response


@pytest.fixture
def mock_formatter(mock_user_counts, mock_query_response):
    attrs = {"format_page.return_value": "Formatted Page"}
    formatter = Mock(spec=UserCountsFormatter, **attrs)
    return formatter


def test_initialization(mock_formatter, mock_query_response, mock_user_counts):
    source = UserCountsSource(
        mock_user_counts, mock_query_response, mock_formatter, per_page=20
    )
    assert len(source.entries) == len(mock_user_counts)
    assert [entry.name for entry in source.entries] == [
        taxon.name for taxon in mock_user_counts
    ]
    assert source.query_response == mock_query_response
    assert source.formatter == mock_formatter


@pytest.mark.asyncio
async def test_pagination(mock_formatter, mock_query_response, mock_user_counts):
    source = UserCountsSource(
        mock_user_counts, mock_query_response, mock_formatter, per_page=20
    )
    page = await source.get_page(0)
    assert len(page) == 20
    assert page[0].id == 1
    assert page[-1].id == 20

    page = await source.get_page(1)
    assert len(page) == 20
    assert page[0].id == 21
    assert page[-1].id == 40


@pytest.mark.asyncio
async def test_formatting(mock_formatter, mock_query_response, mock_user_counts):
    source = UserCountsSource(
        mock_user_counts, mock_query_response, mock_formatter, per_page=20
    )
    page = await source.get_page(0)
    formatted_page = source.format_page(page=page)
    assert formatted_page == "Formatted Page"
    source.formatter.format_page.assert_called_once_with(page)

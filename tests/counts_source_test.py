import copy
import pytest
from unittest.mock import Mock, patch
from dronefly.core.clients.inat import iNatClient
from dronefly.core.menus.counts import CountsSource
from dronefly.core.formatters import CountsFormatter
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
                    "observation_count": i + 1,
                    "species_count": i,
                },
            }
        )
        for i in range(1, 50)
    ]


@pytest.fixture
def mock_total(mock_user_counts):
    user_counts_total = copy.copy(mock_user_counts[-1])
    user_counts_total.id = -1
    user_counts_total.login = "*Total*"
    user_counts_total.observation_count = 500
    return user_counts_total


@pytest.fixture
def mock_inat_client():
    return Mock(spec=iNatClient)


@pytest.fixture
def mock_query_response(mock_user_counts):
    query_response = Mock(spec=QueryResponse)
    query_response.user = mock_user_counts[0]
    return query_response


@pytest.fixture
def mock_formatter(mock_user_counts, mock_query_response):
    attrs = {"format_page.return_value": "Formatted Page"}
    formatter = Mock(spec=CountsFormatter, **attrs)
    return formatter


def test_initialization(
    mock_formatter, mock_inat_client, mock_query_response, mock_user_counts
):
    source = CountsSource(
        mock_user_counts,
        mock_inat_client,
        mock_query_response,
        mock_formatter,
        per_page=20,
    )
    assert len(source.entries) == len(mock_user_counts)
    assert [entry.name for entry in source.entries] == [
        user.name for user in mock_user_counts
    ]
    assert source.query_response == mock_query_response
    assert source.formatter == mock_formatter


@pytest.mark.asyncio
async def test_pagination(
    mock_formatter, mock_inat_client, mock_query_response, mock_user_counts, mock_total
):
    with patch(
        "dronefly.core.menus.counts.get_user_count_total", return_value=mock_total
    ):
        source = CountsSource(
            mock_user_counts,
            mock_inat_client,
            mock_query_response,
            mock_formatter,
            per_page=20,
        )
        page = await source.get_page(0)
        assert len(page) == 21
        assert page[0].id == 1
        assert page[-2].id == 20
        assert page[-1].id == -1

        page = await source.get_page(1)
        assert len(page) == 21
        assert page[0].id == 21
        assert page[-2].id == 40
        assert page[-1].id == -1


@pytest.mark.asyncio
async def test_formatting(
    mock_formatter, mock_inat_client, mock_query_response, mock_user_counts, mock_total
):
    with patch(
        "dronefly.core.menus.counts.get_user_count_total", return_value=mock_total
    ):
        source = CountsSource(
            mock_user_counts,
            mock_inat_client,
            mock_query_response,
            mock_formatter,
            per_page=20,
        )
        page = await source.get_page(0)
        formatted_page = source.format_page(page=page)
        assert formatted_page == "Formatted Page"
        source.formatter.format_page.assert_called_once_with(page)

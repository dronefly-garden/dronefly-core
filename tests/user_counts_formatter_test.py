import pytest
from unittest.mock import Mock
from dronefly.core.formatters.generic import UserCountsFormatter, TAXON_COUNTS_HEADER
from dronefly.core.query import QueryResponse
from pyinaturalist import UserCount


@pytest.fixture
def mock_query_response(mock_user_counts):
    user_count = mock_user_counts[0]
    params = {
        "obs_args.return_value": {"user_id": user_count.id, "taxon_id": 1},
        "obs_query_description.return_value": f"of taxa by {user_count.login}",
    }
    query_response = Mock(spec=QueryResponse, **params)
    return query_response


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
        for i in range(1, 3)
    ]


@pytest.fixture
def mock_source(mock_user_counts, mock_query_response):
    params = {"get_max_pages.return_value": 1}
    source = Mock(**params)
    source.entries = mock_user_counts
    source.query_response = mock_query_response
    source.per_page = 10
    return source


@pytest.fixture
def mock_menu():
    menu = Mock()
    return menu


def test_initialization(mock_source, mock_user_counts):
    formatter = UserCountsFormatter()
    formatter.source = mock_source
    assert formatter.source.entries == mock_user_counts


def test_format(mock_source):
    formatter = UserCountsFormatter()
    formatter.source = mock_source
    page = mock_source.entries[:10]
    formatted_page = formatter.format_page(page)
    expected_output = TAXON_COUNTS_HEADER + (
        "\n[2 (1)](https://www.inaturalist.org/observations?user_id=1&taxon_id=1) user1 \n"
        "[3 (2)](https://www.inaturalist.org/observations?user_id=2&taxon_id=1) user2 "
    )
    assert formatted_page == expected_output

import pytest
from unittest.mock import Mock
from dronefly.core.formatters.generic import (
    CountsFormatter,
    TAXON_COUNTS_HEADER,
    TAXON_PLACES_HEADER,
)
from dronefly.core.models import PlaceCount
from dronefly.core.query import QueryResponse
from pyinaturalist import UserCount


@pytest.fixture
def mock_user_query_response(mock_user_counts):
    user_count = mock_user_counts[0]
    params = {
        "obs_args.return_value": {"taxon_id": 1},
        "obs_query_description.return_value": f"of taxa by {user_count.login}",
    }
    query_response = Mock(spec=QueryResponse, **params)
    return query_response


@pytest.fixture
def mock_place_query_response(mock_place_counts):
    place_count = mock_place_counts[0]
    params = {
        "obs_args.return_value": {"taxon_id": 1},
        "obs_query_description.return_value": f"of taxa by {place_count.name}",
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
def mock_place_counts():
    return [
        PlaceCount.from_json(
            {
                "place_id": i,
                "place": {
                    "id": i,
                    "name": f"Place {i}",
                    "observation_count": i + 1,
                    "species_count": i,
                },
            }
        )
        for i in range(1, 3)
    ]


@pytest.fixture
def mock_user_source(mock_user_counts, mock_user_query_response):
    params = {"get_max_pages.return_value": 1}
    source = Mock(**params)
    source.entries = mock_user_counts
    source.query_response = mock_user_query_response
    source.per_page = 10
    return source


@pytest.fixture
def mock_place_source(mock_place_counts, mock_place_query_response):
    params = {"get_max_pages.return_value": 1}
    source = Mock(**params)
    source.entries = mock_place_counts
    source.query_response = mock_place_query_response
    source.per_page = 10
    return source


@pytest.fixture
def mock_menu():
    menu = Mock()
    return menu


def test_user_initialization(mock_user_source, mock_user_counts):
    formatter = CountsFormatter()
    formatter.source = mock_user_source
    assert formatter.source.entries == mock_user_counts


def test_place_initialization(mock_place_source, mock_place_counts):
    formatter = CountsFormatter()
    formatter.source = mock_place_source
    assert formatter.source.entries == mock_place_counts


def test_user_format(mock_user_source):
    formatter = CountsFormatter()
    formatter.source = mock_user_source
    page = mock_user_source.entries[:10]
    formatted_page = formatter.format_page(page)
    expected_output = TAXON_COUNTS_HEADER + (
        "\n[2 (1)](https://www.inaturalist.org/observations?taxon_id=1&user_id=1) user1 \n"
        "[3 (2)](https://www.inaturalist.org/observations?taxon_id=1&user_id=2) user2 "
    )
    assert formatted_page == expected_output


def test_place_format(mock_place_source):
    formatter = CountsFormatter()
    formatter.source = mock_place_source
    page = mock_place_source.entries[:10]
    print("page=", page)
    formatted_page = formatter.format_page(page)
    expected_output = TAXON_PLACES_HEADER + (
        "\n[2 (1)](https://www.inaturalist.org/observations?taxon_id=1&place_id=1) Place 1 \n"
        "[3 (2)](https://www.inaturalist.org/observations?taxon_id=1&place_id=2) Place 2 "
    )
    assert formatted_page == expected_output

import pytest
from unittest.mock import Mock
from dronefly.core.formatters.generic import ObservationListFormatter
from dronefly.core.query import QueryResponse
from pyinaturalist import Observation, User


@pytest.fixture
def mock_user():
    return Mock(spec=User, id=1, login="test_user")


@pytest.fixture
def mock_observations(mock_user):
    observations = []
    for id in range(50):
        taxon_id = int(id / 10) + 1
        taxon = {
            "id": taxon_id,
            "name": f"Genus1 species{id:02}",
        }
        params = {
            "id": id,
            "taxon": taxon,
            "user": mock_user,
        }
        observations.append(Observation(**params))
    return observations


@pytest.fixture
def mock_query_response(mock_observations, mock_user):
    params = {
        "obs_args.return_value": {"user": 1},
        "obs_query_description.return_value": "of taxa by test_user",
    }
    query_response = Mock(
        spec=QueryResponse, user=mock_user, observations=mock_observations, **params
    )
    return query_response


@pytest.fixture
def mock_source(mock_observations, mock_query_response):
    params = {"get_max_pages.return_value": 3}
    source = Mock(**params)
    source.entries = mock_observations
    source.query_response = mock_query_response
    source.per_page = 10
    return source


@pytest.fixture
def mock_menu():
    menu = Mock()
    return menu


def test_initialization():
    formatter = ObservationListFormatter(
        with_url=True,
    )
    assert formatter.with_url is True


def test_format(mock_source):
    formatter = ObservationListFormatter()
    formatter.source = mock_source
    page = mock_source.entries[:10]
    formatted_page = formatter.format(page, 1, 0)
    expected_output = """[Observations of taxa by test_user](https://www.inaturalist.org/observations?user=1)\n\n"""  # noqa: E501
    assert formatted_page == expected_output

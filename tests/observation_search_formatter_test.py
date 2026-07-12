import pytest
from unittest.mock import Mock
from dronefly.core.formatters.generic import ObservationSearchFormatter
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
            "is_active": True,
            "name": f"Genus1 species{id:02}",
            "rank": "species",
            "rank_level": 10,
        }
        day = int(id / 25) + 1
        min = int(day / 2)
        params = {
            "id": id + 1,
            "observed_on": f"2025-07-{day:02}T13:{min:02}:00",
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
    formatter = ObservationSearchFormatter(
        with_url=True,
    )
    assert formatter.with_url is True


def test_format(mock_source):
    formatter = ObservationSearchFormatter()
    formatter.source = mock_source
    page = mock_source.entries[:10]
    formatted_page = formatter.format(page, 1, 0)
    expected_output = """[Search: Observations of taxa by test_user](https://www.inaturalist.org/observations?user=1)

`Jul-2025`>**__[*Genus1 species00*](https://www.inaturalist.org/observations/1)__**
`Jul-2025` [*Genus1 species01*](https://www.inaturalist.org/observations/2)
`Jul-2025` [*Genus1 species02*](https://www.inaturalist.org/observations/3)
`Jul-2025` [*Genus1 species03*](https://www.inaturalist.org/observations/4)
`Jul-2025` [*Genus1 species04*](https://www.inaturalist.org/observations/5)
`Jul-2025` [*Genus1 species05*](https://www.inaturalist.org/observations/6)
`Jul-2025` [*Genus1 species06*](https://www.inaturalist.org/observations/7)
`Jul-2025` [*Genus1 species07*](https://www.inaturalist.org/observations/8)
`Jul-2025` [*Genus1 species08*](https://www.inaturalist.org/observations/9)
`Jul-2025` [*Genus1 species09*](https://www.inaturalist.org/observations/10)"""  # noqa: E501
    assert formatted_page == expected_output

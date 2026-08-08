# flake8: noqa
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
    formatter = ObservationSearchFormatter(
        with_summaries=True,
    )
    formatter.source = mock_source
    page = mock_source.entries[:10]
    formatted_page = formatter.format(page, 1, 0)
    expected_title = (
        "[Search: Observations of taxa by test_user]"
        "(https://www.inaturalist.org/observations?user=1)\n"
    )
    en = "\N{EN SPACE}"
    indent = f"\N{ZERO WIDTH SPACE}{en}"
    icon = "\N{REPLACEMENT CHARACTER}"
    sel = "\N{BLACK RIGHT-POINTING SMALL TRIANGLE}"
    expected_link = lambda n: (
        f"[*Genus1 species{str(n).zfill(2)}*]"
        f"(https://www.inaturalist.org/observations/{n + 1})"
    )
    expected_summary = f"{en}`Jul-2025                        `{en}{icon}"
    expected_obs = lambda n: "\n".join(
        (f"{indent}{expected_link(n)}", expected_summary)
    )
    expected_sel = "\n".join((f"{sel}**__{expected_link(0)}__**", expected_summary))
    expected_output = "\n".join(
        (expected_title, expected_sel, *(expected_obs(n) for n in range(1, 10)))
    )
    assert formatted_page == expected_output

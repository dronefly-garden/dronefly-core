import pytest
from unittest.mock import Mock
from dronefly.core.menus.observation_list import ObservationListSource
from dronefly.core.formatters import ObservationListFormatter
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
    query_response = Mock(
        spec=QueryResponse, user=mock_user, observations=mock_observations
    )
    return query_response


@pytest.fixture
def mock_formatter():
    attrs = {"format.return_value": "Formatted Page"}
    formatter = Mock(spec=ObservationListFormatter, **attrs)
    return formatter


def test_initialization(mock_formatter, mock_query_response, mock_observations):
    source = ObservationListSource(
        mock_observations, mock_query_response, mock_formatter
    )
    assert len(source.entries) == len(mock_observations)
    assert [entry.id for entry in source.entries] == [
        obs.id for obs in mock_observations
    ]
    assert source.query_response == mock_query_response
    assert source.formatter == mock_formatter


@pytest.mark.asyncio
async def test_pagination(mock_formatter, mock_query_response, mock_observations):
    source = ObservationListSource(
        mock_observations, mock_query_response, mock_formatter
    )
    page = await source.get_page(0)
    assert len(page) == 20
    assert page[-1].id == 19

    page = await source.get_page(1)
    assert len(page) == 20
    assert page[0].id == 20
    assert page[-1].id == 39


@pytest.mark.asyncio
async def test_formatting(mock_formatter, mock_query_response, mock_observations):
    source = ObservationListSource(
        mock_observations, mock_query_response, mock_formatter
    )
    page = await source.get_page(0)
    formatted_page = source.format_page(page=page, page_number=0, selected=0)
    assert formatted_page == "Formatted Page"
    source.formatter.format.assert_called_once_with(
        source, page=page, page_number=0, selected=0
    )

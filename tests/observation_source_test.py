import pytest
from unittest.mock import Mock
from dronefly.core.menus.observation_search import ObservationSearchSource
from dronefly.core.formatters import ObservationSearchFormatter
from dronefly.core.query import QueryResponse
from pyinaturalist import Observation, User


@pytest.fixture
def mock_user():
    return Mock(spec=User, id=1, login="test_user")


@pytest.fixture
def mock_observations_list(mock_user):
    observations = []
    for id in range(1, 51):
        taxon_id = int(id / 10)
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


async def async_obs_gen(data):
    for obs in data:
        yield obs


@pytest.fixture
def mock_query_response(mock_user):
    query_response = Mock(spec=QueryResponse, user=mock_user)
    return query_response


@pytest.fixture
def mock_formatter():
    attrs = {"format.return_value": "Formatted Page"}
    formatter = Mock(spec=ObservationSearchFormatter, **attrs)
    return formatter


@pytest.mark.asyncio
async def test_initialization(
    mock_formatter, mock_query_response, mock_observations_list
):
    iterator = async_obs_gen(mock_observations_list)
    source = ObservationSearchSource(iterator, mock_query_response, mock_formatter)
    await source.prepare()
    assert len(source._cache) == 21
    expected_ids = [i for i in range(1, 22)]
    assert [entry.id for entry in source._cache] == expected_ids
    assert source.query_response == mock_query_response
    assert source.formatter == mock_formatter


@pytest.mark.asyncio
async def test_pagination(mock_formatter, mock_query_response, mock_observations_list):
    iterator = async_obs_gen(mock_observations_list)
    source = ObservationSearchSource(iterator, mock_query_response, mock_formatter)
    page = await source.get_page(0)
    assert len(page) == 20
    assert page[-1].id == 20

    page = await source.get_page(1)
    assert len(page) == 20
    assert page[0].id == 21
    assert page[-1].id == 40


@pytest.mark.asyncio
async def test_formatting(mock_formatter, mock_query_response, mock_observations_list):
    iterator = async_obs_gen(mock_observations_list)
    source = ObservationSearchSource(iterator, mock_query_response, mock_formatter)
    page = await source.get_page(0)
    formatted_page = source.format_page(page=page, page_number=0, selected=0)
    assert formatted_page == "Formatted Page"
    source.formatter.format.assert_called_once_with(
        source, page=page, page_number=0, selected=0
    )

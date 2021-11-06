"""Test INatAPI."""
from unittest.mock import AsyncMock

import pytest
from ..apis.inat import INatAPI

# pylint: disable=missing-function-docstring


@pytest.fixture(name="inat_api")
async def fixture_inat_api():
    return INatAPI()


@pytest.fixture(name="mock_response")
def fixture_mock_response(mocker):
    async_mock = AsyncMock()
    mocker.patch.object(INatAPI, "_get_rate_limited", side_effect=async_mock)
    return async_mock


pytestmark = pytest.mark.asyncio


async def test_get_taxa_by_id(inat_api, mock_response):
    mock_response.return_value = {"results": [{"name": "Animalia"}]}
    taxon = await inat_api.get_taxa(1)
    assert taxon["results"][0]["name"] == "Animalia"


async def test_get_taxa_by_query(inat_api, mock_response):
    mock_response.return_value = {"results": [{"name": "Animalia"}]}
    taxon = await inat_api.get_taxa(q="animals")
    assert taxon["results"][0]["name"] == "Animalia"


async def test_get_observation_bounds_no_ids(inat_api, mock_response):
    mock_response.return_value = {}
    bounds = await inat_api.get_observation_bounds([])
    assert bounds is None


async def test_get_observation_bounds_no_coords(inat_api, mock_response):
    mock_response.return_value = {}
    bounds = await inat_api.get_observation_bounds(["1"])
    assert bounds is None


async def test_get_observation_bounds(inat_api, mock_response):
    valid_result = {"total_bounds": {"swlat": 1, "swlng": 2, "nelat": 3, "nelng": 4}}
    mock_response.return_value = valid_result
    bounds = await inat_api.get_observation_bounds(["1"])
    assert bounds == valid_result["total_bounds"]


async def test_get_users_by_id(inat_api, mock_response):
    mock_response.return_value = {"results": [{"id": 545640, "login": "benarmstrong"}]}
    users = await inat_api.get_users(545640, refresh_cache=True)
    assert users["results"][0]["login"] == "benarmstrong"


async def test_get_users_by_login(inat_api, mock_response):
    mock_response.return_value = {"results": [{"id": 545640, "login": "benarmstrong"}]}
    users = await inat_api.get_users("benarmstrong", refresh_cache=True)
    assert users["results"][0]["login"] == "benarmstrong"


async def test_get_users_by_name(inat_api, mock_response):
    mock_response.return_value = {
        "results": [
            {"id": 545640, "login": "benarmstrong"},
            {"id": 2, "login": "bensomebodyelse"},
        ]
    }
    users = await inat_api.get_users("Ben Armstrong", refresh_cache=True)
    assert users["results"][1]["login"] == "bensomebodyelse"

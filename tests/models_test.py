# pylint: disable=missing-class-docstring disable=no-self-use disable=missing-function-docstring
import pytest

from dronefly.core.models import Config, load_config


@pytest.fixture
def test_places():
    return {"ns": 6853}


@pytest.fixture
def test_projects():
    return {"ever": 48611}


@pytest.fixture
def test_users(test_places):
    return {"1": {"inat_user_id": 585640, "inat_place_id": test_places["ns"]}}


@pytest.fixture
def test_config():
    return """[places]
ns = 6853
[projects]
ever = 48611
[users.1]
inat_user_id = 585640
inat_place_id = 6853
"""


class TestModels:
    def test_empty_config(self):
        config = Config()
        assert config.places == {}
        assert config.projects == {}
        assert config.users == {}

    @pytest.mark.asyncio(scope="session")
    async def test_config(self, test_projects, test_places, test_users):
        config = Config(projects=test_projects, places=test_places, users=test_users)
        assert await config.place_id("ns") == test_places["ns"]
        assert await config.place_id("xyz") is None
        assert await config.project_id("ever") == test_projects["ever"]
        assert await config.project_id("xyz") is None
        assert await config.user(1) == test_users.get("1")
        assert await config.user_id(1) == test_users.get("1").get("inat_user_id")

    @pytest.mark.asyncio(scope="session")
    async def test_load_config(
        self, test_projects, test_places, test_users, test_config
    ):
        config = load_config(test_config)
        assert await config.place_id("ns") == test_places["ns"]
        assert await config.place_id("xyz") is None
        assert await config.project_id("ever") == test_projects["ever"]
        assert await config.project_id("xyz") is None
        assert await config.user(1) == test_users.get("1")
        assert await config.user_id(1) == test_users.get("1").get("inat_user_id")

# pylint: disable=missing-class-docstring disable=no-self-use disable=missing-function-docstring
import pytest

from dronefly.core.models import Workspace, load_workspace


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
        workspace = Workspace()
        assert workspace.places == {}
        assert workspace.projects == {}
        assert workspace.users == {}

    @pytest.mark.asyncio(loop_scope="session")
    async def test_config(self, test_projects, test_places, test_users):
        workspace = Workspace(
            projects=test_projects, places=test_places, users=test_users
        )
        assert await workspace.place_id("ns") == test_places["ns"]
        assert await workspace.place_id("xyz") is None
        assert await workspace.project_id("ever") == test_projects["ever"]
        assert await workspace.project_id("xyz") is None
        assert await workspace.user(1) == test_users.get("1")
        assert await workspace.user_id(1) == test_users.get("1").get("inat_user_id")

    @pytest.mark.asyncio(loop_scope="session")
    async def test_load_config(
        self, test_projects, test_places, test_users, test_config
    ):
        workspace = load_workspace(test_config)
        assert await workspace.place_id("ns") == test_places["ns"]
        assert await workspace.place_id("xyz") is None
        assert await workspace.project_id("ever") == test_projects["ever"]
        assert await workspace.project_id("xyz") is None
        assert await workspace.user(1) == test_users.get("1")
        assert await workspace.user_id(1) == test_users.get("1").get("inat_user_id")

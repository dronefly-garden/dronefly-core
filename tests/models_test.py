# pylint: disable=missing-class-docstring disable=no-self-use disable=missing-function-docstring
import pytest

from dronefly.core.models import Config, load_config


class TestModels:
    def test_empty_config(self):
        config = Config()
        assert config.places == {}
        assert config.projects == {}
        assert config.users == {}

    @pytest.mark.asyncio(scope="session")
    async def test_config(self):
        test_user = {"inat_user_id": 585640, "inat_place_id": 6853}
        config = Config(
            projects={"ever": 48611}, places={"ns": 6853}, users={"1": test_user}
        )
        assert await config.place("ns") == 6853
        assert await config.place("xyz") is None
        assert await config.project("ever") == 48611
        assert await config.project("xyz") is None
        assert await config.user(1) == test_user

    @pytest.mark.asyncio(scope="session")
    async def test_load_config(self):
        test_user = {"inat_user_id": 585640, "inat_place_id": 6853}
        test_config = """
[places]
ns = 6853
[projects]
ever = 48611
[users.1]
inat_user_id = 585640
inat_place_id = 6853
"""
        config = load_config(test_config)
        assert await config.place("ns") == 6853
        assert await config.place("xyz") is None
        assert await config.project("ever") == 48611
        assert await config.project("xyz") is None
        assert await config.user(1) == test_user

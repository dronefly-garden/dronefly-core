from attrs import define, field
import tomllib
from typing import Optional, Union

from ..constants import CONFIG_PATH


@define
class Config:
    """Public class for Config model."""

    places: dict = field(factory=dict)
    projects: dict = field(factory=dict)
    users: dict = field(factory=dict)

    # async accessors to facilitate more complex behaviours
    # in subclasses
    async def user(self, user_id: Union[str, int]):
        return self.users.get(str(user_id))

    async def place(self, place_abbrev: str):
        return self.places.get(place_abbrev)

    async def project(self, project_abbrev: str):
        return self.projects.get(project_abbrev)


def load_config(data: Optional[str] = None):
    config = {}
    try:
        if data:
            config = tomllib.loads(data)
        else:
            with open(CONFIG_PATH, "rb") as config_file:
                config = tomllib.load(config_file)
    except FileNotFoundError:
        pass
    return Config(**config)

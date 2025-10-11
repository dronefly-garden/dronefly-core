from attrs import define, field
import tomllib
from typing import Optional, Union

from ..constants import CONFIG_PATH


class BaseConfig:
    """An interface for configurable lookup of iNat-related settings."""

    async def user(self, name_or_id: Union[str, int]):
        """Returns all user-configurable settings for the user identified by name_or_id."""
        raise NotImplementedError

    async def place(self, abbrev: str):
        """Returns iNat place id# if abbrev is defined."""
        raise NotImplementedError

    async def project(self, abbrev: str):
        """Returns iNat project id# if abbrev is defined."""
        raise NotImplementedError


@define
class Config(BaseConfig):
    """Public class for Config model."""

    places: dict = field(factory=dict)
    projects: dict = field(factory=dict)
    users: dict = field(factory=dict)

    # async accessors to facilitate more complex behaviours
    # in subclasses
    async def user(self, name_or_id: Union[str, int]):
        return self.users.get(str(name_or_id))

    async def place(self, abbrev: str):
        return self.places.get(abbrev)

    async def project(self, abbrev: str):
        return self.projects.get(abbrev)


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

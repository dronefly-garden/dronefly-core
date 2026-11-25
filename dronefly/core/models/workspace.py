from typing import Optional, Union
import tomllib
from attrs import define, field

from ..constants import CONFIG_PATH


class BaseWorkspace:
    """Interface for configurable lookup of iNat-related settings within a workspace."""

    async def user(self, name_or_id: Union[str, int]) -> Optional[dict]:
        """Return Dronefly user record for name_or_id if configured."""
        raise NotImplementedError

    async def user_id(self, name_or_id: Union[str, int]) -> Optional[Union[int, str]]:
        """Return iNat user id for name_or_id if configured."""
        raise NotImplementedError

    async def place_id(
        self, abbrev: Union[str, int], user: Optional[Union[str, int]] = None
    ) -> Optional[int]:
        """Return iNat place id if abbrev is defined (including 'home' resolution)."""
        raise NotImplementedError

    async def project_id(self, abbrev: str) -> Optional[int]:
        """Return iNat project id if abbrev is defined."""
        raise NotImplementedError


@define
class Workspace(BaseWorkspace):
    """Domain model representing a logical workspace (e.g., guild or CLI environment)."""

    places: dict[str, int] = field(factory=dict)
    projects: dict[str, int] = field(factory=dict)
    users: dict[str, dict] = field(factory=dict)
    default_place_id: Optional[int] = None
    default_user: Optional[Union[str, int]] = None
    parent: Optional["Workspace"] = None

    async def user(self, name_or_id: Union[str, int]) -> Optional[dict]:
        found = self.users.get(str(name_or_id))
        if found is None and self.parent:
            found = await self.parent.user(name_or_id)
        return found

    async def user_id(self, name_or_id: Union[str, int]) -> Optional[Union[int, str]]:
        record = await self.user(name_or_id)
        return record.get("inat_user_id") if record else None

    async def place_id(
        self, abbrev: Union[str, int], user: Optional[Union[str, int]] = None
    ) -> Optional[int]:
        if isinstance(abbrev, int) or (isinstance(abbrev, str) and abbrev.isnumeric()):
            return int(abbrev)

        key = abbrev.lower()
        if key == "home":
            target_user = user if user is not None else self.default_user
            if target_user is not None:
                record = await self.user(target_user)
                if record and record.get("inat_place_id"):
                    return record["inat_place_id"]
            if self.default_place_id is not None:
                return self.default_place_id
            return await self.parent.place_id("home") if self.parent else None

        found = self.places.get(key)
        if found is None and self.parent:
            found = await self.parent.place_id(key)
        return found

    async def project_id(self, abbrev: str) -> Optional[int]:
        key = abbrev.lower()
        found = self.projects.get(key)
        if found is None and self.parent:
            found = await self.parent.project_id(key)
        return found


def load_workspace(data: Optional[str] = None) -> Workspace:
    raw = {}
    try:
        if data:
            raw = tomllib.loads(data)
        else:
            with open(CONFIG_PATH, "rb") as config_file:
                raw = tomllib.load(config_file)
    except FileNotFoundError:
        pass
    return Workspace(**raw)

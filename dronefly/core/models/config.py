from attrs import define
import tomllib
from typing import Optional, Union

from ..constants import CONFIG_PATH


@define
class Config:
    """Public class for Config model."""

    data: dict = {}

    def __init__(self, data_str: Optional[str] = None):
        try:
            self.load(data_str)
        except FileNotFoundError:
            pass
        except (tomllib.TOMLDecodeError, OSError) as err:
            print(err)

    def load(self, data_str: Optional[str] = None):
        self.data = {}
        if data_str:
            self.data = tomllib.loads(data_str)
        else:
            with open(CONFIG_PATH, "rb") as config_file:
                self.data = tomllib.load(config_file)

    def user(self, user_id: Union[str, int]):
        try:
            return self.data["users"][str(user_id)]
        except KeyError:
            return None

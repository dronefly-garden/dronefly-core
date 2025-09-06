from typing import Union

from attrs import define

from ..constants import INAT_DEFAULTS, INAT_USER_DEFAULT_PARAMS
from . import BaseFormatter, ListFormatter, User


@define
class Context:
    """A Dronefly command context."""

    author: User = User()
    # Optional page formatter and current page:
    # - Provides support for next & prev commands to navigate through
    #   paged command results.
    # - Every command providing paged results must:
    #   - Set page_formatter to the formatter for the new results.
    #   - Set page_number to the initial page number (default: 0).
    # - Therefore, only a single command providing paged results can
    #   be active at a time.
    page_formatter: Union[ListFormatter, BaseFormatter] = None
    page_number: int = 0
    per_page: int = 0
    selected: int = 0

    def get_inat_user_default(self, inat_param: str):
        """Return iNat API default for user param default, if any, otherwise global default."""
        if inat_param not in INAT_USER_DEFAULT_PARAMS:
            return None
        default = None
        if self.author:
            default = getattr(self.author, inat_param, None)
        if not default:
            default = INAT_DEFAULTS.get(inat_param)
        return default

    def get_inat_defaults(self):
        """Return all iNat API defaults."""
        defaults = {**INAT_DEFAULTS}
        for user_param, inat_param in INAT_USER_DEFAULT_PARAMS.items():
            default = self.get_inat_user_default(user_param)
            if default is not None:
                defaults[inat_param] = default
        return defaults

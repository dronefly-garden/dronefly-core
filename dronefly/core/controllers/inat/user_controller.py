from pyinaturalist.constants import MultiIntOrStr
from pyinaturalist.controllers import UserController as pyiNatUserController
from pyinaturalist.converters import ensure_list
from pyinaturalist.models import User
from pyinaturalist.v1 import get_user_by_id

from ...paginator import Paginator, IDPaginator


class UserController(pyiNatUserController):
    def from_ids(self, user_ids: MultiIntOrStr, **params) -> Paginator[User]:
        """Return our paginator with async_one instead of pyiNat's"""
        return self.client.paginate(
            get_user_by_id, User, cls=IDPaginator, ids=ensure_list(user_ids), **params
        )

    async def from_dronefly_ids(
        self, user_ids: MultiIntOrStr, **params
    ) -> Paginator[User]:
        """Get users by dronefly ID

        Example:
            Get a user by dronefly ID:

            >>> user = client.users.from_dronefly_id(1).one()

            Get multiple users by dronefly ID:

            >>> users = client.users.from_id([1,2]).all()

        Args:
            user_ids: One or more user IDs
        """
        return self.client.paginate(
            get_user_by_id, User, cls=IDPaginator, ids=ensure_list(user_ids), **params
        )

from typing import Iterable

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

    async def from_dronefly_users(
        self, dronefly_users: Iterable, **params
    ) -> Paginator[User]:
        """Get iNat users for list of dronefly users"""
        inat_user_ids = [
            await self.client.ctx.config.user_id(dronefly_user)
            for dronefly_user in dronefly_users
        ]
        return self.client.paginate(
            get_user_by_id,
            User,
            cls=IDPaginator,
            ids=ensure_list(inat_user_ids),
            **params
        )

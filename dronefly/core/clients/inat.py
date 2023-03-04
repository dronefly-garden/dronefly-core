"""Module to access iNaturalist API."""
from contextlib import contextmanager
from typing import Optional

from pyinaturalist import iNatClient as pyiNatClient
from pyinaturalist.constants import RequestParams
from pyinaturalist.request_params import get_valid_kwargs


class iNatClient(pyiNatClient):
    """iNat client based on pyinaturalist."""

    def add_client_settings(
        self,
        request_function,
        kwargs: Optional[RequestParams] = None,
        auth: bool = False,
    ):
        _kwargs = super().add_client_settings(request_function, kwargs, auth)

        user = self.ctx and self.ctx.author
        preferred_place_id = user and user.inat_place_id
        if preferred_place_id:
            user_kwargs = get_valid_kwargs(
                request_function, {"preferred_place_id": preferred_place_id}
            )
            for k, v in user_kwargs.items():
                _kwargs.setdefault(k, v)

        return _kwargs

    @contextmanager
    def set_ctx(self, ctx):
        self.ctx = ctx
        yield self

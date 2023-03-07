"""Module to access iNaturalist API."""
from contextlib import contextmanager
from inspect import signature
from typing import Optional

from pyinaturalist import iNatClient as pyiNatClient
from pyinaturalist.constants import RequestParams


class iNatClient(pyiNatClient):
    """iNat client based on pyinaturalist."""

    def add_client_settings(
        self,
        request_function,
        kwargs: Optional[RequestParams] = None,
        auth: bool = False,
    ):
        _kwargs = super().add_client_settings(request_function, kwargs, auth)

        request_params = signature(request_function).parameters
        if "all_names" in request_params:
            _kwargs.setdefault("all_names", True)
        user = self.ctx and self.ctx.author
        if user and user.inat_place_id and "preferred_place_id" in request_params:
            _kwargs.setdefault("preferred_place_id", user.inat_place_id)

        return _kwargs

    @contextmanager
    def set_ctx(self, ctx):
        self.ctx = ctx
        yield self

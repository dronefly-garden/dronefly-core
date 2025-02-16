"""Module to access iNaturalist API."""
import asyncio
from contextlib import contextmanager
from functools import partial
from inspect import signature
import os
from typing import Optional

from pyinaturalist import (
    ClientSession,
    FileLockSQLiteBucket,
    iNatClient as pyiNatClient,
)
from pyinaturalist.constants import RequestParams

from ..constants import INAT_DEFAULTS, USER_DATA_PATH


def asyncify(client: pyiNatClient, method):
    async def async_wrapper(*args, **kwargs):
        future = client.loop.run_in_executor(None, partial(method, *args, **kwargs))
        try:
            return await asyncio.wait_for(future, timeout=20)
        except TimeoutError:
            raise LookupError("iNaturalist API request timed out")

    return async_wrapper


class iNatClient(pyiNatClient):
    """iNat client based on pyinaturalist."""

    def __init__(self, *args, **kwargs):
        ratelimit_path = os.path.join(USER_DATA_PATH, "ratelimit.db")
        lock_path = os.path.join(USER_DATA_PATH, "ratelimit.lock")
        cache_file = os.path.join(USER_DATA_PATH, "api_requests.db")
        session = ClientSession(
            bucket_class=FileLockSQLiteBucket,
            cache_file=cache_file,
            ratelimit_path=ratelimit_path,
            lock_path=lock_path,
        )
        _kwargs = {
            "session": session,
            **kwargs,
        }
        super().__init__(*args, **_kwargs)
        self.taxa.populate = asyncify(self, self.taxa.populate)
        self.observations.taxon_summary = asyncify(
            self, self.observations.taxon_summary
        )
        self.observations.life_list = asyncify(self, self.observations.life_list)

    def add_client_settings(
        self,
        request_function,
        kwargs: Optional[RequestParams] = None,
        auth: bool = False,
    ):
        _kwargs = super().add_client_settings(request_function, kwargs, auth)

        inat_defaults = self.ctx.get_inat_defaults() if self.ctx else INAT_DEFAULTS
        request_params = signature(request_function).parameters
        for param in inat_defaults:
            if param in request_params:
                _kwargs.setdefault(param, inat_defaults[param])

        return _kwargs

    @contextmanager
    def set_ctx(self, ctx):
        self.ctx = ctx
        yield self

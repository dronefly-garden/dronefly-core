"""Module to access iNaturalist API."""
import asyncio
from contextlib import contextmanager
from functools import partial
from inspect import signature
from typing import Optional

from pyinaturalist import (
    ClientSession,
    FileLockSQLiteBucket,
    iNatClient as pyiNatClient,
)
from pyinaturalist.constants import RequestParams

from ..constants import INAT_DEFAULTS, RATELIMIT_FILE, RATELIMIT_LOCK_FILE, CACHE_FILE


DRONEFLY_SESSION = ClientSession(
    bucket_class=FileLockSQLiteBucket,
    cache_file=CACHE_FILE,
    ratelimit_path=RATELIMIT_FILE,
    lock_path=RATELIMIT_LOCK_FILE,
)


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
        _kwargs = {
            "session": DRONEFLY_SESSION,
            **kwargs,
        }
        super().__init__(*args, **_kwargs)
        self.annotations.async_all = asyncify(self, self.annotations.all)
        self.taxa.populate = asyncify(self, self.taxa.populate)
        self.observations.taxon_summary = asyncify(
            self, self.observations.taxon_summary
        )
        self.observations.life_list = asyncify(self, self.observations.life_list)

    def add_defaults(
        self,
        request_function,
        kwargs: Optional[RequestParams] = None,
        auth: bool = False,
    ):
        _kwargs = super().add_defaults(request_function, kwargs, auth)

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

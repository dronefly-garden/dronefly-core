"""Module to access iNaturalist API."""
from contextlib import contextmanager
from inspect import signature
from typing import Optional

from platformdirs import user_data_dir
from pyinaturalist import (
    ClientSession,
    FileLockSQLiteBucket,
    iNatClient as pyiNatClient,
)
from pyinaturalist.constants import RequestParams
import os

from ..constants import INAT_DEFAULTS

BASE_PATH = os.path.join(user_data_dir(), "dronefly-core")


class iNatClient(pyiNatClient):
    """iNat client based on pyinaturalist."""

    def __init__(self, *args, **kwargs):
        ratelimit_path = os.path.join(BASE_PATH, "ratelimit.db")
        lock_path = os.path.join(BASE_PATH, "ratelimit.lock")
        cache_file = os.path.join(BASE_PATH, "api_requests.db")
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

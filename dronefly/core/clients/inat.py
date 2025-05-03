"""Module to access iNaturalist API."""
from contextlib import contextmanager
from inspect import signature
import os
from typing import Optional

from pyinaturalist import session as pyinat_session
from requests_ratelimiter import Limiter, RequestRate

from pyinaturalist import (
    FileLockSQLiteBucket,
    iNatClient as pyiNatClient,
)
from pyinaturalist.constants import RequestParams

from ..constants import INAT_DEFAULTS, USER_DATA_PATH

# Patch pyinaturalist session.REFRESH_LIMITER because pyinat's ClientSession
# doesn't paramterize it.
pyinat_session.RATELIMIT_FILE = os.path.join(USER_DATA_PATH, "ratelimit.db")
pyinat_session.REFRESH_LIMITER = Limiter(
    RequestRate(1, 122),
    bucket_class=FileLockSQLiteBucket,
    bucket_kwargs={"path": pyinat_session.RATELIMIT_FILE},
)


class iNatClient(pyiNatClient):
    """iNat client based on pyinaturalist."""

    def __init__(self, *args, **kwargs):
        ratelimit_path = os.path.join(USER_DATA_PATH, "ratelimit.db")
        lock_path = os.path.join(USER_DATA_PATH, "ratelimit.lock")
        cache_file = os.path.join(USER_DATA_PATH, "api_requests.db")
        session = pyinat_session.ClientSession(
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

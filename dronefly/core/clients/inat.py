"""Module to access iNaturalist API."""
from contextlib import contextmanager

from pyinaturalist import iNatClient as pyiNatClient

class iNatClient(pyiNatClient):
    """iNat client based on pyinaturalist."""
    def add_client_settings(self, *args, **kwargs):
        request_kwargs = super().add_client_settings(*args,  **kwargs)
        user = self.ctx.author
        if user and user.inat_place_id:
            request_kwargs['preferred_place_id'] = user.inat_place_id

        return request_kwargs

    @contextmanager
    def set_ctx(self, ctx):
        self.ctx = ctx
        yield self

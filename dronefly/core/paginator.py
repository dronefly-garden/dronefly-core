from pyinaturalist.paginator import (
    Paginator as pyiNatPaginator,
    IDPaginator as pyiNatIDPaginator,
)


class AsyncPaginatorMixin:
    async def async_one(self):
        self.per_page = 1
        results = await self.async_all()
        return results[0] if results else None


class Paginator(AsyncPaginatorMixin, pyiNatPaginator):
    """pyinaturalist.Paginator with async_one."""


class IDPaginator(AsyncPaginatorMixin, pyiNatIDPaginator):
    """pyinaturalist.Paginator with async_one."""

from typing import Any

from .source import PageSource


class BaseMenu:
    def __init__(
        self,
        source: PageSource,
        **kwargs: Any,
    ) -> None:
        self._source = source
        super().__init__(**kwargs)

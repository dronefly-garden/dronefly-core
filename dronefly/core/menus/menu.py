from .source import PageSource


class BaseMenu:
    def __init__(
        self,
        source: PageSource,
        current_page: int = 0,
    ) -> None:
        self._source = source
        self.current_page = current_page

from .source import ListPageSource, PageSource


class BaseMenu:
    def __init__(
        self,
        source: PageSource,
    ) -> None:
        self._source = source


class BaseListMenu(BaseMenu):
    def __init__(
        self,
        source: ListPageSource,
        current_page: int = 0,
        selected: int = 0,
    ) -> None:
        self._source = source
        self.current_page = current_page
        self.selected = selected
        super().__init__(source)

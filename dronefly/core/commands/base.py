import asyncio
from copy import copy

from inspect import signature
from typing import Callable, Dict, Optional, TYPE_CHECKING, Union

from ..parsers import NaturalParser
from ..clients.inat import iNatClient
from ..models import BaseFormatter, load_config, ListFormatter
from .constants import Format

if TYPE_CHECKING:
    from ..menus.menu import BaseMenu


class CommandResponse:
    menu: Optional["BaseMenu"] = None

    def format_message(self):
        raise NotImplementedError

    async def start_menu(self):
        if self.menu:
            await self.menu.start()
        else:
            raise NotImplementedError


class Command:
    def __init__(self, name: str):
        self.name = name

    async def __call__(self, *args, **kwargs) -> CommandResponse:
        raise NotImplementedError


class Group(Command):
    pass


class Commands:
    """A Dronefly command processor."""

    _children: Dict[str, Union[Command, Group]] = {}

    def __init__(
        self,
        loop: asyncio.BaseEventLoop,
        format: Format = Format.discord_markdown,
    ):
        self.loop = loop
        # TODO: platform: dronefly.Platform
        # - e.g. discord, commandline, web
        self.format = format
        self.inat_client = iNatClient(loop=loop)
        self.parser = NaturalParser()
        self.dronefly_config = load_config()

    def _parse(self, query_str):
        return self.parser.parse(query_str)

    # FIXME: this is a menu and/or formatter concern, not a commands concern
    async def _get_formatted_page(
        self,
        formatter: Union[ListFormatter, BaseFormatter],
        page_number: int = 0,
        selected: int = 0,
        header: str = None,
        footer: str = None,
    ):
        source = getattr(formatter, "source", None)
        if getattr(formatter, "format_page", None):
            if source:
                page = await source.get_page(page_number)
                sig = signature(formatter.format_page)
                if len(sig.parameters) == 3:
                    markdown_text = formatter.format_page(page, page_number, selected)
                    last_page = formatter.last_page()
                else:
                    markdown_text = formatter.format_page(page)
                    last_page = 0
            else:
                markdown_text = formatter.format_page(page_number, selected)
                last_page = formatter.last_page()
            if last_page > 0:
                markdown_text = "\n\n".join(
                    [markdown_text, f"Page {page_number + 1}/{last_page + 1}"]
                )
        else:
            markdown_text = formatter.format()
        if header or footer:
            markdown_text = "\n\n".join(
                [item for item in (header, markdown_text, footer) if item is not None]
            )
        return markdown_text

    def add_command(self, command: Command, post_format_message: Callable = None):
        _command = copy(command)
        _command.commands = self
        _command.post_format_message = post_format_message
        self._children[command.name] = _command


"""
    def command(
        self,
        func,
    ) -> Any:
        name = func.__name__
        cmd = Command(name=name)
        self.add_command(name, cmd)
        async def decorator(*args, **kwargs):
            return await cmd(*args, **kwargs)

        return decorator

"""

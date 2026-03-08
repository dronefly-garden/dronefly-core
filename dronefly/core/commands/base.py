import asyncio
from inspect import signature
from typing import Dict, Union

from ..parsers import NaturalParser
from ..clients.inat import iNatClient
from ..models import BaseFormatter, load_config, ListFormatter
from .constants import Format


class CommandResponse:
    def __init__(self, response: str):
        # FIXME: should take as input a base response type that is a data
        # representation of the response, not the formatted string response
        # itself
        self.response = response

    def format_message(self):
        # FIXME: should format the data from the response, not just return
        # the response as-is. a default implementation could include common
        # features of Discord embeds like a title, thumbnail, etc.
        return self.response

    def start_menu(self):
        raise NotImplementedError


class Command:
    def __init__(self, name: str):
        self.name = name

    async def execute(self, *args, **kwargs) -> CommandResponse:
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

    @classmethod
    def add_command(cls, command: Command):
        cls._children[command.name] = command


"""
    @classmethod
    def command(
        cls,
        func,
    ) -> Any:
        name = func.__name__
        cmd = Command(name=name, callback=func)
        cls.add_command(name, cmd)
        async def decorator(*args, **kwargs):
            return await cmd.execute(*args, **kwargs)

        return decorator

"""

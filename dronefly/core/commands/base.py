import asyncio
from inspect import signature
import re
from typing import Union

from rich.markdown import Markdown
from ..parsers import NaturalParser
from ..clients.inat import iNatClient
from ..models import BaseFormatter, load_config, ListFormatter
from .constants import (
    Format,
    RICH_BQ_END_PAT,
    RICH_BQ_NEWLINE_PAT,
    RICH_NO_BQ_NEWLINE_PAT,
)


class Command:
    def execute():
        pass


class CommandResponse:
    def format_message():
        pass

    def start_menu():
        pass


class Commands:
    """A Dronefly command processor."""

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

    def _format_markdown(self, markdown_text: str):
        """Format Rich vs. Discord markdown."""
        if self.format == Format.rich:
            # Richify the markdown:
            # - In Discord markdown, all newlines are rendered as line breaks
            # - In Rich:
            #   - Before every newline, emit " \" to force a line break, except
            #     for these exceptions to handle blockquotes:
            #     - Don't do this for a line preceding a blockquote
            #     - Also don't do this on the last line of a blockquote
            #     - Ensure the last line of each blockquote has two newlines to
            #       end it

            # Replace all but last newline of blockquote with line break sequence:
            rich_markdown = re.sub(RICH_BQ_NEWLINE_PAT, r"\1 \\\n", markdown_text)
            # Add extra newline at end of blockquote so following text won't be
            # tacked on:
            rich_markdown = re.sub(RICH_BQ_END_PAT, r"\1\n\n", rich_markdown)
            # Finally, on any line that isn't part of a blockquote, isn't empty,
            # and isn't at the end of the string, emit a line break:
            rich_markdown = re.sub(RICH_NO_BQ_NEWLINE_PAT, r"\1 \\\n", rich_markdown)
            response = Markdown(rich_markdown)
        else:
            # Return the literal markdown for Discord to render
            response = markdown_text
        return response

    def _simple_format_markdown(self, markdown_text: str):
        """Simplified formatter for Rich vs. Discord markdown.

        Discord vs. Rich linebreak rendering is harder than we thought, e.g.
        `_format_markdown()` doesn't give correct results with point-form
        or numbered lists. If special handling of newlines isn't needed, then
        use this helper instead.
        """
        if self.format == Format.rich:
            # Richify the markdown
            response = Markdown(markdown_text)
        else:
            # Return the literal markdown for Discord to render
            response = markdown_text
        return response

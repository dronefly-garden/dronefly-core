from enum import Enum
import re

RICH_BQ_NEWLINE_PAT = re.compile(r"^(\> .*?)\n(?=\> )", re.MULTILINE)
RICH_BQ_END_PAT = re.compile(r"^((\> .*?\n)+)(?!> )", re.MULTILINE)
RICH_NO_BQ_NEWLINE_PAT = re.compile(r"^(?!\> )(.+?)(\n)(?!$|\> )", re.MULTILINE)
RICH_NEWLINE = " \\\n"


class Format(Enum):
    discord_markdown = 1
    rich = 2

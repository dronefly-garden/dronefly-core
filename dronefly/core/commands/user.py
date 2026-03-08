from ..formatters.generic import UserFormatter
from ..models.context import Context
from ..query.query import match_user

from .base import Command, CommandResponse, Commands
from .exceptions import ArgumentError


class UserCommand(Command):
    def __init__(
        self,
        commands: Commands,
        name="user",
    ):
        self.commands = commands
        self.name = name

    async def execute(self, ctx: Context, user_str: str):
        """Show user"""
        with self.commands.inat_client.set_ctx(ctx) as client:
            try:
                user = await match_user(client, user_str)
            except ArgumentError as err:
                return str(err)
            # TODO: return data object, not formatted response:
            return CommandResponse(
                response=self.commands._format_markdown(UserFormatter(user).format())
            )

from pyinaturalist.models import User

from ..formatters.generic import UserFormatter
from ..models.context import Context
from ..query.query import match_user

from .base import Command, CommandResponse, Commands
from .exceptions import ArgumentError


class UserCommandResponse(CommandResponse):
    def __init__(self, user: User, **kwargs):
        super().__init__(**kwargs)
        self.user = user

    def format_message(self):
        message = UserFormatter(self.user).format()
        return message


class UserCommand(Command):
    """Show user"""

    commands: Commands

    def __init__(
        self,
        name="user",
    ):
        self.name = name

    async def __call__(self, ctx: Context, user_str: str):
        with self.commands.inat_client.set_ctx(ctx) as client:
            try:
                user = await match_user(client, user_str)
            except ArgumentError as err:
                return str(err)
            return UserCommandResponse(user=user)

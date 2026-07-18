"""Tests for Observation search command."""
# pylint: disable=missing-class-docstring, no-self-use, missing-function-docstring
# pylint: disable=redefined-outer-name

import asyncio

import pytest
from dronefly.core.commands.cli import CLICommands
from dronefly.core.models.context import Context  # noqa: F401


@pytest.fixture
def ctx():
    ctx = Context()
    ctx.per_page = 10
    return ctx


@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def cmd(event_loop):
    return CLICommands(loop=event_loop)


# TODO: Mock communication with iNatClient
@pytest.mark.asyncio(scope="session")
async def test_obs_search_with_result(cmd, ctx):
    response = await cmd.obs_search(ctx, "poecile by johngcramer added on 2017-01-01")
    expected = "`Jan-2017`>**__[*Poecile atricapillus*](https://www.inaturalist.org/observations/4881581)__**"  # noqa: E501
    assert response == expected


@pytest.mark.asyncio(scope="session")
async def test_obs_search_with_no_result(cmd, ctx):
    with pytest.raises(LookupError) as err:
        await cmd.obs_search(ctx, "xyzzy")
        assert str(err) == "Nothing found"

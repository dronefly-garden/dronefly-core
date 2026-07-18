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
    ctx.per_page = 1
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
async def test_obs_search_with_one_full_page(cmd, ctx):
    ctx.per_page = 3
    response = await cmd.obs_search(
        ctx, "poecile by benarmstrong added until 2019-03-01"
    )
    expected = """`Feb-2019`>**__[*Poecile atricapillus*](https://www.inaturalist.org/observations/20258222)__**
`Jan-2019`\N{EN SPACE}[*Poecile atricapillus*](https://www.inaturalist.org/observations/19864873)
`Jul-2018`\N{EN SPACE}[*Poecile atricapillus*](https://www.inaturalist.org/observations/14325258)"""  # noqa: E501
    assert response == expected


@pytest.mark.asyncio(scope="session")
async def test_obs_search_with_two_pages(cmd, ctx):
    ctx.per_page = 2
    response = await cmd.obs_search(
        ctx, "poecile by benarmstrong added until 2019-03-01"
    )
    expected = """`Feb-2019`>**__[*Poecile atricapillus*](https://www.inaturalist.org/observations/20258222)__**
`Jan-2019`\N{EN SPACE}[*Poecile atricapillus*](https://www.inaturalist.org/observations/19864873)

Page 1/2"""  # noqa: E501
    assert response == expected
    response = await cmd.next(ctx)
    expected = """`Jul-2018`>**__[*Poecile atricapillus*](https://www.inaturalist.org/observations/14325258)__**

Page 2/2"""  # noqa: E501
    assert response == expected


@pytest.mark.asyncio(scope="session")
async def test_obs_search_with_one_of_three_pages(cmd, ctx):
    response = await cmd.obs_search(
        ctx, "poecile by benarmstrong added until 2019-03-01"
    )
    expected = """`Feb-2019`>**__[*Poecile atricapillus*](https://www.inaturalist.org/observations/20258222)__**

Page 1/3"""  # noqa: E501
    assert response == expected


@pytest.mark.asyncio(scope="session")
async def test_obs_search_with_no_result(cmd, ctx):
    with pytest.raises(LookupError) as err:
        await cmd.obs_search(ctx, "xyzzy")
        assert str(err) == "Nothing found"

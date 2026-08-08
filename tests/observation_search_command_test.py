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
    expected = """[Search: Observations of Genus *Poecile* (Chickadees and Allies) by Ben Armstrong (benarmstrong) added  on or before Mar 1, 2019 Mar:03 AM](https://www.inaturalist.org/observations?verifiable=any&taxon_id=144351&user_id=545640&created_d2=2019-03-01T00%3A00%3A00)

\N{BLACK RIGHT-POINTING SMALL TRIANGLE}**__[*Poecile atricapillus*](https://www.inaturalist.org/observations/20258222)__**
\N{EN SPACE}`Feb-2019 Halifax Regional Munic…`\N{EN SPACE}✅ 📷 👥 (2/2)
\N{ZERO WIDTH SPACE}\N{EN SPACE}[*Poecile atricapillus*](https://www.inaturalist.org/observations/19864873)
\N{EN SPACE}`Jan-2019 Halifax Regional Munic…`\N{EN SPACE}✅ 📷2 👥 (2/2)
\N{ZERO WIDTH SPACE}\N{EN SPACE}[*Poecile atricapillus*](https://www.inaturalist.org/observations/14325258)
\N{EN SPACE}`Jul-2018 Halifax, Nova Scotia, …`\N{EN SPACE}✅ 📷 👥 (4/4)"""  # noqa: E501
    assert response == expected


@pytest.mark.asyncio(scope="session")
async def test_obs_search_with_two_pages(cmd, ctx):
    ctx.per_page = 2
    response = await cmd.obs_search(
        ctx, "poecile by benarmstrong added until 2019-03-01"
    )
    expected = """[Search: Observations of Genus *Poecile* (Chickadees and Allies) by Ben Armstrong (benarmstrong) added  on or before Mar 1, 2019 Mar:03 AM](https://www.inaturalist.org/observations?verifiable=any&taxon_id=144351&user_id=545640&created_d2=2019-03-01T00%3A00%3A00)

\N{BLACK RIGHT-POINTING SMALL TRIANGLE}**__[*Poecile atricapillus*](https://www.inaturalist.org/observations/20258222)__**
\N{EN SPACE}`Feb-2019 Halifax Regional Munic…`\N{EN SPACE}✅ 📷 👥 (2/2)
\N{ZERO WIDTH SPACE}\N{EN SPACE}[*Poecile atricapillus*](https://www.inaturalist.org/observations/19864873)
\N{EN SPACE}`Jan-2019 Halifax Regional Munic…`\N{EN SPACE}✅ 📷2 👥 (2/2)

Page 1/2"""  # noqa: E501
    assert response == expected
    response = await cmd.next(ctx)
    expected = """\N{BLACK RIGHT-POINTING SMALL TRIANGLE}**__[*Poecile atricapillus*](https://www.inaturalist.org/observations/14325258)__**
\N{EN SPACE}`Jul-2018 Halifax, Nova Scotia, …`\N{EN SPACE}✅ 📷 👥 (4/4)

Page 2/2"""  # noqa: E501
    assert response == expected


@pytest.mark.asyncio(scope="session")
async def test_obs_search_with_one_of_three_pages(cmd, ctx):
    response = await cmd.obs_search(
        ctx, "poecile by benarmstrong added until 2019-03-01"
    )
    expected = """[Search: Observations of Genus *Poecile* (Chickadees and Allies) by Ben Armstrong (benarmstrong) added  on or before Mar 1, 2019 Mar:03 AM](https://www.inaturalist.org/observations?verifiable=any&taxon_id=144351&user_id=545640&created_d2=2019-03-01T00%3A00%3A00)

\N{BLACK RIGHT-POINTING SMALL TRIANGLE}**__[*Poecile atricapillus*](https://www.inaturalist.org/observations/20258222)__**
\N{EN SPACE}`Feb-2019 Halifax Regional Munic…` ✅ 📷 👥 (2/2)

Page 1/3"""  # noqa: E501
    print(response)
    print(expected)
    assert response == expected


@pytest.mark.asyncio(scope="session")
async def test_obs_search_with_no_result(cmd, ctx):
    with pytest.raises(LookupError) as err:
        await cmd.obs_search(ctx, "xyzzy")
        assert str(err) == "Nothing found"

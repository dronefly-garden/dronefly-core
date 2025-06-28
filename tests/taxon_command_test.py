"""Tests for Taxon command."""
# pylint: disable=missing-class-docstring, no-self-use, missing-function-docstring
# pylint: disable=redefined-outer-name

import asyncio
import re

import pytest
from dronefly.core import Commands
from dronefly.core.commands import Context  # noqa: F401


@pytest.fixture
def ctx():
    return Context()


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
    return Commands(loop=event_loop)


# TODO: Mock communication with iNatClient
@pytest.mark.asyncio(scope="session")
async def test_taxon_with_result(cmd, ctx):
    response = re.sub(r"\[[0-9,]*?\]", "[19,999,999]", await cmd.taxon(ctx, "birds"))
    assert response == (
        "[Class Aves (Birds)](https://www.inaturalist.org/taxa/3)\nis a class with "
        "[19,999,999](https://www.inaturalist.org/observations?taxon_id=3) observations "
        "🟩 [native in United States](https://www.inaturalist.org/listed_taxa/127259059) "
        "in: \n> **Animalia** > \n> **Chordata** > Vertebrata"
    )


@pytest.mark.asyncio(scope="session")
async def test_taxon_with_no_result(cmd, ctx):
    assert await cmd.taxon(ctx, "xyzzy") == "Nothing found"


@pytest.mark.asyncio(scope="session")
async def test_taxon_with_group_macro(cmd, ctx):
    assert await cmd.taxon(ctx, "herps") == "Not a taxon"


@pytest.mark.asyncio(scope="session")
async def test_taxon_list_with_result(cmd, ctx):
    response = re.sub(r"`[0-9,]*?`>", "`999999`>", await cmd.taxon_list(ctx, "homo"))
    assert (
        response
        == """Children of Genus *Homo* (Ancestral and Modern Humans)

`999999`>**__[*Homo sapiens*](https://www.inaturalist.org/observations?verifiable=true&taxon_id=43584)__**

`1` species

Total: 1 child taxa"""  # noqa: E501
    )

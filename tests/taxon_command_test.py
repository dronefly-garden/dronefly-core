"""Tests for Taxon command."""
# pylint: disable=missing-class-docstring, no-self-use, missing-function-docstring
# pylint: disable=redefined-outer-name

import re

import pytest
from dronefly.core import Commands
from dronefly.core.commands import Context  # noqa: F401


@pytest.fixture
def cmd():
    return Commands()


@pytest.fixture
def ctx():
    return Context()


# TODO: Mock communication with iNatClient
def test_taxon_with_result(cmd, ctx):
    if not getattr(cmd.inat_client.taxa, "full_taxon", None):
        pytest.skip(
            "Not yet supported by pyinaturalist: client.taxa.full_record(taxon)"
        )
    response = re.sub(r"\[[0-9,]*?\]", "[19,999,999]", cmd.taxon(ctx, "birds"))
    assert response == (
        "[Class Aves (Birds)](https://www.inaturalist.org/taxa/3) \\\nis a class with "
        "[19,999,999](https://www.inaturalist.org/observations?taxon_id=3) observations in: "
        "\n> **Animalia** > \n> **Chordata** > Vertebrata"
    )


def test_taxon_with_no_result(cmd, ctx):
    assert cmd.taxon(ctx, "xyzzy") == "Nothing found"

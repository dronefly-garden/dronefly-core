"""Tests for Taxon command."""
# pylint: disable=missing-class-docstring, no-self-use, missing-function-docstring
# pylint: disable=redefined-outer-name

import pytest
from dronefly.core import Commands
from dronefly.core.commands import Context

@pytest.fixture
def cmd():
    return Commands()

@pytest.fixture
def ctx():
    return Context()

# TODO: Mock communication with iNatClient
def test_taxon_with_result(cmd, ctx):
    assert cmd.taxon(ctx, 'birds') == '[Class Aves (Birds)](https://www.inaturalist.org/taxa/3) \n> **Animalia** > \n> **Chordata** > Vertebrata'

def test_taxon_with_no_result(cmd, ctx):
    assert cmd.taxon(ctx, 'xyzzy') == 'Nothing found'

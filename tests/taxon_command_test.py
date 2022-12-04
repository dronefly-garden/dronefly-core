"""Tests for Taxon command."""
# pylint: disable=missing-class-docstring, no-self-use, missing-function-docstring
# pylint: disable=redefined-outer-name

import pytest
from dronefly.core import Commands

@pytest.fixture
def cmd():
    return Commands()

def test_taxon_with_result(cmd):
    assert cmd.taxon('birds') == 'Class Aves (Birds)'

def test_taxon_with_no_result(cmd):
    assert cmd.taxon('xyzzy') == 'Nothing found'

"""Test INatAPI."""
import pytest
from dronefly.core.clients.inat import iNatClient

# pylint: disable=missing-function-docstring


@pytest.fixture(name="inat_api")
async def fixture_inat_api():
    return iNatClient()

"""Tests for Taxon."""
# pylint: disable=missing-class-docstring, no-self-use, missing-function-docstring
# pylint: disable=redefined-outer-name

import pytest

from ..models.taxon import Taxon
from ..formatters.discord import format_taxon_names


@pytest.fixture
def birds():
    return Taxon(
        id=3,
        name="Aves",
        matched_term="Birds",
        rank="class",
        ancestor_ids=[48460, 1, 2, 355675, 3],
        observations_count=11645562,
        ancestor_ranks=["stateofmatter", "kingdom", "phylum", "class"],
        is_active=True,
        listed_taxa=[
            {
                "id": 5756493,
                "taxon_id": 3,
                "establishment_means": "native",
                "place": {
                    "id": 6803,
                    "name": "New Zealand",
                    "display_name": "New Zealand",
                    "admin_level": 0,
                    "ancestor_place_ids": [97393, 6803],
                },
                "list": {"id": 7126, "title": "New Zealand Check List"},
            },
            {
                "id": 86811797,
                "taxon_id": 3,
                "establishment_means": "native",
                "place": {
                    "id": 83350,
                    "name": "Auckland Ecological Region",
                    "display_name": "Auckland Ecological Region, NZ",
                    "admin_level": None,
                    "ancestor_place_ids": [97393, 6803, 83350],
                },
                "list": {
                    "id": 3848234,
                    "title": "Auckland Ecological Region Check List",
                },
            },
            {
                "id": 22740081,
                "taxon_id": 3,
                "establishment_means": "native",
                "place": {
                    "id": 128329,
                    "name": "Auckland Isthmus",
                    "display_name": "Auckland Isthmus, NZ",
                    "admin_level": None,
                    "ancestor_place_ids": [97393, 6803, 108679, 128329],
                },
                "list": {"id": 1265139, "title": "Auckland Isthmus Check List"},
            },
            {
                "id": 48895541,
                "taxon_id": 3,
                "establishment_means": "native",
                "place": {
                    "id": 146883,
                    "name": "Corredor Mashpi-Cotacachi Cayapas",
                    "display_name": "Corredor Mashpi-Cotacachi Cayapas, EC",
                    "admin_level": None,
                    "ancestor_place_ids": [97389, 7512, 146883],
                },
                "list": {
                    "id": 2747919,
                    "title": "Corredor Mashpi-Cotacachi Cayapas Check List",
                },
            },
        ],
        names=[
            {"is_valid": True, "name": "Aves", "position": 0, "locale": "sci"},
            {"is_valid": True, "name": "Aves", "position": 0, "locale": "es"},
            {"is_valid": True, "name": "鳥綱", "position": 1, "locale": "ja"},
            {"is_valid": True, "name": "Oiseaux", "position": 2, "locale": "fr"},
            {"is_valid": True, "name": "Birds", "position": 3, "locale": "en"},
            {"is_valid": True, "name": "Aves", "position": 4, "locale": "pt"},
            {"is_valid": True, "name": "Vögel", "position": 5, "locale": "de"},
            {"is_valid": True, "name": "Птицы", "position": 6, "locale": "ru"},
        ],
        preferred_common_name="Birds",
        thumbnail="https://inaturalist-open-data.s3.amazonaws.com/photos/222/square.jpg?1553973240",  # noqa: E501
        image="https://inaturalist-open-data.s3.amazonaws.com/photos/222/original.jpg?1553973240",  # noqa: E501
        image_attribution="(c) Kenny P., some rights reserved (CC BY-NC)",
    )


@pytest.fixture
def myrtle_warbler():
    return Taxon(
        id=132704,
        name="Setophaga coronata coronata",
        matched_term="Myrtle Warbler",
        rank="subspecies",
        ancestor_ranks=[
            "stateofmatter",
            "kingdom",
            "phylum",
            "class",
            "order",
            "family",
            "genus",
            "species",
        ],
        ancestor_ids=[48460, 1, 2, 355675, 3, 7251, 71349, 10246, 145245],
        preferred_common_name="Myrtle Warbler",
        observations_count=8866,
        is_active=True,
        listed_taxa=[],
        names=[],
    )


@pytest.fixture
def yellow_rumped_warbler():
    return Taxon(
        id=145245,
        name="Setophaga coronata",
        matched_term="Yellow-rumped Warbler",
        rank="species",
        ancestor_ranks=[
            "stateofmatter",
            "kingdom",
            "phylum",
            "class",
            "order",
            "family",
            "genus",
        ],
        ancestor_ids=[48460, 1, 2, 355675, 3, 7251, 71349, 10246],
        preferred_common_name="Yellow-rumped Warbler",
        observations_count=75339,
        is_active=True,
        listed_taxa=[],
        names=[],
    )


@pytest.fixture
def setophaga_warblers():
    return Taxon(
        id=10246,
        name="Setophaga",
        matched_term="Setophaga",
        rank="genus",
        ancestor_ranks=[
            "stateofmatter",
            "kingdom",
            "phylum",
            "class",
            "order",
            "family",
        ],
        ancestor_ids=[48460, 1, 2, 355675, 3, 7251, 71349],
        preferred_common_name="Setophaga Warblers",
        observations_count=233584,
        is_active=True,
        listed_taxa=[],
        names=[],
    )


@pytest.fixture
def new_world_warblers():
    return Taxon(
        id=145245,
        name="Parulidae",
        matched_term="New World Warblers",
        rank="family",
        ancestor_ranks=["stateofmatter", "kingdom", "phylum", "class", "order"],
        ancestor_ids=[48460, 1, 2, 355675, 3, 7251],
        preferred_common_name="New World Warblers",
        observations_count=372094,
        is_active=True,
        listed_taxa=[],
        names=[],
    )


@pytest.fixture
def myrtle_warbler_ancestors(
    birds, new_world_warblers, setophaga_warblers, yellow_rumped_warbler
):
    """A slightly condensed list of ancestors (only class, family, genus, and species)."""
    return [birds, new_world_warblers, setophaga_warblers, yellow_rumped_warbler]


def test_taxon_is_a_taxon(birds):
    assert isinstance(birds, Taxon)


def test_taxon_names_list(birds, myrtle_warbler):
    assert (
        format_taxon_names([birds, myrtle_warbler])
        == "Class Aves (Birds), *Setophaga coronata* ssp. *coronata* (Myrtle Warbler)"
    )


def test_taxon_names_hierarchy(myrtle_warbler_ancestors):
    assert (
        format_taxon_names(myrtle_warbler_ancestors, hierarchy=True)
        == "\n> **Aves** > \n> **Parulidae** > *Setophaga* > *Setophaga coronata*"
    )

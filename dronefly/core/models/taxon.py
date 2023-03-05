"""Taxon model module."""
from pyinaturalist.models import Taxon as PyiNatTaxon
from pyinaturalist.constants import COMMON_RANKS, RANK_EQUIVALENTS, RANK_LEVELS

PLANTAE_ID = 47126
TRACHEOPHYTA_ID = 211194
RANK_KEYWORDS = tuple(RANK_LEVELS.keys()) + tuple(RANK_EQUIVALENTS.keys())
TAXON_PRIMARY_RANKS = COMMON_RANKS[-5:]
TRINOMIAL_ABBR = {"variety": "var.", "subspecies": "ssp.", "form": "f."}


def taxon_ancestor_ranks(taxon: PyiNatTaxon):
    return (
        ["stateofmatter"] + [ancestor.rank for ancestor in taxon.ancestors]
        if taxon.ancestors
        else []
    )


class Taxon(PyiNatTaxon):
    """Public class for Taxon model."""

    # Deprecated. Use taxon_ancestor_ranks directly instead.
    def ancestor_ranks(self):
        return taxon_ancestor_ranks(self)

from pyinaturalist.constants import COMMON_RANKS, RANK_EQUIVALENTS, RANK_LEVELS

# Map Dronefly User param names to iNat API param names:
INAT_USER_DEFAULT_PARAMS = {
    "inat_place_id": "preferred_place_id",
    "inat_lang": "locale",
}
# User-settable defaults:
INAT_USER_DEFAULTS = {"locale": None, "preferred_place_id": 1}
# All defaults:
INAT_DEFAULTS = {**INAT_USER_DEFAULTS, "all_names": True}

PLANTAE_ID = 47126
TRACHEOPHYTA_ID = 211194
RANK_KEYWORDS = tuple(RANK_LEVELS.keys()) + tuple(RANK_EQUIVALENTS.keys())
TAXON_PRIMARY_RANKS = COMMON_RANKS
TRINOMIAL_ABBR = {"variety": "var.", "subspecies": "ssp.", "form": "f."}

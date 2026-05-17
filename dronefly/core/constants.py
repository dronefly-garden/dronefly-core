from platformdirs import user_data_dir
import os

from pyinaturalist.constants import COMMON_RANKS, RANK_EQUIVALENTS, RANK_LEVELS


USER_DATA_PATH = os.path.join(user_data_dir(), "dronefly-core")
CONFIG_PATH = os.path.join(USER_DATA_PATH, "config.toml")
RATELIMIT_FILE = os.path.join(USER_DATA_PATH, "ratelimit.db")
RATELIMIT_LOCK_FILE = os.path.join(USER_DATA_PATH, "ratelimit.lock")
CACHE_FILE = os.path.join(USER_DATA_PATH, "api_requests.db")

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
RANK_LEVEL_NAMES = {}
# TODO: import from pyinaturalist.constants instead of defining here:
# - see https://github.com/pyinat/pyinaturalist/commit/82cee9d642538a8afb3add8809cca161345bdc68
RANK_LEVEL_REPRESENTATIVE_RANKS = {
    5: "subspecies",
    10: "species",
    20: "genus",
}
RANKS_FOR_LEVEL = {}
for (rank, level) in RANK_LEVELS.items():
    RANK_LEVEL_NAMES[level] = RANK_LEVEL_REPRESENTATIVE_RANKS.get(level) or rank
    if level not in RANKS_FOR_LEVEL:
        RANKS_FOR_LEVEL[level] = [rank]
    else:
        RANKS_FOR_LEVEL[level].append(rank)

TAXON_PRIMARY_RANKS = COMMON_RANKS
TRINOMIAL_ABBR = {"variety": "var.", "subspecies": "ssp.", "form": "f."}

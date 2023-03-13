# Map Dronefly User param names to iNat API param names:
INAT_USER_DEFAULT_PARAMS = {
    "inat_place_id": "preferred_place_id",
    "inat_lang": "locale",
}
# User-settable defaults:
INAT_USER_DEFAULTS = {"locale": None, "preferred_place_id": 1}
# All defaults:
INAT_DEFAULTS = {**INAT_USER_DEFAULTS, "all_names": True}

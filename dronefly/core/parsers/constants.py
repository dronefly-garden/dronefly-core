"""Constants for parsers."""

ARGPARSE_ARGS = {
    "of": {"nargs": "+", "dest": "main", "default": []},
    "in": {"nargs": "+", "dest": "ancestor", "default": []},
    "by": {"nargs": "+", "dest": "user", "default": []},
    "not-by": {"nargs": "+", "dest": "unobserved_by", "default": []},
    "id-by": {"nargs": "+", "dest": "id_by", "default": []},
    "except-by": {"nargs": "+", "dest": "except_by", "default": []},
    "from": {"nargs": "+", "dest": "place", "default": []},
    "rank": {"nargs": "+", "dest": "ranks", "default": []},
    "with": {"nargs": "+", "dest": "controlled_term"},
    "per": {"nargs": "+", "dest": "per", "default": []},
    "sort-by": {"nargs": "+", "dest": "sort_by", "default": []},
    "asc": {"dest": "order", "action": "store_const", "const": "asc"},
    "desc": {"dest": "order", "action": "store_const", "const": "desc"},
    "opt": {"nargs": "+", "dest": "options", "default": []},
    "in-prj": {"nargs": "+", "dest": "project", "default": []},
    "since": {"nargs": "+", "dest": "obs_d1", "default": []},
    "until": {"nargs": "+", "dest": "obs_d2", "default": []},
    "on": {"nargs": "+", "dest": "obs_on", "default": []},
    "added-since": {"nargs": "+", "dest": "added_d1", "default": []},
    "added-until": {"nargs": "+", "dest": "added_d2", "default": []},
    "added-on": {"nargs": "+", "dest": "added_on", "default": []},
}
REMAINING_ARGS = list(ARGPARSE_ARGS)[1:]
MACROS = {
    "rg": {"opt": ["quality_grade=research"]},
    "nid": {"opt": ["quality_grade=needs_id"]},
    "oldest": {"order": "asc", "sort_by": "observed"},
    "newest": {"order": "desc", "sort_by": "observed"},
    "my": {"by": "me"},
    "home": {"from": "home"},
    "faves": {"sort_by": "votes", "opt": ["popular"]},
    "spp": {"opt": ["hrank=species"]},
    "species": {"opt": ["hrank=species"]},
    "unseen": {"not by": "me", "from": "home"},
}
# Groups of taxa:
# - can't function in place of a single taxon, and are typically only used in
#   observation searches & counts
# - must not be expanded when adjacent to other taxon keywords in the query
GROUP_MACROS = {
    # Because there are no iconic taxa for these three taxa, they must be specifically
    # excluded in order to match only actual unknowns (Bacteria, Archaea, & Viruses):
    "unknown": {"opt": ["iconic_taxa=unknown", "without_taxon_id=67333,151817,131236"]},
    "waspsonly": {"of": "apocrita", "opt": ["without_taxon_id=47336,630955"]},
    "mothsonly": {"of": "lepidoptera", "opt": ["without_taxon_id=47224"]},
    "herps": {"opt": ["taxon_ids=20978,26036"]},
    "lichenish": {
        "opt": [
            "taxon_ids=152028,54743,152030,175541,127378,117881,117869,175246",
            "without_taxon_id=372831,1040687,1040689,352459",
        ]
    },
    "nonflowering": {
        "of": "plantae",
        "opt": ["without_taxon_id=47125"],
    },
    "nonvascular": {
        "of": "plantae",
        "opt": ["without_taxon_id=211194"],
    },
    "inverts": {"of": "animalia", "opt": ["without_taxon_id=355675"]},
    "seaslugs": {
        "opt": [
            (
                "taxon_ids=130687,775798,775804,49784,500752,47113,775801,"
                "775833,775805,495793,47801,801507"
            ),
        ],
    },
    "allfish": {
        "opt": ["taxon_ids=47178,47273,797045,85497"],
    },
}
VALID_OBS_OPTS = [
    "captive",
    "csi",
    "day",
    "endemic",
    "geoprivacy",
    "hrank",
    "iconic_taxa",
    "id",
    "identified",
    "introduced",
    "lrank",
    "month",
    "native",
    "not_id",
    "order",
    "order_by",
    "out_of_range",
    "page",
    "pcid",
    "photos",
    "place_id",
    "popular",
    "project_id",
    "q",
    "quality_grade",
    "rank",
    "search_on",
    "sounds",
    "taxon_geoprivacy",
    "taxon_ids",
    "threatened",
    "user_id",
    "verifiable",
    "without_taxon_id",
    "year",
]
VALID_OBS_SORT_BY = {
    "added": "created_at",
    "observed": "observed_on",
    "votes": "votes",
    # Technically these are valid values, but we are not supporting them:
    # - these fields are not typically shown in Dronefly displays
    # - these sort options are of limited utility & hard to explain
    #    "guess": "species_guess",
    #    "id": "id",
}

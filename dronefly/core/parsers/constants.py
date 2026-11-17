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
    "oldest": {"asc": None, "sort by": "observed"},
    "newest": {"desc": None, "sort by": "observed"},
    "my": {"by": "me"},
    "home": {"from": "home"},
    "faves": {"sort by": "votes", "opt": ["popular"]},
    "spp": {"opt": ["hrank=species"]},
    "species": {"opt": ["hrank=species"]},
    "unseen": {"not by": "me", "from": "home"},
    "most": {"per": "species", "sort by": "obs"},
    "least": {"per": "species", "sort by": "obs", "asc": None},
}
# Keyword 'any' functions as a taxon name that means "no specific taxon"
# in a query expression, e.g. when an observations search is performed
# without a taxon_id parameter.
ANY_TAXA = {
    "any": {
        "query_macro": {},
        "taxon_params": {
            "name": "Any",
            "preferred_common_name": "",
        },
    },
}
# Groups of taxa:
# - can't function in place of a single taxon, and are typically only used in
#   observation searches & counts
# - must not be expanded when adjacent to other taxon keywords in the query
GROUP_TAXA = {
    "unknown": {
        "query_macro": {
            "opt": [
                "iconic_taxa=unknown",
                "without_taxon_id=67333,151817,131236",
            ]
        },
        "taxon_params": {
            "name": "Unknown",
            "preferred_common_name": "",
        },
    },
    "waspsonly": {
        "query_macro": {
            "of": "124417",
            "opt": ["without_taxon_id=47336,630955"],
        },
        "taxon_params": {
            "name": "Apocrita without Formicidae, Anthophila",
            "preferred_common_name": "Wasps without Ants and Bees",
        },
    },
    "mothsonly": {
        "query_macro": {"of": "47157", "opt": ["without_taxon_id=47224"]},
        "taxon_params": {
            "name": "Lepidoptera without Papilionoidea",
            "preferred_common_name": "Moths",
        },
    },
    "herps": {
        "query_macro": {"opt": ["taxon_ids=20978,26036"]},
        "taxon_params": {
            "name": "Amphibia, Reptilia",
            "preferred_common_name": "Amphibians & Reptiles aka Herps",
        },
    },
    "lichenish": {
        "query_macro": {
            "opt": [
                "taxon_ids=152028,54743,152030,175541,127378,117881,117869,175246",
                "without_taxon_id=372831,1040687,1040689,352459",
            ]
        },
        "taxon_params": {
            "name": "Lecanoromycetes, Arthoniomycetes, etc.",
            "preferred_common_name": "Lichenized Fungi",
        },
    },
    "nonflowering": {
        "query_macro": {
            "of": "47126",
            "opt": ["without_taxon_id=47125"],
        },
        "taxon_params": {
            "name": "Plantae without Angiospermae",
            "preferred_common_name": "Non-flowering Plants",
        },
    },
    "nonvascular": {
        "query_macro": {
            "of": "47126",
            "opt": ["without_taxon_id=211194"],
        },
        "taxon_params": {
            "name": "Plantae without Tracheophyta",
            "preferred_common_name": "Non-vascular Plants",
        },
    },
    "inverts": {
        "query_macro": {
            "of": "1",
            "opt": ["without_taxon_id=355675"],
        },
        "taxon_params": {
            "name": "Animalia without Vertebrata",
            "preferred_common_name": "Invertebrates",
        },
    },
    "seaslugs": {
        "query_macro": {
            "opt": [
                (
                    "taxon_ids=130687,775798,775804,49784,500752,47113,775801,"
                    "775833,775805,495793,47801,801507"
                ),
            ],
        },
        "taxon_params": {
            "name": "Nudibranchia, Aplysiida, etc.",
            "preferred_common_name": "Nudibranchs, Sea Hares & Other Marine Slugs",
        },
    },
    "allfish": {
        "query_macro": {
            "opt": ["taxon_ids=47178,47273,797045,85497"],
        },
        "taxon_params": {
            "name": "Actinopterygii, Agnatha, Elasmobranchii, Sarcopterygii",
            "preferred_common_name": "Extant Fish",
        },
    },
    "roachesonly": {
        "query_macro": {
            "of": "81769",
            "opt": ["without_taxon_id=118903"],
        },
        "taxon_params": {
            "name": "Blattodea without Termitoidae",
            "preferred_common_name": "Cockroaches without termites",
        },
    },
}
VIRTUAL_TAXA = {
    **ANY_TAXA,
    **GROUP_TAXA,
}
GROUP_MACROS = {key: config["query_macro"] for key, config in GROUP_TAXA.items()}


def taxon_group_members(params):
    taxon_ids = params.get("taxon_ids")
    without_taxon_id = params.get("without_taxon_id")
    includes = set(taxon_ids.split(",") if taxon_ids else [])
    excludes = set(without_taxon_id.split(",") if without_taxon_id else [])
    iconic_taxa = params.get("iconic_taxa")
    if iconic_taxa:
        includes.add(iconic_taxa)
    return includes, excludes


def group_macro_taxon_ids(group_name, group_macro):
    params = dict((option.split("=") + [""])[:2] for option in group_macro.get("opt"))
    includes, excludes = taxon_group_members(params) if params else (set(), set())
    of = group_macro.get("of")
    if of:
        includes.add(of)
    return group_name, {"includes": includes, "excludes": excludes}


GROUP_TAXON_IDS = dict(group_macro_taxon_ids(k, v) for k, v in GROUP_MACROS.items())

VALID_OBS_OPTS = [
    "captive",
    "csi",
    "day",
    "endemic",
    "geoprivacy",
    "hrank",
    "hour",
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
VALID_TAXON_LIST_SORT_BY = [
    "obs",
    "name",
]

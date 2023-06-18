from typing import TYPE_CHECKING
from urllib.parse import urlencode

from dronefly.core.formatters.constants import WWW_BASE_URL

if TYPE_CHECKING:
    from dronefly.core.query.query import QueryResponse


def lifelists_url_from_query_response(query_response: "QueryResponse"):
    """Lifelists url for a user from query_response."""
    user = query_response.user
    obs_args = query_response.obs_args()
    # TODO: use taxon_id common ancestor if multiple taxon_ids
    #       - see `,related`
    # TODO: use place_id smallest enclosing (major) place if multiple place_ids
    #       - no place hierarchy support yet in dronefly
    url = f"{WWW_BASE_URL}/lifelists/{user.login}"
    lifelists_obs_args = {
        key: val
        for key in ("taxon_id", "place_id")
        if (val := obs_args.get(key)) and "," not in str(val)
    }
    if lifelists_obs_args:
        url += f"?{urlencode(lifelists_obs_args)}"
    return url


def obs_url_from_v1(params: dict):
    """Observations query URL corresponding to /v1/observations API params."""
    url = WWW_BASE_URL + "/observations"
    if params:
        if "observed_on" in params:
            _params = params.copy()
            _params["on"] = params["observed_on"]
            del _params["observed_on"]
        else:
            _params = params
        url += "?" + urlencode(_params)
    return url

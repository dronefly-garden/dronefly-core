from pyinaturalist.constants import V1_OBS_ORDER_BY_PROPERTIES
from pyinaturalist.controllers import (
    ObservationController as pyiNatObservationController,
)
from pyinaturalist.docs import copy_doc_signature
from pyinaturalist.docs import templates as docs
from pyinaturalist.models import Observation
from pyinaturalist.request_params import validate_multiple_choice_param
from pyinaturalist.v1 import get_observations

from ...paginator import Paginator


class ObservationController(pyiNatObservationController):
    @copy_doc_signature(*docs._get_observations, docs._only_id)
    def search(self, **params) -> Paginator[Observation]:
        params = validate_multiple_choice_param(
            params, "order_by", V1_OBS_ORDER_BY_PROPERTIES
        )
        params = self.client.add_defaults(get_observations, params)

        return Paginator(
            get_observations,
            Observation,
            loop=self.client.loop,
            annotation_callback=self.client.annotations.lookup,
            **params,
        )

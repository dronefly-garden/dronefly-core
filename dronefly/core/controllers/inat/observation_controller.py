from collections.abc import Callable

from pyinaturalist.constants import V1_OBS_ORDER_BY_PROPERTIES
from pyinaturalist.controllers import (
    ObservationController as pyiNatObservationController,
)
from pyinaturalist.docs import copy_doc_signature
from pyinaturalist.docs import templates as docs
from pyinaturalist.models import Annotation, BaseModel, Observation
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

        return ObservationPaginator(
            loop=self.client.loop,
            annotation_callback=self.client.annotations.lookup,
            **params,
        )


class ObservationPaginator(Paginator):
    """Paginate through observation results

    This also optionally fills in missing annotation information for each observation, using results
    from ``GET /controlled_terms``.
    """

    def __init__(
        self,
        request_function: Callable = get_observations,
        model: BaseModel = Observation,
        *args,
        annotation_callback: Callable[[list[Annotation]], list[Annotation]],
        **kwargs,
    ):
        super().__init__(request_function, model, *args, **kwargs)
        self.annotation_callback = annotation_callback

    def next_page(self) -> list[Observation]:
        observations = super().next_page()
        # Use cached controlled_terms lookup to fill in missing annotation details
        for obs in observations:
            obs.annotations = self.annotation_callback(obs.annotations)
        return observations

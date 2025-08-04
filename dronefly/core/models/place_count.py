from pyinaturalist.constants import JsonResponse, TableRow
from pyinaturalist.models import Place, define_model, field


@define_model
class PlaceCount(Place):
    """:fa:`place` An iNaturalist place, with an associated count of filtered IDs or observations"""

    count: int = field(default=0, doc="Filtered count for the place")
    observation_count: int = field(
        default=0, doc="Filtered count for the place's observations"
    )
    species_count: int = field(
        default=0, doc="Filtered count for the place's unique species observed"
    )

    @classmethod
    def from_json(cls, value: JsonResponse, **kwargs) -> "PlaceCount":
        """Flatten out count + place fields into a single-level dict before initializing"""
        if "results" in value:
            value = value["results"]
        if "place" in value:
            value = value.copy()
            value.update(value.pop("place"))
        if "observation_count" in value and "count" not in value:
            value["count"] = value["observation_count"]
        return super(PlaceCount, cls).from_json(value)

    @property
    def _row(self) -> TableRow:
        return {
            "ID": self.id,
            "Display Name": self.display_name,
            "Count": self.count,
        }

    def __str__(self) -> str:
        return super().__str__() + f": {self.count}"

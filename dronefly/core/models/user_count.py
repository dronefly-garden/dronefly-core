from pyinaturalist.models import UserCount as pyiNatUserCount, define_model, field


@define_model
class UserCount(pyiNatUserCount):
    """:fa:`place` An iNaturalist place, with an associated count of filtered IDs or observations"""

    countable_param: str = field(default="user_id")

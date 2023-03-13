from attrs import define


@define
class User:
    """Public class for User model."""

    id: int = 0
    inat_user_id: int = None
    inat_place_id: int = None
    inat_lang: str = None

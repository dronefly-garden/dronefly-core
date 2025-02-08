from attrs import define


@define
class TaxonListMetadata:
    ranks: str = "main ranks"
    rank_totals: dict[str] = {}
    count_digits: int = 0
    direct_digits: int = 0
    taxon_count: int = 0

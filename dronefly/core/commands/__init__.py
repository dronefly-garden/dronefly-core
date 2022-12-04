from pyinat import iNatClient

from ..parsers import NaturalParser
from ..formatters.discord import format_taxon_name

class Commands:
    # TODO: Use Dronefly client to apply any ctx-specific parameters
    def __init__(self, inat_client=iNatClient()):
        self.inat_client = inat_client
        self.parser = NaturalParser()

    def _parse(self, query_str):
        return self.parser.parse(query_str)

    def taxon(self, query_str: str):
        query = self._parse(query_str)
        # TODO: Handle all query clauses, not just main.terms
        # TODO: Doesn't do any ranking or filtering of results
        main_query_str = " ".join(query.main.terms)
        # TODO: Mock iNatClient response
        taxon = next(iter(self.inat_client.taxa.autocomplete(q=main_query_str)), None)
        if taxon:
            return format_taxon_name(taxon)
        return "Nothing found"

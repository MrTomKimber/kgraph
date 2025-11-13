from datetime import datetime
from rdflib.plugins.stores import sparqlstore, memory
from rdflib import URIRef, Literal, BNode, Dataset, Namespace
from rdflib import Graph as RDFGraph
from rdflib.namespace import RDF, RDFS


class KGStore:
    """Class for wrapping utility graph-store functions like
    query, load-data, delete data etc
    `store_type` parameter can be set to `memory` or `jena`
    """

    def __init__(self, **kwargs):
        """Initialising the Store defines default parameters and exposes
        a Dataset object as self.DS against-which various functions will
        operate."""

        kwarg_lower_d = {k.lower(): v for k, v in kwargs.items()}

        if "service" in kwarg_lower_d.keys():
            self.SERVICENAME = kwarg_lower_d.get("service")

        if "queryurl" in kwarg_lower_d.keys():
            self.QUERYURL = str(kwarg_lower_d.get("queryurl"))
        else:
            self.QUERYURL = f"http://localhost:3030/{self.SERVICENAME}/query"

        if "updateurl" in kwarg_lower_d.keys():
            self.UPDATEURL = str(kwarg_lower_d.get("updateurl"))
        else:
            self.UPDATEURL = f"http://localhost:3030/{self.SERVICENAME}/update"

        if "store_type" in kwarg_lower_d.keys():
            if kwarg_lower_d.get("store_type") == "memory":
                self.store = memory.Memory()
            elif kwarg_lower_d.get("store_type") == "jena":
                self.store = sparqlstore.SPARQLUpdateStore(
                    self.QUERYURL, context_aware=True
                )
                self.store.open((self.QUERYURL, self.UPDATEURL))
        self.DS = Dataset(
            store=self.store, default_union=True, default_graph_base="http://base.raw"
        )  # pyright: ignore[reportGeneralTypeIssues]

    def sparql(self, query):
        return self.DS.query(query)

    @staticmethod
    def triple_list_to_named_quad_iterator(triples: list[tuple], named_graph_uri: str):
        NGRAPH = URIRef(named_graph_uri)
        for s, p, o, *_ in triples:
            yield (s, p, o, NGRAPH)

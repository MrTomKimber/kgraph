"""Utility code for working with a knowledge graph store"""

from enum import Enum
from rdflib import Dataset, URIRef, BNode, Literal, Graph
from rdflib.plugins.stores import sparqlstore, memory
from rdflib.namespace import RDF
import uuid
from urllib.parse import urljoin

class StoreType(str, Enum):
    memory = "memory"
    jena = "jena"

DEFAULT_GRAPH_URI = "http://foo.bar/"

class KGStore:
    def __init__(self, 
             store_type : StoreType = StoreType.memory, 
             base_graph_uri : str = DEFAULT_GRAPH_URI,
             query_url : str | None = None, 
             update_url : str | None = None, 
             ):
        if store_type == StoreType.memory:
            self.store = memory.Memory()
        elif store_type == StoreType.jena:
            self.store = sparqlstore.SPARQLUpdateStore(query_url=query_url, 
                                                context_aware=True)
            if not any([v is None for v in [query_url, update_url]]):
                self.store.open((query_url, update_url))
            else:
                raise ValueError(f"Bad parameter, both query_url and update_url need populating.")

        self.base_graph_uri = base_graph_uri
        self.dataset = Dataset(store=self.store, 
                               default_union=True, 
                               default_graph_base = self.base_graph_uri)
    
    def list_graphs(self):
        """Return a list of all named graphs in the store"""
        # Note that self.store.contexts() returns a similar list, 
        # but one that might include empty graphs.
        # The sparql method returns only those graphs that contain
        # at least one triple.
        sparql_q = """SELECT distinct ?g 
        WHERE { GRAPH ?g { ?s ?p ?o } }"""

        return [r.get('g') for r in self.dataset.query(sparql_q)]
    
    def drop_graph(self, 
                   named_graph : URIRef) -> None:
        drop_graph_sparql = f"DROP GRAPH {named_graph.n3()}"
        if named_graph in self.list_graphs():
            self.dataset.update(drop_graph_sparql)
            self.store.commit()
            print(f"Graph `{named_graph}` dropped from store.")
        else:
            print(f"Graph `{named_graph}` not found in store.")

    def get_graph(self, 
                  graph_id : URIRef | None = None) -> Graph:
        if graph_id is None:
            unique_id = uuid.uuid4().hex
            graph_id = URIRef(urljoin(self.base_graph_uri, unique_id))
        store_graph = self.dataset.graph(graph_id)
        return store_graph

    def save_graph(self, 
                      data_graph : Graph,
                      graph_id : URIRef | None = None, 
                      ) -> URIRef:
        graph = self.get_graph(graph_id)
        triples = [(*t[0:3], graph.identifier) for t in data_graph.triples((None, None, None))]
        self.dataset.addN(triples)
        self.store.commit()
        print(f"Loaded {len(triples)} to Graph `{graph.identifier.toPython()}`")
        return graph
    
    def get_graph_metrics(self, 
                          data_graph : Graph, 
                          graph_id : URIRef) -> dict:
        total_triples = len(data_graph)
        predicates = set(data_graph.predicates())
        predicate_counts = {}
        for p in predicates:
            predicate_counts[p] = len(list(data_graph.triples((None, p, None))))
        types = set([t for _,_,t in data_graph.triples((None, RDF.type, None ))])
        type_counts={}
        for t in types:
            type_counts[t] = len(list(data_graph.triples((None, RDF.type, None))))
        typed_subjects = set(data_graph.subjects(RDF.type, None))
        all_subjects = set(data_graph.subjects())
        untyped_subjects = all_subjects - typed_subjects
        metrics_dict = { "triple_count" : total_triples, 
                         "predicates" : predicates, 
                         "predicate_count" : predicate_counts, 
                         "types" : types, 
                         "type_count" : type_counts, 
                         "untyped_count" : len(untyped_subjects)}
        return metrics_dict
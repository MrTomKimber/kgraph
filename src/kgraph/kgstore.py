"""Utility code for working with a knowledge graph store"""

from rdflib import Dataset, URIRef, BNode, Literal, Graph
from rdflib.plugins.stores import sparqlstore, memory
import uuid
from urllib.parse import urljoin

class KGStore:
    def __init__(self, 
             query_url, 
             update_url, 
             base_graph_uri):
        self.store = sparqlstore.SPARQLUpdateStore(query_url=query_url, 
                                              context_aware=True)
        self.store.open((query_url, update_url))
        self.base_graph_uri = base_graph_uri
        self.dataset = Dataset(store=self.store, 
                               default_union=True, 
                               default_graph_base = self.base_graph_uri)
    
    def list_graphs(self):
        """Return a list of all named graphs in the store"""
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
                      ) -> None:
        graph = self.get_graph(graph_id)
        triples = [(*t[0:3], graph.identifier) for t in data_graph.triples((None, None, None))]
        self.dataset.addN(triples)
        self.store.commit()
        print(f"Loaded {len(triples)} to Graph `{graph.identifier.toPython()}`")

    


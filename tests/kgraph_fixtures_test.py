import os
from pathlib import Path
current_dir = Path(__file__).parent

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import SKOS, RDF, RDFS
from pandas import read_excel, DataFrame
from importlib import resources

from kgraphing import declarations
from kgraphing.ingest import schemamapping
from kgraphing.ingest import kgpipeline
from kgraphing import rdfexplorer
from kgraphing.store import kgstore
from kgraphing.store import metadata
from kgraphing import ontologies, shapes

from kgraphing import gerf


@pytest.fixture(scope='session')
def schema_mapping_object() -> schemamapping.SchemaMapping:
    S = schemamapping.SchemaMapping(os.path.join(current_dir, "data/skos_vocabulary_mapping.json"))
    return S

@pytest.fixture(scope='session')
def raw_data_df() -> DataFrame:
    rd_df = read_excel(os.path.join(current_dir, "data/alphabet_vocab.xlsx"))
    return rd_df

@pytest.fixture(scope='session')
def serialised_graph(schema_mapping_object, raw_data_df) -> Graph:
    g = schema_mapping_object.to_rdf_graph(raw_data_df)
    g.serialize(os.path.join(current_dir, "data/ignore_alphabet_graph.rdf"), format="xml")
    return g

@pytest.fixture(scope='session')
def shacl_graph() -> Graph:
    g = Graph()
    g.parse(os.path.join(current_dir, "data/skos_vocabulary_mapping.json"))
    return g

@pytest.fixture(scope='session')
def kgp_pipeline() -> kgpipeline.KGraphPipeline:
    mapping_config_at = os.path.join(current_dir, "data/skos_vocabulary_mapping.json")
    validation_shacl = [str(resources.files(shapes) / os.path.normpath("kgnam_shacl.ttl"))]

    kgp = kgpipeline.KGraphPipeline(mapping_config_at,
                                validation_shacl)
    
    return kgp

@pytest.fixture(scope='session') 
def kgp_graph(kgp_pipeline, raw_data_df) -> Graph:
    g = kgp_pipeline.process(raw_data_df)
    return g

@pytest.fixture(scope='session')
def explorer_obj(kgp_graph):
    Explorer = rdfexplorer.RDFExplorer(kgp_graph)
    return Explorer

@pytest.fixture(scope='session')
def in_memory_store() -> kgstore.KGStore:
    store_type=kgstore.StoreType.memory
    kgs = kgstore.KGStore(store_type, base_graph_uri="http://kgraph.foo.bar")
    return kgs

@pytest.fixture(scope='session')
def toy_graph(scope='session'):
    toy_graph = Graph()
    toy_graph.add((URIRef('http://kgraph.foo.bar#example1'), 
                URIRef('http://kgraph.foo.bar#predicate'), 
                URIRef('http://kgraph.foo.bar#example2')))
    return toy_graph

@pytest.fixture(scope='session')
def ontology_cache(scope='session'):
    """Create an empty OntologyCache object"""
    OC = gerf.OntologyCache(os.path.join(current_dir, "data/ocache"))
    OC.purge() # Delete any remaining content that might exist from an earlier run
    return OC

@pytest.fixture(scope='session')
def rdf2dict_of_serialised_graph(ontology_cache, serialised_graph, scope='session'):
    rdf2d = gerf.Gerf(serialised_graph, ontology_cache)
    return rdf2d

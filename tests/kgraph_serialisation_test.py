import sys, os
from pathlib import Path
current_dir = Path(__file__).parent
repo_path = os.path.abspath(os.path.join(current_dir, "../src"))
if repo_path not in sys.path:
    sys.path.append(repo_path)

import pytest
import pandas as pd
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import SKOS, RDF, RDFS
from pyshacl import validate

from kgraph import declarations
from kgraph import schemamapping
from kgraph import kgpipeline
from kgraph import rdfexplorer


@pytest.fixture(scope='session')
def schema_mapping_object() -> schemamapping.SchemaMapping:
    S = schemamapping.SchemaMapping(os.path.join(current_dir, "data/skos_vocabulary_mapping.json"))
    return S

@pytest.fixture(scope='session')
def raw_data_df() -> pd.DataFrame:
    rd_df = pd.read_excel(os.path.join(current_dir, "data/alphabet_vocab.xlsx"))
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
    ontology_list = [os.path.join(current_dir, "../src/kgraph/ontologies/kgmeta.owl"), 
                    os.path.join(current_dir, "../src/kgraph/ontologies/skos.rdf")]
    validation_shacl = [os.path.join(current_dir, "../src/kgraph/ontologies/kgmeta_shacl.ttl")]

    kgp = kgpipeline.KGraphPipeline(mapping_config_at,
                                ontology_list,
                                validation_shacl)
    
    return kgp

@pytest.fixture(scope='session') 
def kgp_graph(kgp_pipeline, raw_data_df) -> Graph:
    g = kgp_pipeline.process(raw_data_df)
    return g


def test_instantiate_schema_mapping_isdataframe(schema_mapping_object):
    """Instantiate a schema_mapping object"""
    S = schema_mapping_object
    assert isinstance(S, schemamapping.SchemaMapping)

def test_serialise_data_isgraph(serialised_graph):
    g = serialised_graph
    assert isinstance(g, Graph)

def test_serialised_concept_count(serialised_graph):
    """In an pre-prepared list of definitions, the expected number of Concepts is 26"""
    extracted_concepts=[s for s,_,_ in serialised_graph.triples((None, RDF.type, SKOS.Concept))]
    extracted_concept_names = [
        n
        for s in extracted_concepts
        for _,_,n in serialised_graph.triples((s, declarations.KGMETA.FullyQualifiedName, None))
    ]

    assert len(extracted_concept_names) == 32
    assert sorted(extracted_concept_names) == [Literal(n) 
                                       for n in ['Vocabularies.Test.TestAlphabetVocab.Apple',
                                                 'Vocabularies.TestAlphabetVocab.Animal', 'Vocabularies.TestAlphabetVocab.Apple',
                                                 'Vocabularies.TestAlphabetVocab.Artifact',
                                                'Vocabularies.TestAlphabetVocab.Banana', 'Vocabularies.TestAlphabetVocab.Cat',
                                                'Vocabularies.TestAlphabetVocab.Dog', 'Vocabularies.TestAlphabetVocab.Elephant',
                                                'Vocabularies.TestAlphabetVocab.Fox', 'Vocabularies.TestAlphabetVocab.Fruit',
                                                'Vocabularies.TestAlphabetVocab.Goat', 'Vocabularies.TestAlphabetVocab.House',
                                                'Vocabularies.TestAlphabetVocab.Imagination', 'Vocabularies.TestAlphabetVocab.Jungle',
                                                'Vocabularies.TestAlphabetVocab.King', 'Vocabularies.TestAlphabetVocab.Lemon',
                                                'Vocabularies.TestAlphabetVocab.Monarch', 'Vocabularies.TestAlphabetVocab.Mouse',
                                                'Vocabularies.TestAlphabetVocab.Nest', 'Vocabularies.TestAlphabetVocab.Octopus',
                                                'Vocabularies.TestAlphabetVocab.Parrot', 'Vocabularies.TestAlphabetVocab.Queen',
                                                'Vocabularies.TestAlphabetVocab.Rain', 'Vocabularies.TestAlphabetVocab.Structure',
                                                'Vocabularies.TestAlphabetVocab.Sun', 'Vocabularies.TestAlphabetVocab.Train', 
                                                'Vocabularies.TestAlphabetVocab.Umbrella', 'Vocabularies.TestAlphabetVocab.Village', 
                                                'Vocabularies.TestAlphabetVocab.Wheel', 'Vocabularies.TestAlphabetVocab.Xylophone', 
                                                'Vocabularies.TestAlphabetVocab.Yak', 'Vocabularies.TestAlphabetVocab.Zebra',
                                                ]
                                                                                    ]
    
def test_post_schema_mapping_shacl_validation(serialised_graph):
    ont = Graph()
    ont.parse(os.path.join(current_dir, "../src/kgraph/ontologies/kgmeta.owl"))
    conforms, results_g, results_t = validate(
                                            serialised_graph, 
                                            shacl_graph=declarations.KGMETA_SHAPES_G, 
                                            ont_graph=ont, 
                                            inference='rdfs', 
                                            abort_on_first=False, 
                                            allow_infos=False, 
                                            allow_warnings=False, 
                                            meta_shacl=False, 
                                            advanced=False, 
                                            js=False, 
                                            debug=False
                                        )
    assert conforms == True

def test_kgpipeline_is_a_pipeline(kgp_pipeline):
    assert isinstance(kgp_pipeline, kgpipeline.KGraphPipeline)

def test_kgpipeline_graph_is_a_graph(kgp_graph):
    assert isinstance(kgp_graph, Graph)

def test_kgpipeline_graph_validation_is_true(kgp_pipeline, kgp_graph):
    assert kgp_pipeline.shacl_validation_results[0][0]==True


def test_kgpipeline_graph_matches_alt_graph(kgp_graph, serialised_graph):
    assert len(kgp_graph)==len(serialised_graph)



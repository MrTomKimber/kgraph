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
from kgraph import declarations
from kgraph import serialisation
from pyshacl import validate


@pytest.fixture(scope='session')
def serialisation_object() -> serialisation.Serialisation:
    S = serialisation.Serialisation(os.path.join(current_dir, "data/skos_vocabulary_serialisation.json"))
    return S

@pytest.fixture(scope='session')
def raw_data_df() -> pd.DataFrame:
    rd_df = pd.read_excel(os.path.join(current_dir, "data/alphabet_vocab.xlsx"))
    return rd_df

@pytest.fixture(scope='session')
def serialised_graph(serialisation_object, raw_data_df) -> Graph:
    g = serialisation_object.to_rdf_graph(raw_data_df)
    g.serialize("alphabet_graph.rdf", format="xml")
    return g

@pytest.fixture(scope='session')
def shacl_graph() -> Graph:
    g = Graph()
    g.parse(os.path.join(current_dir, "data/skos_vocabulary_serialisation.json"))
    return g

def test_instantiate_serialisation_isdataframe(serialisation_object):
    """Instantiate a serialisation object"""
    S = serialisation_object
    assert isinstance(S, serialisation.Serialisation)

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

    assert len(extracted_concept_names) == 31
    assert sorted(extracted_concept_names) == [Literal(n) 
                                       for n in ['Vocabularies.TestAlphabetVocab.Animal', 'Vocabularies.TestAlphabetVocab.Apple',
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
                                                'Vocabularies.TestAlphabetVocab.Yak', 'Vocabularies.TestAlphabetVocab.Zebra']
                                                                                    ]
    
def test_post_serialisation_shacl_validation(serialised_graph):
    conforms, results_g, results_t = validate(
                                            serialised_graph, 
                                            shacl_graph=declarations.KGMETA_SHAPES_G, 
                                            ont_graph=None, 
                                            inference=None, 
                                            abort_on_first=False, 
                                            allow_infos=False, 
                                            allow_warnings=False, 
                                            meta_shacl=False, 
                                            advanced=False, 
                                            js=False, 
                                            debug=False
                                        )
    

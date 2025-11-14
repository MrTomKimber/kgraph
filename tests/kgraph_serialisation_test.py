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
    g = serialisation_object.serialise(raw_data_df)
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
        for _,_,n in serialised_graph.triples((s, RDFS.label, None))
    ]

    assert len(extracted_concept_names) == 26
    assert sorted(extracted_concept_names) == [Literal(n) 
                                       for n in ['Apple', 'Banana', 'Cat', 'Dog', 'Elephant', 
                                       'Fox', 'Goat', 'House', 'Imagination', 'Jungle', 
                                       'King', 'Lemon', 'Mouse', 'Nest', 'Octopus', 
                                       'Parrot', 'Queen', 'Rain', 'Sun', 'Train', 
                                       'Umbrella', 'Village', 'Wheel', 'Xylophone', 'Yak', 
                                       'Zebra']
                                      ]




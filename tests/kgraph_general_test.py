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

from kgraph_fixtures_test import (raw_data_df, 
                                  schema_mapping_object, 
                                  serialised_graph, 
                                  kgp_pipeline, 
                                  kgp_graph, 
                                  explorer_obj)


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

def test_rdfexplorer_is_instance_of(explorer_obj):
    assert isinstance(explorer_obj, rdfexplorer.RDFExplorer)

def test_rdfexplorer_get_types(explorer_obj):
    s_types = explorer_obj._get_all_types_in_graph().union(set([RDF.type]))
    assert s_types == {URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'),
                        URIRef('http://www.w3.org/2004/02/skos/core#Concept'),
                        URIRef('http://www.w3.org/2004/02/skos/core#ConceptScheme'),
                        URIRef('https://kgraph.foo/onto/kgmeta#Namespace')}


def test_rdfexplorer_gen_entity_report(explorer_obj):
    s_types = explorer_obj._get_all_types_in_graph().union(set([RDF.type]))
    e_dict = explorer_obj.gen_entity_report_dict_for_types(s_types)
    assert len(e_dict.keys())==35
    assert all(v.got_neighbours for v in e_dict.values())

def test_rdfexplorer_gen_entity_report_all_keys(explorer_obj):
    s_types = explorer_obj._get_all_types_in_graph().union(set([RDF.type]))
    e_dict = explorer_obj.gen_entity_report_dict_for_types(s_types)
    e_store_objects = {k:v for k,v in explorer_obj.entity_store.items() if v.type=='object'}
    assert all([all([k in ['title', 'property_table','outbound_links','inbound_links']]) for q in [
        v.html_components(configuration={})
        for k,v in e_store_objects.items()
    ] for k in q.keys()])


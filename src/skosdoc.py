"""A small utility for generating html to describe a skos vocabulary"""

from rdflib.namespace import RDF, RDFS, SKOS
from rdflib import URIRef, Literal, Graph as rdflibGraph

skos_extract_pattern = {
    ""
}

def extract_skos_concept_scheme_uris(skos_graph :rdflibGraph)->set[URIRef]:
    concept_scheme_uris = set([s for s,_,_ in list(skos_graph.triples((None, RDF.type, SKOS.ConceptScheme)))])
    return concept_scheme_uris

def extract_skos_concept_uris_for_concept_scheme(skos_graph :rdflibGraph, concept_scheme_uri: URIRef)->set[URIRef]:
    concept_uris = set([s for s,_,_ in list(skos_graph.triples((None, RDF.type, SKOS.Concept)))])
    concept_uris_in_scheme = set([s for s,_,_ in list(skos_graph.triples((None, SKOS.inScheme, concept_scheme_uri)))])
    return concept_uris.union(concept_uris_in_scheme)

def pull_literals_for_subject(skos_graph : rdflibGraph, subject : URIRef)->list[tuple[URIRef, Literal]]:
    literal_triples=[]
    for _, p, o in skos_graph.triples((subject, None, None)):
        if isinstance(o, Literal):
            literal_triples.append((p, o))
    return sorted(literal_triples)


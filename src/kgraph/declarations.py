from typing import Tuple, TypeAlias, Union
from rdflib import URIRef, Literal, BNode

# Define the type-aliases used to handle triple contents
RDFSubjectAtom: TypeAlias = Union[URIRef, BNode]
RDFPredicateAtom: TypeAlias = URIRef
RDFObjectAtom: TypeAlias = Union[URIRef, BNode, Literal]
RDFTriple: TypeAlias = Tuple[RDFSubjectAtom, RDFPredicateAtom, RDFObjectAtom]
RDFQuad: TypeAlias = Tuple[URIRef, RDFSubjectAtom, RDFPredicateAtom, RDFObjectAtom]


def create_fixed_po_triples_for_s_list(subjects : list[URIRef], predicate : URIRef, object : RDFObjectAtom) -> set[RDFTriple]:
    """With a list of subjects, and a fixed predicate/object combination, generate a set of RDFTriples"""
    triples = set()
    for s in subjects:
        triples.add((s, predicate, object))
    return triples


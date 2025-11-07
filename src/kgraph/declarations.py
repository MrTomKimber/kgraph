from typing import Tuple, TypeAlias, Union
from rdflib import URIRef, Literal, BNode

# Define the type-aliases used to handle triple contents
RDFTripleSubject: TypeAlias = Union[URIRef, BNode]
RDFTriplePredicate: TypeAlias = URIRef
RDFTripleObject: TypeAlias = Union[URIRef, BNode, Literal]
RDFTriple: TypeAlias = Tuple[RDFTripleSubject, RDFTriplePredicate, RDFTripleObject]
RDFQuad: TypeAlias = Tuple[URIRef, RDFTripleSubject, RDFTriplePredicate, RDFTripleObject]


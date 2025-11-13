"""This module defines shared definitions and reference resources 
to be imported by other modules within the package"""

import os
from importlib import resources
from typing import Tuple, TypeAlias, Union
from rdflib import URIRef, Literal, BNode
from rdflib import Graph as rdflibGraph
from rdflib.namespace import Namespace
import json
import kgraph.ontologies, kgraph.jschema

# SERIALISATIONSCHEMA is the json-schema that validates serialisation configuration files
with resources.as_file(resources.files(kgraph.jschema) / os.path.normpath("serialisationschema.json")) as serialisation_schema_file:
    with serialisation_schema_file.open('r', 
                                        encoding='utf-8',
                                        errors='strict') as serialisation_schema:
        SERIALISATIONSCHEMA = json.load(serialisation_schema)

# KGMETA is the fixed namespace used by the kgraph suite of utilities
# Here the namespace is defined, and the underlying ontology resource
# is openend as an rdflib-Graph object, to which are bound core ontology
# namespaces to the graph's namespace manager.
KGMETA = Namespace("https://kgraph.foo/onto/kgmeta#")
KGMETA_G = rdflibGraph()

with resources.as_file(resources.files(kgraph.ontologies) / os.path.normpath("kgmeta.owl")) as kgmeta_owl:
    KGMETA_G.parse(kgmeta_owl, format='xml')
    KGMETA_G.bind("KGMETA", KGMETA.title.toPython())

KGMETA_SHAPES_G = rdflibGraph()
with resources.as_file(resources.files(kgraph.ontologies) / os.path.normpath("kgmeta_shacl.ttl")) as kgmeta_shapes:
    KGMETA_SHAPES_G.parse(kgmeta_shapes, format='ttl')
    KGMETA_SHAPES_G.bind("KGMETA", KGMETA.title.toPython())



# Define the type-aliases used to handle triple contents
RDFSubjectAtom: TypeAlias = Union[URIRef, BNode]
RDFPredicateAtom: TypeAlias = URIRef
RDFObjectAtom: TypeAlias = Union[URIRef, BNode, Literal]
RDFTriple: TypeAlias = Tuple[RDFSubjectAtom, RDFPredicateAtom, RDFObjectAtom]
RDFQuad: TypeAlias = Tuple[URIRef, RDFSubjectAtom, RDFPredicateAtom, RDFObjectAtom]


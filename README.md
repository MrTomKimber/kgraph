# kgraph

*kgraph* (potentially to be renamed to *kgstore*) is a suite of components for working with knowledge graph data.

The primary components are a jena/fuseki server that acts as a persistent graph store, and a flask front-end that provides a convenient user-interface for various functions.

The purpose of *kgstore* is to capture utilities that (usually) require a knowledge-graph store - these might include querying capabilities, the use of shacl, inferencing and similar.

Additional utilities within the kg-universe should tie-in nicely within the above framework, but are also applicable to stand-alone situations.
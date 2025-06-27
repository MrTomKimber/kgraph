# kgraph

*kgraph* is a suite of components for working with knowledge graph data.

Two main components are a jena/fuseki server that acts as a persistent graph store, and a flask front-end that provides a convenient user-interface for various functions. 

Additional utilities found within this package should work within the above framework, but also ought to be applicable to stand-alone situations. 

The framework is designed to be modular and extensible but offer the following capabilities:

1) A simplified meta-data framework, enabling schemas to be quickly authored and serialised
2) A straight-forward data-to-rdf serialisation routine, enabling raw data to be uploaded into meaningful knowledge graphs without frustration
3) Useful querying and visualisation options for exploring the knowledge uploaded to the KG



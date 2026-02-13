"""Templating and utilities for defining a simple data-catalogue within a knowledge graph:
See: https://www.w3.org/TR/vocab-dcat/"""

from dataclasses import dataclass, asdict
from rdflib import URIRef, Literal, Graph
from rdflib.namespace import RDF, RDFS, DCAT, DCTERMS
import datetime


@dataclass
class NamedGraphMetaData:
    uri : URIRef # The uri of the named graph
    title : str # The title of the named graph
    label : str # The label to be used for the named graph
    language : str # ISO language value - conforming to https://www.rfc-editor.org/info/bcp47
    description: str # DCTERMS.description
    is_dataset: bool 
    is_catalogue: bool
    created : datetime.datetime # http://purl.org/dc/terms/W3CDTF
    modified : datetime.datetime # http://purl.org/dc/terms/W3CDTF



    def to_graph(self):
        # Return the metadata package as an rdflib Graph object
        triple_list = []
        if self.is_catalogue:
            identity_triple = (self.uri, RDF.type, DCAT.Catalog)
        elif self.is_dataset:
            identity_triple = (self.uri, RDF.type, DCAT.Dataset)
        else:
            identity_triple = (self.uri, RDF.type, DCAT.Resource)

        title_triple = (self.uri, DCTERMS.title, Literal(self.title, lang=self.language))
        label_triple = (self.uri, RDFS.label, Literal(self.label, lang=self.language))
        description_triple = (self.uri, DCTERMS.description, Literal(self.description, lang=self.language))
        created_triple = (self.uri, DCTERMS.created, self.created.isoformat(), DCTERMS.W3CDTF)
        modified_triple = (self.uri, DCTERMS.created, self.modified.isoformat(), DCTERMS.W3CDTF)
        triple_list.extend(
            [identity_triple, 
            title_triple, 
            label_triple, 
            description_triple, 
            created_triple, 
            modified_triple]
        )
        g = Graph()
        g.bind("dcterms", DCTERMS)
        g.bind("dcat", DCAT)
        for t in triple_list:
            g.add(t)
        return g
        





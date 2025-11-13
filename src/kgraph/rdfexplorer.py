"""A small generalised utility for extracting detail from an rdflib graph"""

from dataclasses import dataclass, asdict
from enum import Enum, StrEnum
from rdflib.namespace import RDF, RDFS, SKOS, XSD
from rdflib import Container, URIRef, Literal, Graph as rdflibGraph, Namespace
from rdflib.term import Node, Identifier
from kgraph.declarations import (
    RDFTriple,
    RDFQuad,
    RDFSubjectAtom,
    RDFPredicateAtom,
    RDFObjectAtom,
)

from kgraph.declarations import KGMETA, KGMETA_G


PYTHON2XSDDATATYPEMAPPING = {
    "bool": XSD.boolean,
    "bytes": [XSD.hexBinary, XSD.base64Binary],
    "Decimal": XSD.decimal,
    "float": [XSD.float, XSD.double],
    "int": XSD.integer,
    "QName": XSD.QName,
    "str": XSD.string,
    "XmlDate": XSD.date,
    "XmlDateTime": XSD.dateTime,
    "XmlDuration": XSD.duration,
    "XmlPeriod": [XSD.gYearMonth, XSD.gYear, XSD.gMonthDay, XSD.gMonth, XSD.gDay],
    "XmlTime": XSD.time,
}


def uri_split(uriref):
    frag = uriref.fragment
    prefrag = str(uriref)[0 : -len(frag)]
    return prefrag, frag


@dataclass
class GraphData:
    """Dataclass for handling graph-links from an object to other objects"""

    subject: Identifier
    subject_namespace_str: str
    subject_h_label: str
    subject_t_label: str
    subject_types: list
    subject_type_labels: list[str]
    outgoing_predicates: list[URIRef]
    outgoing_predicate_labels: list[str]
    incoming_predicates: list[URIRef]
    incoming_predicate_labels: list[str]

    def to_dict(self):
        return asdict(self)


@dataclass
class GraphLiteralData(GraphData):
    """Dataclass for handling graph-links from an object to other objects"""

    subject: Literal
    value: object
    subject_types: list


@dataclass
class GraphEntityData(GraphData):
    """Dataclass for handling graph-links from an object to other objects"""

    subject: URIRef
    value: URIRef
    subject_types: list[URIRef]


class GraphEntity(object):

    __default_technical_label_prefs = [
        KGMETA.FullyQualifiedName,
        KGMETA.Name,
        RDFS.label,
        SKOS.prefLabel,
    ]
    __default_human_label_prefs = [
        RDFS.label,
        SKOS.prefLabel,
        KGMETA.Name,
        KGMETA.FullyQualifiedName,
    ]
    __entity_types = StrEnum("EntityType", ["object", "literal", "other"])

    def __init__(
        self,
        graph: rdflibGraph,
        uri: Identifier,
        entity_store: dict[Identifier, "GraphEntity"] | None = None,
        technical_label_prefs=None,
        human_label_prefs=None,
    ):
        self.graph = graph

        if technical_label_prefs is None:
            self.technical_label_prefs = GraphEntity.__default_technical_label_prefs

        if human_label_prefs is None:
            self.human_label_prefs = GraphEntity.__default_human_label_prefs

        if entity_store is not None:
            self.entity_store = entity_store
        else:
            self.entity_store = dict()

        if isinstance(uri, URIRef):
            self.uri = uri
            self.identifier = uri
            self.type = GraphEntity.__entity_types.object
            self._setup_uriref()
        elif isinstance(uri, Literal):
            self.literal = uri
            self.identifier = uri
            self.type = GraphEntity.__entity_types.literal
            self._setup_literal()

        self.got_neighbours = False

    def get_outgoing_linked_entity_data(
        self,
    ):  # pyright: ignore[reportUndefinedVariable]

        link_paths = list()
        predicate_list = self.data.outgoing_predicates

        # Identify what objects are at the other end of the links

        if self.type == "object":
            for p in predicate_list:
                subject = self.uri
                link_paths.append(
                    (p, list(self.graph.objects(subject, p, unique=True)))
                )
        elif self.type == "literal":
            pass  # This makes the assumption that literal data points do not carry any linked_entities

        link_pointers = set([o for _, olist in link_paths for o in olist])
        link_objects_dict = dict()

        for candidate_object in link_pointers:
            if candidate_object in self.entity_store.keys():
                link_objects_dict[candidate_object] = self.entity_store[
                    candidate_object
                ]
        remaining_pointers = link_pointers - set(link_objects_dict.keys())
        for candidate_object in remaining_pointers:
            if candidate_object not in link_objects_dict.keys():
                new_entity = GraphEntity(
                    self.graph, candidate_object, entity_store=self.entity_store
                )
                # Update the shared entity_store with new entity values
                self.entity_store[candidate_object] = new_entity
                link_objects_dict[candidate_object] = new_entity

        return link_objects_dict

    def get_incoming_linked_entity_data(
        self,
    ):  # pyright: ignore[reportUndefinedVariable]

        link_paths = list()
        predicate_list = self.data.incoming_predicates

        # Identify what objects are at the other end of the links
        if self.type == "object":
            object = self.uri
        elif self.type == "literal":
            object = self.literal

        for p in predicate_list:
            link_paths.append(
                (p, list(self.graph.subjects(object=object, predicate=p, unique=True)))
            )

        link_pointers = set([s for _, slist in link_paths for s in slist])
        link_objects_dict = dict()

        for candidate_object in link_pointers:
            if candidate_object in self.entity_store.keys():
                link_objects_dict[candidate_object] = self.entity_store[
                    candidate_object
                ]
        remaining_pointers = link_pointers - set(link_objects_dict.keys())
        for candidate_object in remaining_pointers:
            if candidate_object not in link_objects_dict.keys():
                new_entity = GraphEntity(
                    self.graph, candidate_object, entity_store=self.entity_store
                )
                # Update the shared entity_store with new entity values
                self.entity_store[candidate_object] = new_entity
                link_objects_dict[candidate_object] = new_entity

        return link_objects_dict

    def _setup_literal(self):
        """Where the entity has been identified as being a Literal, capture appropriate dataclass values"""
        value = self.literal.toPython()
        if self.literal.datatype is None:
            types = [
                PYTHON2XSDDATATYPEMAPPING.get(
                    type(value).__name__, URIRef(type(value).__name__)
                )
            ]
        else:
            types = [self.literal.datatype]

        incoming_predicates = sorted(list(self._get_object_predicates(self.literal)))
        incoming_predicate_labels = [
            str(
                self._resolve_to_python_primitive(
                    self._get_result_from_preference_list(
                        t, GraphEntity.__default_human_label_prefs
                    )
                )
            )
            for t in incoming_predicates
        ]

        self.data = GraphLiteralData(
            subject=self.literal,
            subject_namespace_str="",
            value=value,
            subject_h_label=str(value),
            subject_t_label=str(value),
            subject_types=types,
            subject_type_labels=[t.n3(self.graph.namespace_manager) for t in types],
            outgoing_predicates=[],  # Set outgoing_predicates to empty list for a Literal
            outgoing_predicate_labels=[],
            incoming_predicates=incoming_predicates,
            incoming_predicate_labels=incoming_predicate_labels,
        )

    def _setup_uriref(self):
        """Where the entity has been identified as an Object (URIRef), capture appropriate dataclass values"""
        # Careful to ensure that types and labels are aligned in terms of their ordering, to ensure the right type<-->labels can be recovered
        subject_types = sorted(list(self._get_subject_types(self.uri)))
        subject_type_labels = [
            str(
                self._resolve_to_python_primitive(
                    self._get_result_from_preference_list(
                        t, GraphEntity.__default_human_label_prefs
                    )
                )
            )
            for t in subject_types
        ]

        outgoing_predicates = sorted(list(self._get_subject_predicates(self.uri)))
        outgoing_predicate_labels = [
            str(
                self._resolve_to_python_primitive(
                    self._get_result_from_preference_list(
                        t, GraphEntity.__default_human_label_prefs
                    )
                )
            )
            for t in outgoing_predicates
        ]

        incoming_predicates = sorted(list(self._get_object_predicates(self.uri)))
        incoming_predicate_labels = [
            str(
                self._resolve_to_python_primitive(
                    self._get_result_from_preference_list(
                        t, GraphEntity.__default_human_label_prefs
                    )
                )
            )
            for t in incoming_predicates
        ]

        self.data = GraphEntityData(
            subject=self.uri,
            subject_namespace_str=uri_split(self.uri)[0],
            value=self.uri,
            subject_h_label=self._get_subject_human_label(self.uri),
            subject_t_label=self._get_subject_technical_label(self.uri),
            subject_types=list(subject_types),
            subject_type_labels=list(subject_type_labels),
            outgoing_predicates=outgoing_predicates,
            outgoing_predicate_labels=outgoing_predicate_labels,
            incoming_predicates=incoming_predicates,
            incoming_predicate_labels=incoming_predicate_labels,
        )

    def get_neighbours(self):

        self.get_outgoing_linked_entity_data()
        outgoing_linked_neighbours = []

        for p in self.data.outgoing_predicates:
            for o in self._get_objects(self.uri, p):
                outgoing_linked_neighbours.append(
                    (
                        GraphEntity(self.graph, p, self.entity_store),
                        GraphEntity(self.graph, o, self.entity_store),
                    ),
                )
        self.outgoing_linked_neighbours = outgoing_linked_neighbours

        self.get_incoming_linked_entity_data()
        incoming_linked_neighbours = []

        for p in self.data.incoming_predicates:
            for o in self._get_subjects(self.identifier, p):
                incoming_linked_neighbours.append(
                    (
                        GraphEntity(self.graph, p, self.entity_store),
                        GraphEntity(self.graph, o, self.entity_store),
                    ),
                )
        self.incoming_linked_neighbours = incoming_linked_neighbours

        self.got_neighbours = True

    def _resolve_to_python_primitive(self, content: Node) -> int | float | str | None:
        if isinstance(content, URIRef):
            return content.n3(namespace_manager=self.graph.namespace_manager)
        elif isinstance(content, Literal):
            return content.toPython()
        return None

    def _get_subject_predicates(self, subject: URIRef) -> set[URIRef]:
        return set(
            [p for p in self.graph.predicates(subject=subject, object=None)]
        )  # pyright: ignore[reportReturnType]

    def _get_object_predicates(self, object: Identifier) -> set[URIRef]:
        return set(
            [p for p in self.graph.predicates(subject=None, object=object)]
        )  # pyright: ignore[reportReturnType]

    def _get_subject_human_label(self, subject: URIRef) -> str:
        h_term = self._resolve_to_python_primitive(
            self._get_result_from_preference_list(
                subject, GraphEntity.__default_human_label_prefs
            )
        )
        return str(h_term)

    def _get_subject_technical_label(self, subject: URIRef) -> str:
        h_term = self._resolve_to_python_primitive(
            self._get_result_from_preference_list(
                subject, GraphEntity.__default_technical_label_prefs
            )
        )
        return str(h_term)

    def _get_subject_types(self, subject: URIRef) -> set[URIRef]:
        types = set()
        for t in self.graph.objects(subject=subject, predicate=RDF.type):
            types.add(t)
        return types

    def _get_objects(self, subject: URIRef, predicate: URIRef) -> set[URIRef]:
        predicate_objects = set()
        for o in self.graph.objects(subject=subject, predicate=predicate):
            predicate_objects.add(o)
        return predicate_objects

    def _get_subjects(self, object: Identifier, predicate: URIRef) -> set[URIRef]:
        predicate_subjects = set()
        for s in self.graph.subjects(object=object, predicate=predicate):
            predicate_subjects.add(s)
        return predicate_subjects

    def _get_result_from_preference_list(
        self, subject: URIRef, preferences: list[URIRef]
    ) -> Node:
        for p in preferences:
            fetch_lits = [o for o in self.graph.objects(subject=subject, predicate=p)]
            if len(fetch_lits) > 0:
                return fetch_lits[0]

        # Nothing found, convert the object's URIRef into a stringlike value and serve as a Literal
        # (Ideally shortened depending on the namespace_manager associated with the graph)
        return Literal(subject.n3(self.graph.namespace_manager))


# Collection of base methods for generating triples given various input combinations
def create_triples_from_slist_p_o(
    subjects: list[URIRef], predicate: URIRef, object: RDFObjectAtom
) -> set[RDFTriple]:
    """With a list of subjects, and a fixed predicate/object combination, generate a set of RDFTriples"""
    triples = set()
    for s in subjects:
        triples.add((s, predicate, object))
    return triples


class RDFExplorer(object):
    """A utility class for extracting content from an rdflib graph object
    After initial setup, various methods exist for generating lists of objects,
    perhaps selecting by type, or as the result of a query.
    These lists of object identifiers (URIs) are used to drive extracts of subject-centric
    graph reports"""

    def __init__(
        self,
        rdf_g: rdflibGraph,
        entity_store: dict[Identifier, "GraphEntity"] | None = None,
    ) -> None:
        """An object wrapper used to extract data from the graph and expose it as a set of type-centric
        python-dicts"""
        self.graph = rdf_g
        if entity_store is None:
            self.entity_store = dict()
        else:
            self.entity_store = entity_store

    def get_entity_details(self, subject: URIRef) -> GraphEntity:
        return GraphEntity(self.graph, subject, self.entity_store)

    def gen_entity_report_dict(
        self, subjects: list[URIRef]
    ) -> dict[URIRef, GraphEntity]:
        """Generate a collection of entity details based on the list of subjects provided in the parameters
        Note that a side-effect of the fetch process updates the self.entity_store object which serves
        as an index/memory cache. If the object has already been fetched previously, the detail will be
        returned from there."""

        sdict = dict()
        for subject in subjects:
            sdict[subject] = self.get_subject_and_neighbours(subject)
        return sdict

    def get_subject_and_neighbours(self, subject: URIRef):
        entity = self.get_entity_details(subject)
        entity.get_neighbours()
        return entity

    def _get_subjs_by_type(self, type_uri: URIRef) -> set[Identifier]:
        subj_uris = set(
            [s for s, _, _ in list(self.graph.triples((None, RDF.type, type_uri)))]
        )
        return subj_uris  # pyright: ignore[reportReturnType]

    def gen_index(self, data_attribute):
        """Create an unsorted index from data_attribute (as key) to a set of references on self.entity_store keys"""
        index = dict()
        for k, v in self.entity_store.items():
            if hasattr(v.data, data_attribute):
                data = v.data.__getattribute__(data_attribute)
            elif hasattr(v, data_attribute):
                data = v.__getattribute__(data_attribute)
            else:
                data = None
            if isinstance(data, (list, tuple, set, dict)):
                data = frozenset(data)
            else:
                data = frozenset([data])
            if data not in index.keys():
                index[data] = set()

            index[data].add(k)
        return index

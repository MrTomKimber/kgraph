"""A small generalised utility for extracting detail from an rdflib graph"""

from dataclasses import dataclass, asdict
from enum import Enum, StrEnum
from rdflib.namespace import RDF, RDFS, SKOS, XSD
from rdflib import Container, URIRef, Literal, Graph as rdflibGraph, Namespace
from rdflib.term import Node, Identifier
import re
import networkx as nx
from html import escape

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
class EdgeData:
    """Dataclass for expressing edges between entities in the graph"""
    subject: Identifier  # used to store the uri-ref of the subject
    predicate: Identifier # used to store the uri-ref of the predicate
    object: Identifier # used to store the uri-ref of the object
    predicate_label: str # contains the predicate-label for display

    def to_dict(self):
        return asdict(self)

@dataclass(frozen=True)
class NodeData:
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
    is_possible_url: bool

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class GraphLiteralData(NodeData):
    """Dataclass for handling graph-links from an object to other objects"""

    subject: Literal
    value: object
    subject_types: list
    


@dataclass(frozen=True)
class GraphEntityData(NodeData):
    """Dataclass for handling graph-links from an object to other objects"""

    subject: URIRef 
    value: URIRef
    subject_types: list[URIRef]


class GraphEntity:

    __find_url_regex = re.compile(
        r"^https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=]*)$"
    )

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
            self.entity_store = {}

        if isinstance(uri, URIRef):
            self.uri = uri
            self.identifier = uri
            self.type = GraphEntity.__entity_types.object
            self._setup_uriref()
            self.property_list = []
        elif isinstance(uri, Literal):
            self.literal = uri
            self.identifier = uri
            self.type = GraphEntity.__entity_types.literal
            self._setup_literal()

        self.got_neighbours = False
        self.outgoing_linked_neighbours = []
        self.incoming_linked_neighbours = []

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
            # This makes the assumption that literal data points
            # do not carry any linked_entities
            pass

        link_pointers = {o for _, olist in link_paths for o in olist}
        link_objects_dict = {}

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
            obj = self.uri
        elif self.type == "literal":
            obj = self.literal
        else:
            raise TypeError("Object is of type: {self.type}")

        for p in predicate_list:
            link_paths.append(
                (p, list(self.graph.subjects(object=obj, predicate=p, unique=True)))
            )

        link_pointers = set([s for _, slist in link_paths for s in slist])
        link_objects_dict = {}

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
        """Where the entity has been identified as being a Literal,
        capture appropriate dataclass values"""
        value = self.literal.toPython()

        url_match = False
        if isinstance(value, str):
            url_match = GraphEntity.__find_url_regex.match(escape(value.strip()))
            if url_match is not None:
                url_match = True
            else:
                url_match = False

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
            is_possible_url=url_match,
        )

    def _setup_uriref(self):
        """Where the entity has been identified as an Object (URIRef),
        capture appropriate dataclass values"""
        # Careful to ensure that types and labels are aligned in terms
        # of their ordering, to ensure the right type<-->labels can be
        # recovered
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
            is_possible_url=True
        )

    def get_neighbours(self):
        """Populate the incoming and outgoing linked neighbours with
        tuples consisting of (<predicate>, <object>), while updating
        the underlying entity_store to contain all entities extracted
        from the graph in the process"""

        self.get_outgoing_linked_entity_data()
        outgoing_linked_neighbours = []
        property_list = []

        for p in self.data.outgoing_predicates:
            for o in self._get_objects(self.uri, p):
                fetched_predicate_entity = GraphEntity(self.graph, p, self.entity_store)
                fetched_object_entity = GraphEntity(self.graph, o, self.entity_store)
                outgoing_linked_neighbours.append(
                    (
                        fetched_predicate_entity,
                        fetched_object_entity,
                    )
                )

                if fetched_object_entity.type=='literal':
                    property_list.append(
                        (
                            fetched_predicate_entity.data.subject_h_label,
                            fetched_object_entity.data.value
                        )
                    )
                
        self.outgoing_linked_neighbours = outgoing_linked_neighbours
        self.property_list = property_list

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

    def _get_object_predicates(self, obj: Identifier) -> set[URIRef]:
        return set(
            [p for p in self.graph.predicates(subject=None, object=obj)]
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

        if len(types) == 0:
            if (
                len(
                    list(
                        self.graph.subjects(predicate=RDF.type, object=self.identifier)
                    )
                )
                > 0
            ):
                types.add(RDFS.Class)
        return types

    def _get_objects(self, subject: URIRef, predicate: URIRef) -> set[URIRef]:
        predicate_objects = set()
        for o in self.graph.objects(subject=subject, predicate=predicate):
            predicate_objects.add(o)
        return predicate_objects

    def _get_subjects(self, obj: Identifier, predicate: URIRef) -> set[URIRef]:
        predicate_subjects = set()
        for s in self.graph.subjects(object=obj, predicate=predicate):
            predicate_subjects.add(s)
        return predicate_subjects

    def _get_result_from_preference_list(
        self, subject: URIRef, preferences: list[URIRef]
    ) -> Node:
        for p in preferences:
            fetch_lits = [o for o in self.graph.objects(subject=subject, predicate=p)]
            if len(fetch_lits) > 0:
                return fetch_lits[0]

        # Nothing found, convert the object's URIRef into a stringlike value
        # and serve as a Literal
        # (Ideally shortened depending on the namespace_manager associated
        # with the graph)
        return Literal(subject.n3(self.graph.namespace_manager))

    def html_components(self, configuration):

        components={}

        href_entity_lambda = (
            lambda x: f"""<a href="{x.uri}" title="{escape(x.data.subject_t_label)}" target="_blank">{escape(x.data.subject_h_label)}</a>"""
        )

        href_literal_lambda = lambda x: (
                f'<a href="{escape(x.literal.toPython())}">{escape(x.literal.toPython())}</a>'
                if x.data.is_possible_url
                else f"{escape(x.literal.toPython())}"
            )
        if self.type == "object":

            # Define title_stub
            subject_types_string = ",".join(
                [
                    f"""<a href="{st.toPython()}">{escape(sl)}</a>"""
                    for st, sl in zip(
                        self.data.subject_types, self.data.subject_type_labels
                    )
                ]
            )
            html_title_stub = f""" <h1>{href_entity_lambda(self)} | {subject_types_string} <h1> """
            components['title']=html_title_stub
            # Define Literal Property Table
            
            property_rows_string = "".join(
                [
                    f"""<tr><td>{href_entity_lambda(p)}</td><td>{href_literal_lambda(o)}</td></tr>"""
                    for p, o in sorted(
                        self.outgoing_linked_neighbours,
                        key=lambda x: x[0].data.subject_h_label,
                    )
                    if o.type == "literal"
                ]
            )
            if len(property_rows_string) > 0:
                html_property_panel_stub = f"""<table><caption>Properties</caption><tr><th>Property</th><th>Value</th></tr>
                {property_rows_string}
                </table>"""
            else:
                html_property_panel_stub = ""
            components['property_table']=html_property_panel_stub
            # Define Incoming and Outgoing Object Links

 
            outbound_links_string = "".join(
                [
                    f"""<tr><td>{href_entity_lambda(p)}</td><td>{href_entity_lambda(o)}</td></tr>"""
                    for p, o in sorted(
                        self.outgoing_linked_neighbours,
                        key=lambda x: x[0].data.subject_h_label,
                    )
                    if o.type == "object"
                ]
            )
            if len(outbound_links_string) > 0:
                html_outbound_links_panel_stub = f"""<table><caption>Outgoing Links</caption><tr><th>Property</th><th>Value</th></tr>
                {outbound_links_string}
                </table>"""
            else:
                html_outbound_links_panel_stub = ""
            components['outbound_links']=html_outbound_links_panel_stub
            inbound_links_string = "".join(
                [
                    f"""<tr><td>{href_entity_lambda(p)}</td><td>{href_entity_lambda(o)}</td></tr>"""
                    for p, o in sorted(
                        self.incoming_linked_neighbours,
                        key=lambda x: x[0].data.subject_h_label,
                    )
                    if o.type == "object"
                ]
            )
            if len(inbound_links_string) > 0:
                html_inbound_links_panel_stub = f"""<table><caption>Incoming Links</caption><tr><th>Property</th><th>Value</th></tr>
                {inbound_links_string}
                </table>"""
            else:
                html_inbound_links_panel_stub = ""
            components['inbound_links']=html_inbound_links_panel_stub
        return components


# Collection of base methods for generating triples given various
# input combinations
def create_triples_from_slist_p_o(
    subjects: list[URIRef], 
    predicate: URIRef, 
    obj: RDFObjectAtom
) -> set[RDFTriple]:
    """With a list of subjects, and a fixed predicate/object combination,
    generate a set of RDFTriples"""
    triples = set()
    for s in subjects:
        triples.add((s, predicate, obj))
    return triples


class RDFExplorer:
    """A utility class for extracting content from an rdflib graph object
    After initial setup, various methods exist for generating lists of
    objects, perhaps selecting by type, or as the result of a query.
    These lists of object identifiers (URIs) are used to drive extracts
    of subject-centric graph reports"""

    def __init__(
        self,
        rdf_g: rdflibGraph,
        entity_store: dict[Identifier, "GraphEntity"] | None = None,
    ) -> None:
        """An object wrapper used to extract data from the graph and
        expose it as a set of type-centric python-dicts"""
        self.graph = rdf_g
        self.populate_link_store()
        if entity_store is None:
            self.entity_store = {}
        else:
            self.entity_store = entity_store

    def populate_link_store(self):
        """extract all the triples linking entities and
        prepare data packets for each unique s,p,o combination"""
        self.link_store={}
        for e,t in enumerate(self.graph.triples((None, None, None))):
            s,p,o = t
            if isinstance(s,URIRef) and isinstance(p,URIRef) and isinstance(o,URIRef):
                edge_data = EdgeData(
                    subject = s, 
                    predicate = p, 
                    object = o,
                    predicate_label=p.n3(self.graph.namespace_manager)
                )
                self.link_store[e]=edge_data


    def gen_entity_report_dict_for_types(
        self, types: list[URIRef]
    ) -> dict[URIRef, GraphEntity]:
        entities = []
        for t in types:
            entities.extend(self._get_subjs_by_type(t))

        return self.gen_entity_report_dict(entities)

    def get_entity_details(self, subject: URIRef) -> GraphEntity:
        entity = GraphEntity(self.graph, subject, self.entity_store)
        return entity

    def gen_entity_report_dict(
        self, subjects: list[URIRef]
    ) -> dict[URIRef, GraphEntity]:
        """Generate a collection of entity details based on the list
        of subjects provided in the parameters.
        Note that a side-effect of the fetch process updates the
        self.entity_store object which serves as an index/memory
        cache. If the object has already been fetched previously,
        the detail will be returned from there.
        What we're essentially doing here is building an in-memory,
        indexed cache of selected data items that can be interrogated
        independently of the original graph.
        """

        sdict = {}
        for subject in subjects:
            sdict[subject] = self.get_subject_and_neighbours(subject)
        return sdict

    def get_subject_and_neighbours(self, subject: URIRef):
        entity = self.get_entity_details(subject)
        entity.get_neighbours()
        self.entity_store[entity.identifier] = entity
        return entity

    def _get_subjs_by_type(self, type_uri: URIRef) -> set[Identifier]:
        subj_uris = set(
            [s for s, _, _ in list(self.graph.triples((None, RDF.type, type_uri)))]
        )
        return subj_uris  # pyright: ignore[reportReturnType]

    def _get_all_types_in_graph(self) -> set[URIRef]:
        type_uris = set(
            [
                o
                for _, _, o in list(self.graph.triples((None, RDF.type, None)))
                if isinstance(o, URIRef)
            ]
        )
        return type_uris

    def gen_index(self, data_attribute):
        """Create an unsorted index from data_attribute (as key) to
        a set of references on self.entity_store keys"""
        index = {}
        for k, v in self.entity_store.items():
            if hasattr(v.data, data_attribute):
                data = getattr(v.data, data_attribute)
            elif hasattr(v, data_attribute):
                data = getattr(v, data_attribute)
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

    def to_gravis_nx(self):
        nx_g = nx.MultiDiGraph()

        for node, entity in self.entity_store.items():
            
            # Filter out nodes that are objects (exclude literals)
            if entity.type=='object':
                print(entity.property_list)
                html_components = entity.html_components(configuration={})
                html_stuff = ""
                for k, content in html_components.items():
                    html_stuff = html_stuff + content
                try:
                    nx_g.add_node(node, 
                                label=entity.data.subject_h_label, 
                                click=html_stuff, 
                                hover=html_components['title'],
                                rdfclass=entity.data.subject_type_labels[0],
                                property_list=entity.property_list
                                )
                except Exception as e:
                    print(entity, e)
                    
        for edge_id, edge in self.link_store.items():
            if edge.predicate != RDF.type:
                try:
                    nx_g.add_edge(edge.subject,
                                edge.object,
                                label=edge.predicate_label, 
                                uri=edge.predicate,
                                rdfclass=edge.predicate.n3(self.graph.namespace_manager)
                                )

                except Exception as e:
                    print(edge, e)

        return nx_g
        
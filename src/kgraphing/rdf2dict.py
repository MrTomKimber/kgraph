"""Utility for converting rdflib graphs into dictionary
representations, and (at some point in the future) back again."""

from typing import Optional, Self
from dataclasses import dataclass, asdict, field
import json
import uuid
import os
from itertools import combinations

from xml.etree import ElementTree as ET
from urllib.parse import urldefrag
from rdflib import Graph, Literal, URIRef, BNode
from rdflib.term import Identifier, Node
from rdflib.namespace import RDF, RDFS
from rdflib.parser import Parser
from rdflib.plugin import register, PluginException
from rdflib.exceptions import ParserError
from urllib.error import HTTPError, URLError
from send2trash import send2trash

from rdflibowlparser import owlxml

register(
    "owl",  # Format string to use in parse()
    Parser,
    "rdflibowlparser.owlxml",
    "OWLXMLParser",
)


def venn_partitions(sets: dict[str, set], notation_style: str):
    if notation_style is None:
        notation_style = "strict"
    else:
        assert notation_style in ["strict", "loose", "binindex"]
    psize = len(sets)
    set_labels = list(sets.keys())
    set_contents = list(sets.values())
    set_indices = set(range(0, len(sets)))
    n = len(sets)
    partition_d = {}
    for k in range(1, n + 1):
        for combo in combinations(range(n), k):
            in_sets = set(combo)
            out_sets = set_indices - in_sets
            if notation_style == "strict":
                notation = f"{" ∩ ".join([set_labels[s] for s in in_sets])}"
                if len(out_sets) != 0:
                    notation = (
                        notation
                        + f" ∩ {" ∩ ".join([f"{set_labels[s]}ᶜ" for s in out_sets])}"
                    )
            elif notation_style == "loose":
                notation = f"{{{",".join([set_labels[s] for s in in_sets])}}}"
            #               notation = frozenset([set_labels[s] for s in in_sets])
            else:
                notation = frozenset([set_labels[s] for s in in_sets])
            in_elements = set.intersection(*[set_contents[i] for i in in_sets])
            out_elements = set.union(*[set_contents[i] for i in out_sets] + [set()])
            contents = in_elements - out_elements
            if contents != set():
                partition_d[notation] = contents
    return partition_d


class OntologyCache:
    registry: dict[str, str]

    def __init__(self, cache_directory: str):
        self.cache_directory = cache_directory
        if not os.path.isdir(cache_directory):
            os.makedirs(cache_directory)
        self.registry = dict()
        ocache_json_filename = os.path.join(cache_directory, "ocache.json")
        self.cache_json = ocache_json_filename
        if os.path.isfile(self.cache_json):
            self.read_init()
        else:
            self.commit()

    def cleanup(self):
        """Remove all content from the cache that's not present in the registry
        Actions taken:
            keys with no associated file (missing list) are deleted from the registry
            orphan files with no registry key are deleted from the cache"""
        valid, missing, orphan = self.cross_check_registry_cache()
        pre_clean_registry_items = self.registry.copy().items()
        for m in missing:
            for k, v in pre_clean_registry_items:
                if v == m:
                    del self.registry[k]

        for o in orphan:
            send2trash(os.path.join(self.cache_directory, o))
        self.commit()

    def purge(self):
        """Completely wipe any content from the cache and reset it to clean state"""
        self.registry = {}
        self.commit()
        self.cleanup()

    def read_init(self):
        """Load the contents of the cache registry file into memory"""
        with open(self.cache_json, "r") as ocache_json_file:
            self.registry = json.load(ocache_json_file)

    def commit(self):
        with open(self.cache_json, "w") as ocache_json_file:
            json.dump(self.registry, ocache_json_file, indent=4)

    def cross_check_registry_cache(self):
        """Check integrity of registry and files
        outputs a tuple containing (valid, missing, orphan) where:
            valid is a list of valid files in the cache, for which the registry has keys
            missing is a list of keys in the registry for which there is no matching file in the cache
            orphan is a list of files in the cache for which there are no registry keys
        """
        cache_files = set()
        cache_registry_entries = set(self.registry.values())
        files = [
            f
            for f in os.listdir(self.cache_directory)
            if os.path.isfile(os.path.join(self.cache_directory, f))
        ]
        for f in files:
            if f != "ocache.json":
                cache_files.add(f)
        valid_values = cache_registry_entries.intersection(cache_files)
        unresolved_registry_entries = cache_registry_entries - cache_files
        orphan_cache_files = cache_files - cache_registry_entries
        return valid_values, unresolved_registry_entries, orphan_cache_files

    def register_ontologies(
        self, ontology_urls: dict[str, str], overwrite: bool = False
    ):
        for k, v in ontology_urls.items():
            self.register(ontology_url=k, overwrite=overwrite, alias=v)

    def register(
        self,
        ontology_url: str,
        overwrite: bool = False,
        alias: Optional[str] = None,
    ):
        o_graph = Graph()
        if alias is not None:
            ontology_location = alias
        else:
            ontology_location = ontology_url
        if overwrite or ontology_url not in self.registry:
            try:
                o_graph.parse(ontology_location)

                if overwrite and ontology_url in self.registry:
                    serial_filename = self.registry[ontology_url]
                else:
                    serial_filename = f"{uuid.uuid4().hex.upper()[:8]}.owl"
                serial_path = os.path.join(self.cache_directory, serial_filename)
                o_graph.serialize(serial_path, format="xml")
                self.registry[ontology_url] = serial_filename
                self.commit()
            except HTTPError as e:
                print(f"HTTPError found when processing {ontology_url}: {e}")
            except URLError as e:
                print(f"URLError found when processing {ontology_url}: {e}")
            except ParserError as e:
                print(
                    f"Parser error encountered while processing {ontology_url} - consider manually registering an alias"
                )
            except PluginException as e:
                print(
                    f"{e} encountered while processing {ontology_url} - consider manually registering an alias"
                )
            except Exception as e:
                raise e
                print(
                    f"Unable to register {ontology_url} (@{ontology_location}) due to {e}"
                )
        else:
            print(f"{ontology_url} already present in registry")


@dataclass(kw_only=True)
class Thing:
    identifier: Node
    full_name: Optional[str] = None
    short_name: Optional[str] = None

    def to_dict(self):
        return asdict(self)


@dataclass(kw_only=True)
class ObservedRelationClass(Thing):
    """The ObservedRelationClass class collates information about
    how a Relation is used within a given context (graph).
    This can be compared against expected usage for validation
    but is also referenced when unpacking contents from
    one representation to another."""

    _observed_rdf_subject_terms: set[type[Identifier]] = field(default_factory=set)
    _observed_rdf_object_terms: set[type[Identifier]] = field(default_factory=set)
    _observed_rdf_subject_classes: set[Identifier] = field(default_factory=set)
    _observed_rdf_object_classes: set[Identifier] = field(default_factory=set)
    _observed__count: int = 0
    order: int

    def to_dict(self):
        return super().to_dict()


@dataclass(kw_only=True)
class ObservedEntity(Thing):
    """The ObservedEntity class collates information about
    entities observed within a given context and stores
    meta-data collected about them.
    It will have a wider scope than the raw-graph-dict, in
    that non-subject entities (objects and literals)
    will be identified here, while only subjects are keyed in
    the graph_dict
    """

    _observed_rdf_terms: set[type[Identifier]] = field(default_factory=set)
    _observed_rdf_classes: set[URIRef] = field(default_factory=set)
    _observed_outgoing_relations: set[URIRef] = field(default_factory=set)
    _observed_incoming_relations: set[URIRef] = field(default_factory=set)
    interactions: dict[URIRef, Identifier] = field(default_factory=dict)
    order: int

    @property
    def term(self):
        if len(self._observed_rdf_terms) == 1:
            [_term] = self._observed_rdf_terms
        elif len(self._observed_rdf_terms) > 1:
            assert False
        else:  # len(self._observed_rdf_terms)==0
            _term = None

        return _term

    def to_dict(self):
        return {**super().to_dict(), **{"term": self.term}}

    def to_html(self):
        rows = []
        for k, v_set in self.interactions.items():
            for e, v in enumerate(v_set):
                if e == 0:
                    rows.append(f"""<tr>
                                    <td rowspan="{len(v_set)}">{str(k)}</td>
                                    <td> {str(v)} </td>
                                </tr>
                                """)
                else:
                    rows.append(f"""<tr>
                                    <td> {str(v)} </td>
                                </tr>
                                """)

        return f"""<table>{"".join(rows)}</table>"""


class RDF2dict:


    def __init__(self, g: Graph, cache: OntologyCache):
        self.source_graph=RDF2dict.copy_graph(g) # Store a copy of the original graph used to instantiate the object
        self.relations = (
            {}
        )  # A dictionary keyed on predicates - provides graph-level meta-data over the observed usage of the predicate
        self.entities = (
            {}
        )  # A dictionary keyed on subject - this differs from the raw_graph_dict in that it collects observations across the graph
        # It might be worth stripping this out later, I'm not 100% convinced this is doing anything meaningful that the raw_graph_dict isn't
        self.ontology_cache = cache
        self.update(g, order=0)

    @classmethod
    def from_file(cls, file_path : str, cache : OntologyCache)->Self:
        declared_namespaces = RDF2dict.get_xml_namespaces(file_path)
        print(f"Declared Namespaces={declared_namespaces}")
        g = Graph()
        g.parse(file_path)
        # Find the URI of the default namespace
        try:
            default_uri = next(uri for prefix, uri in g.namespaces() if prefix == "")
            print(f"Default uri={default_uri}")
            # Find the named prefix (e.g., 'kgmod') that maps to the same URI as the default
            preferred_prefix = next((prefix for prefix, uri in declared_namespaces.items() if str(uri) == str(default_uri) and prefix != ""), None)
            print(f"Preferred Prefix={preferred_prefix}")
            # Rebind the namespace to use the named prefix
            if preferred_prefix:
                g.bind(preferred_prefix, default_uri, replace=True)

        except StopIteration:
            # There is no default uri
            pass
        return cls(g, cache)
    
    @staticmethod
    def copy_graph(original_graph):
        copy_graph = Graph(
            store=original_graph.store,
            identifier=original_graph.identifier,
            namespace_manager=original_graph.namespace_manager
            )
        for triple in original_graph:
            copy_graph.add(triple)
        return copy_graph

    @staticmethod
    def get_xml_namespaces(file_path):
        with open(file_path, 'r') as file:
            context = ET.iterparse(file, events=['start-ns'])
            # Convert list of (prefix, uri) tuples to a dictionary
            return dict([item for action, item in context])

    @staticmethod
    def get_base_uri(uri_str: str):
        # urldefrag separates the URI into (root, fragment)
        root, fragment = urldefrag(uri_str)
        # If there is a fragment, the namespace is the root + '#'
        if fragment:
            return root + "#"
        # Otherwise, the namespace is the URI up to the last '/'
        return uri_str.rsplit("/", 1)[0] + "/"

    def _get_relationship_definitions(self):
        return set([v.identifier for v in self.relations.values()])

    def _get_class_definitions(self):
        return set([c for e in self.entities.values() for c in e._observed_rdf_classes])

    def _infer_ontology_list(self):
        # Assuming types and predicates are referenced from some
        # canonical ontology, go over these objects and return a
        # list of possible candidate ontologies.
        relations = self._get_relationship_definitions()
        types = self._get_class_definitions()
        candidate_ontology_set = set(
            [RDF2dict.get_base_uri(c) for c in relations.union(types)]
        )
        return candidate_ontology_set

    def _update_entities_relations_from_triple(self, triple, order: int):
        s, p, o = triple
        # Process the subject - s
        if s in self.entities:
            if p in self.entities[s].interactions:

                if o not in self.entities[s].interactions[p]:
                    self.entities[s].interactions[p].add(o)
                else:
                    self.entities[s].interactions[p] = set()
                    self.entities[s].interactions[p].add(o)
            else:
                self.entities[s].interactions[p] = set()
                self.entities[s].interactions[p].add(o)
            self.entities[s]._observed_outgoing_relations.add(p)
            self.entities[s]._observed_rdf_terms.add(type(s))
        else:
            s_ent = ObservedEntity(identifier=s, order=order)
            self.entities[s] = s_ent
            self.entities[s]._observed_outgoing_relations.add(p)
            self.entities[s]._observed_rdf_terms.add(type(s))
            self.entities[s].interactions[p] = set()
            self.entities[s].interactions[p].add(o)

        # Process the object - o

        if o not in self.entities:
            o_ent = ObservedEntity(identifier=o, order=order)
            self.entities[o] = o_ent

        if p == RDF.type:
            #            self.entities[o]._observed_rdf_classes.add(RDFS.Class)
            #            self.entities[o]._observed_rdf_terms.add(type(RDFS.Class))
            self.entities[s]._observed_rdf_classes.add(o)

        if isinstance(o, Literal):
            self.entities[o]._observed_rdf_classes.add(RDFS.Literal)
            self.entities[o]._observed_rdf_terms.add(type(o))
        elif isinstance(o, (URIRef, BNode)):
            self.entities[o]._observed_rdf_terms.add(type(o))

        self.entities[o]._observed_incoming_relations.add(p)

        # Process the predicate - p
        if p in self.relations:
            if type(o) not in self.relations[p]._observed_rdf_object_terms:
                self.relations[p]._observed_rdf_subject_terms.add(type(s))
                self.relations[p]._observed_rdf_object_terms.add(type(o))
            else:
                o_rel = self.relations[p]
                self.relations[p]._observed_rdf_subject_terms.add(type(s))
                self.relations[p]._observed_rdf_object_terms.add(type(o))
        else:
            o_rel = ObservedRelationClass(identifier=p, order=order)
            self.relations[p] = o_rel
            self.relations[p]._observed_rdf_subject_terms.add(type(s))
            self.relations[p]._observed_rdf_object_terms.add(type(o))

        self.relations[p]._observed__count = self.relations[p]._observed__count + 1

    def _enrich_entities_relations_from_global(self):
        # After populating the full entities/relations information, make use
        # of the lookups to add final cross-referencing observations at
        # entity and relation level
        for identifier, entity in self.entities.items():
            entity_relations_d = self.entities[identifier].interactions
            if not isinstance(identifier, Literal):
                if RDF.type in entity_relations_d:
                    self.entities[identifier]._observed_rdf_classes = (
                        entity._observed_rdf_classes.union(entity_relations_d[RDF.type])
                    )
            for relation, obj_set in entity_relations_d.items():
                self.relations[relation]._observed_rdf_subject_classes = self.relations[
                    relation
                ]._observed_rdf_subject_classes.union(entity._observed_rdf_classes)
                for obj_pointer in obj_set:
                    obj = self.entities[obj_pointer]
                    self.relations[relation]._observed_rdf_object_classes = (
                        self.relations[relation]._observed_rdf_object_classes.union(
                            obj._observed_rdf_classes
                        )
                    )


    def update_cache(self):
        cache_ontologies = set(self.ontology_cache.registry)
        start_ontology_count = len(cache_ontologies)
        inferred_required_ontologies = self._infer_ontology_list()
        # Simple placeholder - any standing aliases to be worked into the below dictionary construction
        cache_update_ontologies = {
            k: k for k in inferred_required_ontologies - cache_ontologies
        }
        self.ontology_cache.register_ontologies(cache_update_ontologies)
        end_ontology_count = len(set(self.ontology_cache.registry))
        o_diff = end_ontology_count - start_ontology_count
        if o_diff > 0:
            print(f"Added {o_diff} new ontologies")
        else:
            print("No new ontologies added.")

    def create_ontology_graph(self):
        o_graph = Graph()
        for o in self._infer_ontology_list():
            o_file = self.ontology_cache.registry.get(o)
            if o_file is not None:
                o_graph.parse(os.path.join(self.ontology_cache.cache_directory, o_file))
        return o_graph

    def get_entities_pending_metadata(self):
        all_classes = self._get_class_definitions()
        all_relationships = self._get_relationship_definitions()
        undef_relationships = all_relationships - set(self.entities)
        undef_classes = all_classes - set(
            [k for k, v in self.entities.items() if v.interactions != {}]
        )
        entities_pending_metadata = undef_relationships.union(undef_classes)
        return entities_pending_metadata

    def _enrich_metadata_for_entities(
        self, entity_list: set[URIRef], o_graph: Graph, order
    ):
        triple_count = 0
        for obj in entity_list:
            onto_triples = o_graph.triples((obj, None, None))
            for triple in onto_triples:
                self._update_entities_relations_from_triple(triple, order=order)
                triple_count = triple_count + 1
        if triple_count != 1:
            plural = "s"
        else:
            plural = ""
        print(f"Processed {triple_count} triple{plural}.")

    def enrich_metadata(self):
        delta = -1
        n = 0
        ents_pending_metadata = self.get_entities_pending_metadata()
        start_count = len(ents_pending_metadata)
        while delta != 0:
            n = n + 1
            print(f"Round {n}...")
            self.update_cache()
            o_graph = self.create_ontology_graph()
            self._enrich_metadata_for_entities(ents_pending_metadata, o_graph, order=n)
            ents_pending_metadata = self.get_entities_pending_metadata()
            delta = len(ents_pending_metadata) - start_count
            start_count = len(ents_pending_metadata)

    def update(self, g: Graph, order: int):

        # Populate information into the raw_graph_dict/relations/entities dictionaries
        for triple in g:
            self._update_entities_relations_from_triple(triple, order)
        self._enrich_entities_relations_from_global()

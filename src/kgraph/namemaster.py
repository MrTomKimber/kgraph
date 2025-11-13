from sqlitedict import SqliteDict
from rdflib import Namespace, URIRef, Literal
import rdflib
from datetime import datetime
from kgraph.declarations import KGMETA

class NameMaster:
    """Simple class for providing a data-mastering service using SqliteDict."""

    def __init__(self, db_path=":memory:", table="master", autocommit=False):
        # Start the database and return the number of items in it
        self.db = SqliteDict(db_path, tablename="master", autocommit=autocommit)

    def close(self):
        self.db.close()

    def __len__(self):
        """Return the number of items in the database."""
        return len(self.db)

    def __contains__(self, key):
        """Check if a key exists in the database."""
        return key in self.db

    def get_value(self, key):
        """Retrieve a value by key."""
        return self.db.get(key, None)

    def set_value(self, key, value):
        """Set a value for a key."""
        self.db[key] = value

    def delete_value(self, key):
        """Delete a key-value pair."""
        if key in self.db:
            del self.db[key]

    def exists(self, key):
        """Check if a key exists."""
        return key in self.db

    def clear(self):
        """Clear the database."""
        self.db.clear()

    def commit(self):
        """Commit changes to the database."""
        self.db.commit()

    def rollback(self):
        """Rollback changes in the database."""
        self.db.rollback()

    def set_values(self, items, safe=False):
        """Set multiple key-value pairs."""
        report = [0, 0, 0]  # [added, updated, skipped]
        for key, value in items.items():
            if key in self.db:
                if value != self.db[key]:
                    if not safe:
                        self.db[key] = value
                        report[1] += 1  # Updated
                    else:
                        print(
                            f"Key {key} already exists with value {self.db[key]}, not overwriting."
                        )
                        report[2] += 1  # Skipped
                else:
                    pass  # Value is the same, no action needed
                    report[2] += 1  # Skipped
            else:
                self.db[key] = value
                report[0] += 1  # Added
        self.commit()
        return report

    def test_keyvalue_against_master(self, key, value):
        """Given a key, value pair, test if the key is already in the database.
        If it is, return the value from the database.
        Return a tuple (diffclue, mastered_value) where diffclue is True if the value was altered
        """

        diffclue = False
        mastered_value = None

        if key in self.db:
            mastered_value = self.get_value(key)
        else:
            mastered_value = value
        diffclue = mastered_value != value
        return diffclue, mastered_value

    def return_altered_values_from_dict(self, dictionary):
        """Remaster a dictionary by checking each key-value pair, returning
        a new dictionary with key/value pairs that were remastered."""
        print(f"return_altered_values_from_dict:start {datetime.now()}")
        remastered = {}
        for key, value in dictionary.items():
            diffclue, mastered_value = self.test_keyvalue_against_master(key, value)
            if diffclue:
                remastered[key] = mastered_value
        print(f"return_altered_values_from_dict:end {datetime.now()}")
        return remastered

    def fully_qualified_names_from_graph(self, graph):
        """Given an rdflib graph, find all named entities and return a dictionary
        describing those whose URIs require updating to conform to the
        master database."""
        print(f"fully_qualified_names_from_graph:start {datetime.now()}")
        keyvalue_pairs = {}

        # Cycle over all the named entities in the graph
        for s, p, o in graph.triples((None, KGMETA.FullyQualifiedName, None)):
            subject = s  # By convention, store entity references as raw URIRefs
            if isinstance(o, URIRef):
                object = o.n3()
                assert False, "FullyQualifiedName {object} should not be a URIRef"
            elif isinstance(o, Literal):
                object = o.toPython()
            if object in keyvalue_pairs:
                assert (
                    False
                ), "FullyQualifiedName found in graph pointing to multiple objects"

            keyvalue_pairs[object] = subject
        print(f"fully_qualified_names_from_graph:end {datetime.now()}")
        return keyvalue_pairs

    def master_spec_from_rdflib_graph(self, graph):
        """Given an rdflib graph, find all named entities and return a dictionary
        describing those whose URIs require updating to conform to the
        master database."""
        keyvalue_pairs = self.fully_qualified_names_from_graph(graph)
        diff_spec = self.return_altered_values_from_dict(keyvalue_pairs)
        remaster_transform = {}
        for key, value in keyvalue_pairs.items():
            remaster_transform[value] = diff_spec.get(key, value)
        return remaster_transform

    def remaster_graph(self, graph):
        """Given an rdflib graph, remaster the URIs of named entities
        according to the master database."""
        remastered_graph = rdflib.Graph()
        for ns_prefix, namespace in graph.namespaces():
            remastered_graph.bind(ns_prefix, namespace)

        master_spec = self.master_spec_from_rdflib_graph(graph)
        print(f"{len(master_spec)} named entities to remaster in the graph.")
        # Cycle over all the named entities in the graph and update their URIs
        for s, p, o in graph.triples((None, None, None)):
            ms, mp, mo = (
                master_spec.get(s, s),
                master_spec.get(p, p),
                master_spec.get(o, o),
            )
            remastered_graph.add((ms, mp, mo))

        return remastered_graph

    def master_graph(self, graph):
        print(f"master_graph:start {datetime.now()}")
        remastered_graph = self.remaster_graph(graph)

        key_values_to_master = self.fully_qualified_names_from_graph(
            remastered_graph
        )
        update_report = self.set_values(key_values_to_master, safe=True)
        if update_report[0] > 0:
            print(
                f"Mastered {update_report[0]} new values, updated {update_report[1]} existing values, skipped {update_report[2]} existing values."
            )
        else:
            print(
                f"No new values mastered, updated {update_report[1]} existing values, skipped {update_report[2]} existing values."
            )
        print(f"master_graph:end {datetime.now()}")
        return remastered_graph

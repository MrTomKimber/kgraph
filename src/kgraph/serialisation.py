from declarations import RDFTriple
import json
import jsonschema 
from importlib import resources
import urllib.parse
from rdflib import Graph as rdflibGraph, Namespace, URIRef, BNode, Literal
from rdflib.namespace import RDF, RDFS, OWL, SH
import pandas as pd
import uuid
import numpy as np
import re
from hashlib import md5
from itertools import product

from datetime import datetime


s_jsonschema = resources.read_text(__name__, "jschema/serialisationschema.json")

def split_on_comma_respecting_quotes(some_string):
    quote_respecter = re.compile(r"(?<!\\)(\".+?(?<!\\)\")")
    in_d = dict()
    text = "".join([c for c in some_string])
    fms = quote_respecter.findall(text)
    for m in fms:
        key=uuid.uuid4().hex
        in_d[key]=m
        text=text.replace(m, key)
    values=[]
    for value in text.split(","):
        if any([k in value for k in in_d.keys()]):
            for k,v in in_d.items():
                if k in value:
                    values.append(value.replace(k,v).strip())
        else:
            values.append(value.strip())
    return values

class Serialisation(object):
    
    schema = json.loads(s_jsonschema)
    # Assign the namespace "DATA" to be used for temporary in-memory raw data graph
    DATA = Namespace("http://data#")
    def __init__(self, serialisation_config):
        """Read in a configuration file, validate it and generate a 
           well-populated Serialisation object"""
        self.config = json.load(open(serialisation_config, "r"))
        try:
            jsonschema.validate(self.config, schema=Serialisation.schema)
        except jsonschema.exceptions.ValidationError as err:
            print(err)
        
        # Note that this forces any NamedObject Instances to mirror their associated SubjectTag column-names
        # A discrepancy between these two would cause the lineage to break.
        self.specifications=dict()
        self.fully_qualified_names_tree=dict()
        self.glob_vars = dict()
        for varname, varvalue in self.config['GlobalVariables'].items():
            self.glob_vars[varname]=varvalue

        for named_object_definition in self.config['NamedObjects']:
            for instance in named_object_definition['Instances']:
                iname=instance.get("InstanceName")
                targetclass = named_object_definition.get("TargetClass")
                classbase = URIRef(named_object_definition['URIBase'])
                named_instance = NamedObjectInstanceSpecification(self, targetclass, classbase, instance)
                self.specifications[iname]=named_instance
                if named_instance._subject__column not in self.fully_qualified_names_tree.keys():
                    self.fully_qualified_names_tree[named_instance._subject__column]=named_instance._parent__column


        for relationship_definition in self.config['Relationships']:
            for instance in relationship_definition['Instances']:
                iname=instance.get("InstanceName")
                targetclass = relationship_definition.get("Predicate")
                relation_instance = RelationshipInstanceSpecification(self, targetclass, instance)
                self.specifications[iname]=relation_instance


        for property_definition in self.config['Properties']:
            for instance in property_definition['Instances']:
                iname=instance.get("InstanceName")
                targetclass = property_definition.get("Predicate")
                property_instance = PropertyInstanceSpecification(self, targetclass, instance)
                self.specifications[iname]=property_instance

        
        # Update the list of object instances with the naming_hierarchy_path used later to establish its FQN
        referenced_columns = []
        for iname, instance_object in self.specifications.items():
            if isinstance(instance_object, NamedObjectInstanceSpecification):
                instance_object.populate_naming_hierarchy_path()
            referenced_columns.extend(instance_object.column_list)

        self.referenced_columns=list(set(referenced_columns))
        multivalue_columns=[]
        for c in self.referenced_columns:
            for instance in self.specifications.values():
                if c == instance._expose_multi_value_field():
                    multivalue_columns.append(c)
        self.multivalue_columns=list(set(multivalue_columns))
    
    def _filter_specifications_on_subject_column(self, column):
        c_specs = [s for k,s in self.specifications.items() if isinstance(s, NamedObjectInstanceSpecification) and s._subject__column==column]
        return c_specs

    def _traverse_hierarchy_path(self, start, acc=None):
        # Given a dictionary containing node-to-node parental linkages {child:parent} and a start node,
        # traverse the hierarchy and return the path taken from start node, all the way up the 
        # tree, until it reaches the (local) top.
        if acc is None:
            acc = [start]
        next_value = self.fully_qualified_names_tree.get(start)
        if next_value is not None :
            acc.append(next_value)
            self._traverse_hierarchy_path(next_value, acc)
        return acc
    
    def populate_entity_fqn_index(self, raw_graph):
        # Create set of entities from the raw graph
        entities=[]
        entity_fqn_index=dict()
        for datarow in [r[0] for r in raw_graph.triples((None, RDF.type, Serialisation.DATA['row']))]:
            for s in [s for s in self.specifications.values() if isinstance(s, NamedObjectInstanceSpecification)]:
                #print("\t", s._instance_name)
                #print("\t", s.column_list)
                #print("\t subcol:", s._subject__column)
                #print("\t parcol:", s._parent__column)
                #print("\t muvals:", s._multivalues)
                for newobj in s.NamedObjectListFromDataGraphRow(datarow, raw_graph):
                    if newobj.fully_qualified_name not in entity_fqn_index.keys():
                        entities.append(newobj)
                        entity_fqn_index[newobj.fully_qualified_name]=newobj
                    else:
                        # Already found this one
                        pass
        # Save the entity_fqn_index to be accessible at object level
        self.entities=entities
        self.entity_fqn_index=entity_fqn_index

    def serialise(self, dataframe) -> rdflibGraph:
        # Convert the dataframe into a raw graph where rows are "triplified" with 
        # minimal steer from the serialisation.
        # This raw graph is expressed in the raw data namespace and consists of rows with floating column(name) predicates
        # linking to properties in the dataframe
        print(f"serialise:start {datetime.now()}")
        raw_graph = self._rdflib_graph_from_dataframe(dataframe)
        self.populate_entity_fqn_index(raw_graph)
        triple_generating_objects = list(self.entity_fqn_index.values())
        
        
        # Once the entities are defined, next it's time to link them all via the various relationship linkages
        for datarow in [r[0] for r in raw_graph.triples((None, RDF.type, Serialisation.DATA['row']))]:
            for s in [s for s in self.specifications.values()] :
                if isinstance(s, RelationshipInstanceSpecification):
                    triple_generating_objects.extend( s.constructRelationFromDataGraphRow(datarow, raw_graph, self.entity_fqn_index))
                elif isinstance(s, PropertyInstanceSpecification):
                    triple_generating_objects.extend( s.constructPropertyFromDataGraphRow(datarow, raw_graph, self.entity_fqn_index))


        return_graph = rdflibGraph(bind_namespaces="rdflib")

        for e in triple_generating_objects:
            for t in e.to_triples():
                return_graph.add(t)
        print(f"serialise:end {datetime.now()}")
        return return_graph

    def _rdflib_graph_from_dataframe(self, dataframe) -> rdflibGraph:
        """Reads in a dataframe and converts it into an anonymous graph"""
        g = rdflibGraph(bind_namespaces="rdflib")
        g.bind("DATA", Serialisation.DATA)
        g.add ((Serialisation.DATA.row, RDF.type, OWL.Class))
        g.add ((Serialisation.DATA.row, RDFS.label, Literal("Row")))

        for c in dataframe.columns:
            url_c = urllib.parse.quote(c)
            g.add(( Serialisation.DATA[f"column({url_c})"], RDF.type, OWL.DatatypeProperty )) # Define the column as a datatype property
            g.add(( Serialisation.DATA[f"column({url_c})"], RDFS.label, Literal(c) )) # Attach a simple label to the datatype property
            g.add(( Serialisation.DATA.row, Serialisation.DATA.has_field, Serialisation.DATA[f"column({url_c})"]))

        for c in self.glob_vars.keys():
            url_c = urllib.parse.quote(c)
            g.add(( Serialisation.DATA[f"column({url_c})"], RDF.type, OWL.DatatypeProperty )) # Define the column as a datatype property
            g.add(( Serialisation.DATA[f"column({url_c})"], RDFS.label, Literal(c) )) # Attach a simple label to the datatype property
            g.add(( Serialisation.DATA.row, Serialisation.DATA.has_field, Serialisation.DATA[f"column({url_c})"]))
        
        unspecified_colums=set()
        for row_i, data in dataframe.replace({np.nan: None,
                                            pd.NaT: None,
                                            pd.NA: None,
                                            "": None
                                            }).iterrows():
            row_url = Serialisation.DATA[uuid.uuid4().hex]
            row_index = Literal(row_i)
            g.add((row_url, RDF.type, Serialisation.DATA.row))
            g.add((row_url, Serialisation.DATA.row_ident, row_index))

            # Populate the contents of `GlobalVariables` as pseudo-columns associated with each 
            # data row
            for c,v in self.glob_vars.items():
                url_c = urllib.parse.quote(c)
                p_url = Serialisation.DATA[f"column({url_c})"]
                o_literal = Literal(v)
                g.add((row_url, p_url, o_literal))

            
            for c in dataframe.columns:
                
                url_c = urllib.parse.quote(c)
                p_url = Serialisation.DATA[f"column({url_c})"]

                if data[c] is not None:
                    #print(c, ":", data[c])
                    raw_data_value = data[c]
                    if c in self.referenced_columns:
                        # The column is identified as being referenced
                        # Now we need to see if it needs interpreting as a multivalue column or not
                        # N.B. there could be some discrepancy - i.e. one specification might
                        # interpret the value as multi-value, while another one doesn't.
                        # Let's adopt the convention that if *any* specification imposes the multivalues
                        # flag, then *all* specifications must treat it as such.
                        if c in self.multivalue_columns:
                            # Apply explosion transformation on the value presented
                            data_fetched = split_on_comma_respecting_quotes(raw_data_value)
                            #print( c, raw_data_value, data_fetched)
                        else:
                            data_fetched=[raw_data_value]
                    else:
                        data_fetched=[raw_data_value]
                        # print(f"This column {c} isn't referenced in the spec!")
                        unspecified_colums.add(c)
                
                    for v in data_fetched:
                        o_literal = Literal(v)
                        g.add((row_url, p_url, o_literal))
        print(f"The following columns are not listed in the spec {unspecified_colums}")
        return g
    
class SerialisationInstanceSpecification(object):
    
    def __init__(self, parent):
        self.parent_serialisation = parent
        self.column_list = []
        self._multivalues = None
    
    @staticmethod
    def extract_valid_fqns(rowurl, data_graph, fetch_key):
        f_key = [f for f in fetch_key if f!="<root>"]
        raw_fqn = SerialisationInstanceSpecification.get_keylist_from_datarow(rowurl, data_graph, f_key)
        # Each block of the fqn could contain multiple values - we need to build the collection of fqns that
        # could possibly be constructed from each combination -  it's the cartesian product that we're looking
        # for. 
        
        results = []
        if len(raw_fqn)>0 and raw_fqn[0]!=[]:
            for fqn_spec in list(product(*raw_fqn)):
                results.append( ".".join([n.toPython() for n in fqn_spec[::-1] if n != []]))
            return results
        else:

            return None
        
    @staticmethod
    def get_keylist_from_datarow(rowurl, data_graph, spec):
        fetched_values=[]
        for fetch_key in spec:
            # data_key = URIRef(Serialisation.DATA[f"column({fetch_key})"] )
            fetched_key_values = SerialisationInstanceSpecification.get_values_from_datarow(rowurl, data_graph, fetch_key)
            fetched_values.append([fkv for fkv in fetched_key_values if fkv != []])
        return fetched_values
    
    @staticmethod
    def get_values_from_datarow(rowurl, data_graph, key):
        # Given a row url and predicate key, return all the values that match
        data_key = URIRef(Serialisation.DATA[f"column({key})"] )
        key_values = [r[2] for r in data_graph.triples((rowurl, data_key, None))]
        return key_values

    
    def _populate_column_list(self):
        
        for attr_name, attr_value in vars(self).items():
            if attr_name.endswith("__column"):
                self.column_list.append(attr_value)

    def _expose_multi_value_field(self):
        if self._multivalues:
            if isinstance(self, NamedObjectInstanceSpecification):
                return self._subject__column
            elif isinstance(self, RelationshipInstanceSpecification):
                return self._object__column
            elif isinstance(self, PropertyInstanceSpecification):
                return self._literal__column
            else:
                raise TypeError(f"Class {self.__class__.__name__} not recognised as one supporting this function.")
        else:
            return None
            

class NamedObjectInstanceSpecification(SerialisationInstanceSpecification):
    def __init__(self, parent, target_class, classbase, instance_d):
        """Extract the values hosted in the configuration and store as 
        object properties"""
        super().__init__(parent)
        self.target_class = target_class
        self._instance_name = instance_d['InstanceName']
        self._subject__column = instance_d['SubjectTag']
        self._parent__column = instance_d['ParentTag']
        self._classbase_uri = classbase
        if self._parent__column is None or str(self._parent__column).strip()=="":
            self._parent__column="<root>"
        self._multivalues = instance_d.get("EnableMultiValues", False)
        
        super()._populate_column_list()

    def __repr__(self):
        return f"<{self.__class__.__name__}:{self._instance_name}/{self._parent__column}/{self._subject__column}>"
    
    def populate_naming_hierarchy_path(self):
        if isinstance(self, NamedObjectInstanceSpecification):
            # Needs parent column to determine naming_hierarchy - only works for NamedObjects
            #self.naming_hierarchy_path = self.parent_serialisation._traverse_hierarchy_path(self._instance_name)
            # 10/10/2025 - updated to use subject__column to instantiate hierarchy_path rather than instance name
            # keep an eye open for problems!
            self.naming_hierarchy_path = self.parent_serialisation._traverse_hierarchy_path(self._subject__column)
        else:
            raise TypeError(f"This function can only be called on InstanceSpecifications that reference a parent")
    
    def NamedObjectListFromDataGraphRow(self, row_uri, data_graph):
        # A NamedObject must have one or more principle:
        #       types
        #       names (KGNAM)
        #       labels (KGNAM)
        #       namespace 
        #       FullyQualifiedNames (KGNAM)
        # In addition, it might have any additional, overlapping properties that describe the object, but for
        # basic construction, we start with this list to populate the minimal, KGNAM based content (...or do we??)

        type_uris = [URIRef(self.target_class)]
        
        #fqn_parts = SerialisationInstanceSpecification.get_keylist_from_datarow(row_uri, data_graph, self.naming_hierarchy_path)
        #fqn = ".".join([n[0].toPython() for n in fqn_parts[::-1] if n != []])
        fqns = SerialisationInstanceSpecification.extract_valid_fqns(row_uri, data_graph, self.naming_hierarchy_path)
        #print("fqns: ", fqns)
        # What instances exist that contain name values?
        # Let's use the final value from each fqn as a proxy for Name
        #names = SerialisationInstanceSpecification.get_values_from_datarow(row_uri, data_graph, self._subject__column)
        namespace = self._classbase_uri
        object_list=[]
        if fqns is not None:
            
            for fqn in fqns:
                names = [fqn.split(".")[-1]]
                if fqn is not None:
                    object_list.append( NamedObject(type_uris, fqn, names, namespace) )
        else:
            print(f"{self._instance_name} generated no objects for this row")
        return object_list


class NamedObject(object):
    def __init__(self, type_uris, fully_qualified_name, names, namespace):
        ENT=Namespace(namespace)
        self.uri = ENT[f"{uuid.uuid4().hex}"].toPython()
        self.types=[]
        self.names=names
        self.fully_qualified_name = fully_qualified_name
        # Coerce self.type to be a string 
        for uri in type_uris:
            if isinstance(uri, str):
                self.types.append(uri)
            elif isinstance(uri, URIRef):
                self.types.append(uri.toPython())

    def to_triples(self)-> list[RDFTriple]:
        triples = []
        for t in self.types:
            triples.append((URIRef(self.uri), RDF.type, URIRef(t)))

        for n in self.names:
            triples.append((URIRef(self.uri), URIRef("https://kgraph.foo/onto/kgmeta#Name"), Literal(n)))
        
        triples.append((URIRef(self.uri), URIRef("https://kgraph.foo/onto/kgmeta#FullyQualifiedName"), Literal(self.fully_qualified_name)))
        return triples
                
    def __repr__(self):
        return f"<NamedObject:{self.types[0]}//{self.fully_qualified_name}>({self.uri})>"

class RelationshipInstanceSpecification(SerialisationInstanceSpecification):
    def __init__(self, parent, target_class, instance_d):
        """Extract the values hosted in the configuration and store as 
        object properties"""
        super().__init__(parent)
        self.target_class = target_class
        self._instance_name = instance_d['InstanceName']
        self._subject__column = instance_d['SubjectTag']
        self._object__column = instance_d['ObjectTag']
        self._multivalues = instance_d.get("EnableMultiValues", False)
        super()._populate_column_list()

    def __repr__(self):
        return f"<{self.__class__.__name__}:{self._instance_name}/{self._object__column}/{self._subject__column}>"
    
    def constructRelationFromDataGraphRow(self, row_uri, data_graph, entity_fqn_index):
        # Collect the set of candidate fqn specifications (i.e. the columns used to fetch the FQNs from the data row) for both sides of the relationship (subject, object)
        # These are expressed as lists containing string values that describe the original column names
        candidate_subject_spec = self.parent_serialisation._traverse_hierarchy_path(self._subject__column)
        candidate_object_spec = self.parent_serialisation._traverse_hierarchy_path(self._object__column)

        # Get the FQNs from the data row - but these can be tricky in that if no match for the root of the FQN is found, 
        # it still shows, but with element[0] being empty
        subject_fqns = SerialisationInstanceSpecification.extract_valid_fqns(row_uri, data_graph, candidate_subject_spec)
        object_fqns = SerialisationInstanceSpecification.extract_valid_fqns(row_uri, data_graph, candidate_object_spec)
        subject_entities=[]
        if subject_fqns is not None:
            for fqn in subject_fqns:
                subject_entities.append ( entity_fqn_index.get(fqn, None) )

        object_entities=[]
        if object_fqns is not None:
            for fqn in object_fqns:
                object_match = entity_fqn_index.get(fqn, None)
                if object_match is None:
                    print(f"\t\tObject match not found for {fqn}")
                object_entities.append ( object_match )

        # Review the returned object lists and make a call on whether there's enough information to accept
        # whatever matches are returned
        # Since the subjects and objects might be in n>1 collections, we generate the product of both to
        # create a single relations which consists of all combinations of both (in practice, subjects should)
        # be singular, but the multivalues option means objects can contain multiple possibilities
        relations = list(product(*[subject_entities,object_entities]))
        relation_list=[]
        for relation in relations:
            if all([v is not None for v in relation]):
                sobj, oobj = relation
                relation_list.append ( RelationObject(sobj, oobj, self.target_class))


        return relation_list

class RelationObject(object):
    def __init__(self, subject, object, relation_uri):
        self.subject = subject
        self.object = object
        self.relation_uri = relation_uri

    def to_triples(self) -> list[RDFTriple]:
        triples = []

        triples.append((URIRef(self.subject.uri), URIRef(self.relation_uri), URIRef(self.object.uri)))

        return triples
                
    def __repr__(self):
        return f"<Relation:{self.relation_uri}//<({self.subject.uri}-{self.object.uri})>"


class PropertyInstanceSpecification(SerialisationInstanceSpecification):
    def __init__(self, parent, target_class, instance_d):
        """Extract the values hosted in the configuration and store as 
        object properties"""
        super().__init__(parent)
        self.target_class = target_class
        self._instance_name = instance_d['InstanceName']
        self._subject__column = instance_d['SubjectTag']
        self._literal__column = instance_d['LiteralTag']
        self._multivalues = instance_d.get("EnableMultiValues", False)
        super()._populate_column_list()


    def constructPropertyFromDataGraphRow(self, row_uri, data_graph, entity_fqn_index) -> list[RDFTriple]:
        # Get the subject fqn
        candidate_subject_spec = self.parent_serialisation._traverse_hierarchy_path(self._subject__column)

        # Get the FQNs from the data row - but these can be tricky in that if no match for the root of the FQN is found, 
        # it still shows, but with element[0] being empty
        subject_fqns = SerialisationInstanceSpecification.extract_valid_fqns(row_uri, data_graph, candidate_subject_spec)
        subject_entities=[]
        if subject_fqns is not None:
            for fqn in subject_fqns:
                subject_entities.append ( entity_fqn_index.get(fqn, None) )

        # Now extract the literal contents from the data row, which should *already* respect earlier multi-values processing
        literal_values = SerialisationInstanceSpecification.get_values_from_datarow(row_uri, data_graph, self._literal__column)

        # Review the returned object lists and make a call on whether there's enough information to accept
        # whatever matches are returned
        # Since the subjects and objects might be in n>1 collections, we generate the product of both to
        # create a single relations which consists of all combinations of both (in practice, subjects should)
        # be singular, but the multivalues option means objects can contain multiple possibilities
        relations = list(product(*[subject_entities,literal_values]))
        relation_list=[]
        for relation in relations:
            if all([v is not None for v in relation]):
                sobj, oobj = relation
                relation_list.append ( PropertyObject(sobj, oobj, self.target_class))


        return relation_list



    def __repr__(self):
        return f"<{self.__class__.__name__}:{self._instance_name}/{self._literal__column}/{self._subject__column}>"




class PropertyObject(object):
    def __init__(self, subject, property, relation_uri):
        self.subject = subject
        self.property = property
        self.relation_uri = relation_uri

    def to_triples(self)->list[RDFTriple]:
        triples = []

        triples.append((URIRef(self.subject.uri), URIRef(self.relation_uri), Literal(self.property)))

        return triples
                
    def __repr__(self):
        return f"<Relation:{self.relation_uri}//<({self.subject.uri}-{self.property})>"



from dataclasses import dataclass
import spacy
from kgraph.declarations import KGMETA

def parse_text(nlpdoc):
    """Read in a spacy document and process it to provide outputs
    that can be used to retrieve structural meta-data
    """
    sentence_root_loc = dict()
    sentence_root_lem = dict()
    subject_node_loc = dict()
    subject_node_full_locs = dict()
    subject_text=dict()

    object_node_loc = dict()
    object_node_full_locs = dict()
    object_text=dict()
    
    sentence_root_t_id = dict()
    sr_distance = dict()
    or_distance = dict()
    
    # Extract raw token level meta-data for each token, split by sentence
    d_links = [
    (   e, 
        f, 
        t.idx, 
        t.text, 
        t.lemma_, 
        t.pos_, 
        t.dep_, 
        t.head.idx, 
        t.head.text, 
        t.head.lemma_, 
        t.head.pos_, ) 
               for e,s in enumerate(nlpdoc.sents) 
                   for f,t in enumerate(s)
              ]

    # Create an empty graph to help host the markup content
    sentence_ids = set([s for s, *_ in d_links])
    d_graphs = dict()
    d_graphs_ud = dict()
    for s_id in sentence_ids:
        d_graphs[s_id]= nx.MultiDiGraph()


    # Looping over the tokens per sentence, populate a graph with token data
    for s_id, w_seq, Lt_id, Lt_text, Lt_lem, Lt_POS, t_dep, Rt_id, Rt_text, Rt_lem, Rt_POS in d_links:
        d_graphs[s_id].add_node(Lt_id, seq=w_seq, text=Lt_text, lem=Lt_lem, POS=Lt_POS)
        d_graphs[s_id].add_edge(Lt_id, Rt_id, d_type=t_dep)
        if t_dep == 'ROOT':
            sentence_root_loc[s_id]=w_seq, Lt_id
            sentence_root_lem[s_id] = Lt_lem
        if s_id not in sentence_ids:
            sentence_ids.add(s_id)

    # Copy the populated directed graph into an undirected graph format
    for s_id in sentence_ids:
        # Create undirected graphs from directed collection
        d_graphs_ud[s_id]= nx.Graph(d_graphs[s_id])

    # Cycle over the contents of the tokens, per sentence
    for s_id, w_seq, Lt_id, Lt_text, Lt_lem, Lt_POS, t_dep, Rt_id, Rt_text, Rt_lem, Rt_POS in d_links:
        if s_id in sentence_root_loc:
            # Calculate the node-to-node distance between the current candidate subject, and the root node
            candidate_root_distance = nx.shortest_path_length(d_graphs_ud[s_id], Lt_id, sentence_root_loc[s_id][1])
            # Test for the existance of a subject - and identify if it's the most central one to the sentence's root node
            if t_dep in ('nsubj', 'nsubjpass') and Rt_id in set(nx.ancestors(d_graphs[s_id], sentence_root_loc[s_id][1]).union(set([sentence_root_loc[s_id][1]]))):
                if s_id not in subject_node_loc or ( s_id in subject_node_loc and candidate_root_distance < sr_distance[s_id]):
                    subject_node_loc[s_id]=w_seq,Lt_id
                    subject_node_full_locs[s_id]=set(nx.ancestors(d_graphs[s_id], Lt_id)).union(set([Lt_id]))
                    subject_text[s_id]=" ".join([t for t,s in sorted(
                        [(d['text'],d['seq']) for n,d in d_graphs[s_id].nodes(data=True) if n in subject_node_full_locs[s_id]]
                        , key=lambda y : y[1])
                    ])
                    sr_distance[s_id] = candidate_root_distance
            # If the current token is an object - test to see if it's the one most local to the sentence's root node
            if t_dep in ('dobj', 'pobj') and Rt_id in set(nx.ancestors(d_graphs[s_id], sentence_root_loc[s_id][1]).union(set([sentence_root_loc[s_id][1]]))):
                if s_id not in object_node_loc or ( s_id in object_node_loc and candidate_root_distance < or_distance[s_id]):
                    object_node_loc[s_id]=w_seq,Lt_id
                    object_node_full_locs[s_id]=set(nx.ancestors(d_graphs[s_id], Lt_id)).union(set([Lt_id]))
                    object_text[s_id]=" ".join([t for t,s in sorted(
                        [(d['text'],d['seq']) for n,d in d_graphs[s_id].nodes(data=True) if n in object_node_full_locs[s_id]]
                        , key=lambda y : y[1])
                    ])
                    or_distance[s_id] = candidate_root_distance
    

    # s_id, w_seq, Lt_id, Lt_text, Lt_lem, Lt_POS, t_dep, Rt_id, Rt_text, Rt_lem, Rt_POS
    # Return all the values collected relating to each sentence's root, its core subjects and objects.
    return d_links, sentence_root_loc, sentence_root_lem, subject_node_loc, subject_node_full_locs, subject_text, object_node_loc, object_node_full_locs, object_text, d_graphs


def get_root_nodes(d_links):
    route_links = []
    for link in d_links:
        s_id, t_id, t_text, t_lem, t_pos, t_dep, h_id,h_text, h_lem, h_pos = link
        if t_dep.lower() == 'root':
            route_links.append((s_id, t_id, t_text, t_lem, t_dep, h_id, h_text, h_lem))
    return route_links


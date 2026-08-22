from kgraph_fixtures_test import (kgp_pipeline_for_testthings, test_things_data_df)
from kgraphing import ganalytics
from networkx import MultiDiGraph

def test_serialise_testthings_mapping_fqn_tree(kgp_pipeline_for_testthings, test_things_data_df):
    # Run the analytics against a prepared dataset and test that the returned metrics records
    # contain the right collection of headers...
    # A better test would be to review the contents and population - but for now, just getting
    # it to run successfully demonstrates a degree of holding-together under any future api or
    # unintended change.
    rdfgraph = kgp_pipeline_for_testthings.process(test_things_data_df)
    pred_metrics=[]
    relations = set([r[0] for r in rdfgraph.query("""SELECT DISTINCT ?p WHERE {?s ?p ?o. } GROUP BY ?p""")])
    for pred in relations:
        g = MultiDiGraph()
        for s, _, o in rdfgraph.triples((None, pred, None)):
            g.add_edge(s, o)
        metrics = ganalytics.calculate_metrics_over_induced_subgraphs(g)
        m_summary = ganalytics.summarise_metrics_records(metrics)
        pred_metrics.append({**{"pred" : pred } , **m_summary})
        assert [k for k in pred_metrics[0].keys()]== \
            ['pred',
            'population',
            'partitions',
            'mean_p_size',
            'mean_p_std',
            'mean_p_radius',
            'p_cyclic',
            'p_tree',
            'p_source',
            'p_sink',
            'p_trans',
            'p_hubs']
        
from kgraphing import setfunctions

def test_sets_to_lir():
    set_a = {1,2,3,4}
    set_b = {3,4,5,6}
    l,i,r = setfunctions.sets_to_lir(set_a, set_b)
    assert l=={1,2}
    assert i=={3,4}
    assert r=={5,6}

def test_lir_stats():
    set_a = {1,2,3,4}
    set_b = {3,4,5,6}
    precision, recall, f1_score = setfunctions.lir_stats(set_a, set_b)
    assert precision == 0.5
    assert recall == 0.5
    assert f1_score == 0.5

def test_venn_partitions():
    set_a = {1,2,3,4}
    set_b = {3,4,5,6}
    set_c = {1,4,6,8}
    vp_1 = setfunctions.venn_partitions({"a" : set_a, 
                                        "b" : set_b, 
                                        "c" : set_c},
                                        notation_style="strict")

    assert vp_1 == {'a ∩ c ∩ bᶜ': {1}, 
                    'a ∩ bᶜ ∩ cᶜ': {2}, 
                    'a ∩ b ∩ cᶜ': {3},
                    'a ∩ b ∩ c': {4}, 
                    'b ∩ aᶜ ∩ cᶜ' : {5}, 
                    'b ∩ c ∩ aᶜ' : {6},
                    'c ∩ aᶜ ∩ bᶜ' : {8}
                    } 

    vp_2 = setfunctions.venn_partitions({"a" : set_a, 
                                    "b" : set_b, 
                                    "c" : set_c},
                                    notation_style="loose")

    assert vp_2 == {'{a,c}': {1}, 
                    '{a}': {2}, 
                    '{a,b}': {3},
                    '{a,b,c}': {4}, 
                    '{b}' : {5}, 
                    '{b,c}' : {6},
                    '{c}' : {8}
                } 
    vp_3 = setfunctions.venn_partitions({"a" : set_a, 
                                    "b" : set_b, 
                                    "c" : set_c},
                                    notation_style="binindex")

    for k,v in vp_3.items():
        print(k, "-", v)

    assert vp_3 == {frozenset({'a','c'}): {1}, 
                    frozenset({'a'}): {2}, 
                    frozenset({'a','b'}): {3},
                    frozenset({'a','b','c'}): {4}, 
                    frozenset({'b'}) : {5}, 
                    frozenset({'b','c'}) : {6},
                    frozenset({'c'}) : {8}
                } 



from itertools import combinations


def sets_to_lir(set_a, set_b):
    l, i, r = set_a - set_b, set_a.intersection(set_b), set_b - set_a
    return l, i, r


def lir_stats(set_a, set_b):
    l, i, r = sets_to_lir(set_a, set_b)
    total_size, len_a, len_b = (
        sum((1 for v in [l, i, r] for e in v)),
        len(set_a),
        len(set_b),
    )
    precision = (len(i)) / (len(i) + len(l))
    recall = (len(i)) / (len(i) + len(r))
    if (precision + recall) != 0:
        f1_score = 2 * (precision * recall) / (precision + recall)
    else:
        f1_score = 0
    return precision, recall, f1_score


def venn_partitions(sets: dict[str, set], notation_style: str):
    """Given a dictionary containing named sets, partition them
    to show their intersection based partitions.
    The notion_style parameter will define the naming function
    used to describe each partition.
        strict uses the intersection notation ∩ with ᶜ to describe the complement
        loose uses a comma-delimited form where inclusive sets are listed
            and non-inclusion is inferred by not-being present
        binindex returns a dict which uses 
            frozensets of the inclusive-only dict-names as a key, 
            and the set of container elements are returned as values"""
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
            try:
                in_elements = set.intersection(*[set_contents[i] for i in in_sets])
                out_elements = set.union(*[set_contents[i] for i in out_sets] + [set()])
            except TypeError as e:
                print(in_sets)
                print(out_sets)
                raise e

            contents = in_elements - out_elements
            if contents != set():
                partition_d[notation] = contents
    return partition_d
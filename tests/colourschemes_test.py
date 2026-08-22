from itertools import cycle
from kgraphing import colourschemes

def test_get_colour_scheme():
    # Colourschemes provides some named schemes of colours for use in visualisations
    # Select from a list and confirm length and first colour match expected values
    scheme_names_being_tested = {"bold4", "rich10", "metro9", "tfl-tube"}
    scheme_test_values = {"bold4": [4, "#ff3e3a"], 
                          "rich10" :[10,"#001219"], 
                          "metro9":[9,"#ea5545"], 
                          "tfl-tube":[14,"#B26300"]}
    for scheme_name in scheme_names_being_tested:
        c_scheme = colourschemes.get_colour_scheme(scheme_name)
        assert len(c_scheme) == scheme_test_values[scheme_name][0]
        assert c_scheme[0]==scheme_test_values[scheme_name][1]

def test_get_colour_scheme_error():
    bad_scheme="no_scheme_of_this_name_exists"
    try:
        c_scheme = colourschemes.get_colour_scheme(bad_scheme)
    except ValueError as e:
        assert str(e)==f"Colour scheme '{bad_scheme}' not found."

def test_gen_cycle():
    # Similar to the previous test, only this time, the return object
    # should be a python cycle object.
    scheme_names_being_tested = {"bold4", "rich10", "metro9", "tfl-tube"}
    scheme_test_values = {"bold4": [4, "#ff3e3a"], 
                          "rich10" :[10,"#001219"], 
                          "metro9":[9,"#ea5545"], 
                          "tfl-tube":[14,"#B26300"]}
    for scheme_name in scheme_names_being_tested:
        c_scheme = colourschemes.gen_cycle(scheme_name)
        assert type(c_scheme) == cycle
        assert next(c_scheme)==scheme_test_values[scheme_name][1]

def test_get_gen_cycle_error():
    bad_scheme="no_scheme_of_this_name_exists"
    try:
        c_scheme = colourschemes.gen_cycle(bad_scheme)
    except ValueError as e:
        assert str(e)==f"Colour scheme '{bad_scheme}' not found."

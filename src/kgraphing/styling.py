"""Set of utilities for generating style values"""

import colorsys


def partition_range(p, r):
    p_array = []
    m_array = []
    interpartition_step = 1 / p
    mid_offset = interpartition_step / 2
    for i in range(0, p):
        p_array.append(i * interpartition_step)
        m_array.append((i * interpartition_step) + mid_offset)
    return p_array, m_array


test = "#bf3f3f", "#3fbf3f", "#3f3fbf"
test = "#e51919", "#19e519", "#1919e5"


test = (
    "#e51919",
    "#e57f19",
    "#e5e519",
    "#7fe519",
    "#19e519",
    "#19e57f",
    "#19e5e5",
    "#197fe5",
    "#1919e5",
    "#7f19e5",
    "#e519e5",
    "#e5197f",
)

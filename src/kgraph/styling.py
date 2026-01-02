"""Set of utilities for generating style values"""

import colorsys

def partition_range(p,r):
    p_array=[]
    m_array=[]
    interpartition_step = 1 / p
    mid_offset = interpartition_step / 2
    for i in range(0,p):
        p_array.append(i * interpartition_step)
        m_array.append((i * interpartition_step)+mid_offset)
    return p_array, m_array


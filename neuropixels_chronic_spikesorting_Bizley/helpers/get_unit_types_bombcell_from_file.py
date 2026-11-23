from pathlib import Path
import numpy as np
from neuropixels_chronic_spikesorting_Bizley.helpers.load_tsv import load_tsv

def get_unit_types_bombcell_from_file(ks_dir):
    unit_type_string = load_tsv(ks_dir / 'cluster_bc_unitType.tsv')
    # unit_type = np.isin(unit_type_string[:,1],['GOOD','MUA'])
    # labels = {0: "noise", 1: "somatic, good", 2: "somatic, MUA",3: "non-somatic, good" if param["splitGoodAndMua_NonSomatic"] else "non-somatic",4: "non-somatic, MUA", 5: ""}
    unit_type = np.zeros(len(unit_type_string[:,1]))
    unit_type[np.isin(unit_type_string[:,1],['GOOD'])] = 1
    unit_type[np.isin(unit_type_string[:,1],['MUA'])] = 2
    unit_type[np.isin(unit_type_string[:,1],['NON-SOMA'])] = 3
    return unit_type,unit_type_string[:,1]


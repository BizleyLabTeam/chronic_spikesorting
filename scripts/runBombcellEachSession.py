### runs bombcell pipeline for each session in specified session sets, saving results into the kilosort output folder.

from pathlib import Path
import pandas as pd
from itertools import product as combination_product

import numpy as np
import shutil

import matplotlib
import matplotlib.pyplot as plt

# si is just used to read the meta file in this script which we probably can do ourselves
# TODO: replace spikeinterface read_spikeglx with in-house function
import spikeinterface.full as si

import kilosort as ks
import bombcell as bc
from bombcell.plot_functions import plot_summary_data

from neuropixels_chronic_spikesorting_Bizley.helpers.get_unit_types_bombcell_from_file import get_unit_types_bombcell_from_file

from neuropixels_chronic_spikesorting_Bizley.helpers.helpers_spikesorting_scripts import get_channelmap_names, getSessionsWithinMap
from neuropixels_chronic_spikesorting_Bizley.spikesorting import applyOverStrike, nullify_saturations, makeAndProcessRaw, getLFP
from neuropixels_chronic_spikesorting_Bizley.run_bombcell_session import run_bombcell_session
from neuropixels_chronic_spikesorting_Bizley.sessionSetManagement.getSessionsWithinMapForSessionSet import getSessionsWithinMapForSessionSet
from generally_useful_functions_Bizley.getCorrectRecordingForRegion import getCorrectRecordingForRegion
from generally_useful_functions_Bizley.splitLocationsIntoShanks import splitLocationsIntoShanks

import neuropixels_chronic_spikesorting_Bizley.outerLoopConfigs as outerLoopConfigs
import neuropixels_chronic_spikesorting_Bizley.all_VE_config as all_VE_config # this config file should be synced between all your VEs.

from neuropixels_chronic_spikesorting_Bizley.sessionSetManagement.gatherSessionSetListForFerret import gatherSessionSetListForFerret
from neuropixels_chronic_spikesorting_Bizley.sessionSetManagement.SpecifySessionSetParameters import SpecifySessionSetParameters

def main():
    kilosort_version = 4 ### not future proofed. But algorithmically finding the ks version wouldn't change that. ks.cersion
    reloadExistingResults = False # should never want to reload existing results if you are running this code, as its only purpose is to save results. Another variable will skip stuff already done.
    plot_withPlannedBreakpoints = True
    recordingZones = gatherSessionSetListForFerret(all_VE_config.ferret) ### still doing one ferret at a time. Though there is potential to iterate them... Don't really see a good reason to do so.

    toIterate = list(combination_product([all_VE_config.ferret],recordingZones,all_VE_config.regionLabels)) ### this function seems nondeterministic?
    toIterate = sorted(toIterate,key=lambda tup: tup[2]) ### first sort by region
    toIterate = sorted(toIterate,key=lambda tup: tup[1]) ### then sort by session set.
    pass
    for ixixi,sessionSet in enumerate(toIterate):
        sessionSetParams = SpecifySessionSetParameters(sessionSet[0],sessionSet[1],sessionSet[2])
        NAS_SessionsWithinMap,Local_SessionsWithinMap = getSessionsWithinMapForSessionSet(sessionSetParams)
        actuallyUsedSessions = np.zeros(len(NAS_SessionsWithinMap),dtype='bool')
        session_results = [] ### don't know that I actually want or need this yet.
        for i, (session,session_local) in enumerate(zip(NAS_SessionsWithinMap,Local_SessionsWithinMap)):

            temp_session_configs = [{ ### session config code as expected by the UnitMatch/Bonbcell code.
                            'name': [], ## session name
                            'ks_dir': [], ### points to where the spikesort results are, I believe.
                            'raw_file': [],
                            'meta_file': [],
                            'save_path': []}] ### points to where you save the bombcell results, which ends up being the ks_dir
            session_name = session.name
            if not i: # initialize
                session_configs = temp_session_configs
                # custom_bombcell_paths = [] #### MIGHT NOT NEED remove if I don't
                # custom_raw_waveform_paths  = [] #### MIGHT NOT NEED remove if I don't
            else:
                session_configs = session_configs + temp_session_configs
            session_configs[i]["name"] = session_name
            print(f'Processing {session_name}')



            imecFolderList = list(session.glob('*' + 'imec' + '*'))
            metaFileData,usedImro,NASprobeFolder = getCorrectRecordingForRegion(imecFolderList,sessionSetParams['channel_map_to_use'],localData=False)





            if usedImro == None:
                pass # usedImro should be None if, for any reason, the channel map is not used in this session. In that case, we skip it.
                actuallyUsedSessions[i] = False ### should already be false but just cause
            else:
                # if there is an imro file, we should fill out required paths.
                actuallyUsedSessions[i] = True
                local_probeFolder = list(session_local.glob('*' + usedImro[:-3]))
                local_probeFolder = local_probeFolder[0] / Path('catgt_CorrectedRaw')  # name of probe folder
                session_configs[i]["meta_file"] = list(local_probeFolder.glob('*.meta'))[0]
                session_configs[i]["raw_file"] = list(local_probeFolder.glob('*.bin'))[0]

                sorter_output_folder =  all_VE_config.output_folder / sessionSet[0] / sessionSet[1] / sessionSet[2] / session_name
                session_configs[i]["ks_dir"] = sorter_output_folder
                session_configs[i]["save_path"] = session_configs[i]["ks_dir"] ### As far as I can tell, this will always be the best place to save bombcell results.

                #### PROBABLY DONT NEED THE FOLLOWING FOR THIS CODE, DELETE IF TRUE
                    # custom_bombcell_paths  = custom_bombcell_paths  + [session_configs[i]["ks_dir"] / Path("cluster_bc_unitType.tsv")] # this variable will only include the actually included sessions...
                    # custom_raw_waveform_paths = custom_raw_waveform_paths + [session_configs[i]["raw_file"]] ### not sure what this is or if it is correct. This is where the raw file is. Possibly I want the folder though...
                pass









            print(f"\n{'=' * 60}")
            print(f"SESSION {i + 1}/{len(Local_SessionsWithinMap)} {session_name}")
            print(f"{'=' * 60}")
            try:

                result,template_waveforms = run_bombcell_session(session_configs[i],kilosort_version,reloadExistingResults)
                # within results:
                #         'name': name,
                #         'ks_dir': ks_dir,
                #         'save_path': str(save_path),
                #         'quality_metrics': quality_metrics,
                #         'param': param,
                #         'unit_type': unit_type,
                #         'unit_type_string': unit_type_string
                session_results.append(result)
                pass
            except:
                raise ### comment this out if you want to move past errors.
                result = dict() ### make a blank dict
                with open(errorFileName, "a") as f:
                    print('bombcell failed for ' + session_configs[i]['name'], file=f) # puts errors into a file so you can check them later.
                pass



            pass
            if plot_withPlannedBreakpoints:
                if bool(result):
                    pass
                    plot_summary_data(result['quality_metrics'], template_waveforms, result['unit_type'], result['unit_type_string'], result['param'])
                    pass ### put breakpoint here.


if __name__ == '__main__':
    main()
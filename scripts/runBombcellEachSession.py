### runs bombcell pipeline for each session in specified session sets, saving results into the kilosort output folder.
### optionally can plot as you do it via breakpoint; I plan to write another function which loads and plots previous
### results, and this may be preferable for real work.

### external functions
from pathlib import Path
from itertools import product as combination_product

import numpy as np
from bombcell.plot_functions import plot_summary_data

### internal functions
from neuropixels_chronic_spikesorting_Bizley.helpers.helpers_spikesorting_scripts import getSessionsWithinMap
from neuropixels_chronic_spikesorting_Bizley.run_bombcell_session import run_bombcell_session
from neuropixels_chronic_spikesorting_Bizley.sessionSetManagement.getSessionsWithinMapForSessionSet import getSessionsWithinMapForSessionSet
from generally_useful_functions_Bizley.getCorrectRecordingForRegion import getCorrectRecordingForRegion

import neuropixels_chronic_spikesorting_Bizley.all_VE_config as all_VE_config # this config file should be synced between all your VEs.

from neuropixels_chronic_spikesorting_Bizley.sessionSetManagement.gatherSessionSetListForFerret import gatherSessionSetListForFerret
from neuropixels_chronic_spikesorting_Bizley.sessionSetManagement.SpecifySessionSetParameters import SpecifySessionSetParameters

def main():
    ### main arguments/constants
    kilosort_version = 4 ### not future proofed. But algorithmically finding the ks version wouldn't change that.
    reloadExistingResults = False # should never want to reload existing results if you are running this code, as its only purpose is to save results. Another variable will skip stuff already done.
    skipIfAlreadyDone = False # not actually implemented yet. I should do it before I even commit this comment though.
    plot_withPlannedBreakpoints = True ### turns on plotting; intended to be used with breakpoints. Hense, the name.

    ### set up sessionSet loops, standard style
    recordingZones = gatherSessionSetListForFerret(all_VE_config.ferret) ### still doing one ferret at a time. Though there is potential to iterate them... Don't really see a good reason to do so.
    toIterate = list(combination_product([all_VE_config.ferret],recordingZones,all_VE_config.regionLabels)) ### this function seems nondeterministic?
    toIterate = sorted(toIterate,key=lambda tup: tup[2]) ### first sort by region
    toIterate = sorted(toIterate,key=lambda tup: tup[1]) ### then sort by session set.
    ### session set loop
    for ixixi,sessionSet in enumerate(toIterate):
        sessionSetParams = SpecifySessionSetParameters(sessionSet[0],sessionSet[1],sessionSet[2])
        NAS_SessionsWithinMap,Local_SessionsWithinMap = getSessionsWithinMapForSessionSet(sessionSetParams)
        actuallyUsedSessions = np.zeros(len(NAS_SessionsWithinMap),dtype='bool')
        ### session loop
        for i, (session,session_local) in enumerate(zip(NAS_SessionsWithinMap,Local_SessionsWithinMap)):
            session_name = session.name
            ## here, add anything to sessionSetParams you want to transfer into adjustParametersSessionSpecific for bombcell
            sessionSetParams['currentSession'] = session_name
            temp_session_configs = [{ ### session config code as expected by the UnitMatch/Bonbcell code. Keeps track for every session in the loop, although the code doesn't need that.
                            'name': [], ## session name
                            'ks_dir': [], ### points to where the spikesort results are, I believe.
                            'raw_file': [],
                            'meta_file': [],
                            'save_path': [],
                            'sessionSetParams':sessionSetParams, # added into the bombcell structure.
                            }] ### points to where you save the bombcell results, which ends up being the ks_dir

            if not i: # initialize
                session_configs = temp_session_configs
            else:
                session_configs = session_configs + temp_session_configs
            session_configs[i]["name"] = session_name
            print(f'Processing {session_name}')
            ### choose correct probe and load metadata
            imecFolderList = list(session.glob('*' + 'imec' + '*'))
            metaFileData,usedImro,NASprobeFolder = getCorrectRecordingForRegion(imecFolderList,sessionSetParams['channel_map_to_use'],localData=False)
            if usedImro == None:
                pass # usedImro should be None if, for any reason, the channel map is not used in this session. In that case, we skip it.
                actuallyUsedSessions[i] = False ### should already be false but just for symmetry/clarity
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


            print(f"\n{'=' * 60}")
            print(f"SESSION {i + 1}/{len(Local_SessionsWithinMap)} {session_name}")
            print(f"{'=' * 60}")
            existing_results = session_configs[i]["save_path"] / "cluster_bc_unitType.tsv" ### the name cluster_bc_unitType is hardcoded within bombcell, so don't change it.
            if not(existing_results.exists()&skipIfAlreadyDone): ### also skips plotting. Imo, it should. Another function will load things to plot.
                try:
                    result,template_waveforms = run_bombcell_session(session_configs[i],kilosort_version,reloadExistingResults) # "result" is a dict with well named keys. template_waveforms also are what the name implies. Both are only used for plotting, within this code; actual results are saved within the function.
                except:
                    raise ### comment this out if you want to move past errors.
                    result = dict() ### make a blank dict
                    with open(errorFileName, "a") as f:
                        print('bombcell failed for ' + session_configs[i]['name'], file=f) # puts errors into a file so you can check them later.
                    pass
                if plot_withPlannedBreakpoints:
                    if bool(result):
                        pass
                        plot_summary_data(result['quality_metrics'], template_waveforms, result['unit_type'], result['unit_type_string'], result['param'])
                        pass ### put breakpoint here.


if __name__ == '__main__':
    main()
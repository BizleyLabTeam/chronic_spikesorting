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


from neuropixels_chronic_spikesorting_Bizley.helpers.helpers_spikesorting_scripts import get_channelmap_names, getSessionsWithinMap
from neuropixels_chronic_spikesorting_Bizley.spikesorting import applyOverStrike, nullify_saturations, makeAndProcessRaw, getLFP
from neuropixels_chronic_spikesorting_Bizley.sessionSetManagement.getSessionsWithinMapForSessionSet import getSessionsWithinMapForSessionSet
from generally_useful_functions_Bizley.getCorrectRecordingForRegion import getCorrectRecordingForRegion
from generally_useful_functions_Bizley.splitLocationsIntoShanks import splitLocationsIntoShanks

import neuropixels_chronic_spikesorting_Bizley.outerLoopConfigs as outerLoopConfigs
import neuropixels_chronic_spikesorting_Bizley.all_VE_config as all_VE_config # this config file should be synced between all your VEs.
from neuropixels_chronic_spikesorting_Bizley.sessionSetManagement.gatherSessionSetListForFerret import gatherSessionSetListForFerret
from neuropixels_chronic_spikesorting_Bizley.sessionSetManagement.SpecifySessionSetParameters import SpecifySessionSetParameters

def main():

    doSessionRasters = True

    recordingZones = gatherSessionSetListForFerret(all_VE_config.ferret) ### still doing one ferret at a time. Though there is potential to iterate them... Don't really see a good reason to do so.

    #sessionSetParams = SpecifySessionSetParameters(all_VE_config.ferret,SessionSetName,all_VE_config.regionLabels)
    toIterate = list(combination_product([all_VE_config.ferret],recordingZones,all_VE_config.regionLabels)) ### this function seems nondeterministic?
    toIterate = sorted(toIterate,key=lambda tup: tup[2]) ### first sort by region
    toIterate = sorted(toIterate,key=lambda tup: tup[1]) ### then sort by session set.
    pass
    for ixixi,sessionSet in enumerate(toIterate):
        sessionSetParams = SpecifySessionSetParameters(sessionSet[0],sessionSet[1],sessionSet[2])
        NAS_SessionsWithinMap,Local_SessionsWithinMap = getSessionsWithinMapForSessionSet(sessionSetParams)
        setUpSessionLoop = True # preferred in case "i==0" is not working
        largestSpikeSampleTimeEachSession = np.zeros(len(Local_SessionsWithinMap))
        if doSessionRasters:
            sessionRasterPlots = dict()
        for i, session in enumerate(Local_SessionsWithinMap):
            session_name = session.name
            sorter_output_folder =  all_VE_config.output_folder / sessionSet[0] / sessionSet[1] / sessionSet[2] / session_name
            spike_clusters = np.load(sorter_output_folder / 'spike_clusters.npy')
            amplitudes = np.load(sorter_output_folder / 'amplitudes.npy')
            full_amp = np.load(sorter_output_folder / 'full_amp.npy')
            spike_positions = np.load(sorter_output_folder / 'spike_positions.npy')
            spike_times = np.load(sorter_output_folder / 'spike_times.npy')
            spike_shankLabel = splitLocationsIntoShanks(spike_positions)
            largestSpikeSampleTimeEachSession[i] = spike_times[-1] # just the biggest recrded sample number, so that we can concatenate easily. We will add the cumulative sum of this to each successive session.
            if setUpSessionLoop:
                shanksInUse = np.unique(spike_shankLabel) ### strictly speaking, if in any session in your set you have zero spikes in one shank for one session and any number in another session, then this will be incorrect... That feels ultra unlikely, but keep an ear out. Frankly if this causes an error you probably want to know about it.
                fullSessionSetSpikeLocations = dict()
                fullSessionSetTimes = dict()
                # fullSessionSetAmplitudes = dict() # probably don't actually need that, especially as I probably would want to use percentiles even if I use them.
                for ii,currentShank in enumerate(shanksInUse):
                    currentShankIndices = spike_shankLabel == currentShank
                    fullSessionSetSpikeLocations[currentShank] = spike_positions[currentShankIndices,:]
                    fullSessionSetTimes[currentShank] = spike_times[currentShankIndices]
                    # fullSessionSetAmplitudes[currentShank] = amplitudes[currentShankIndices]
                setUpSessionLoop = False
            else:
                for ii,currentShank in enumerate(shanksInUse):
                    currentShankIndices = spike_shankLabel == currentShank
                    fullSessionSetSpikeLocations[currentShank] = np.concatenate((fullSessionSetSpikeLocations[currentShank],spike_positions[currentShankIndices,:]),axis=0)
                    adjustedTimes = spike_times[currentShankIndices] + np.cumsum(largestSpikeSampleTimeEachSession[:i])[-1]
                    fullSessionSetTimes[currentShank] = np.concatenate((fullSessionSetTimes[currentShank],adjustedTimes),axis=0)

                    # fullSessionSetAmplitudes[currentShank] = np.concatenate((fullSessionSetAmplitudes[currentShank],amplitudes[currentShankIndices]),axis=0)
            pass
        pass
        if doSessionRasters:
            for ii,currentShank in enumerate(shanksInUse):
                sessionRasterPlots[currentShank] = dict()
                sessionRasterPlots[currentShank]['plot'],sessionRasterPlots[currentShank]['axis'] = plt.subplots()
                sessionRasterPlots[currentShank]['axis'].scatter(fullSessionSetTimes[currentShank] / 30000, fullSessionSetSpikeLocations[currentShank][:, 1], s=0.0005, c="black")
                sessionRasterPlots[currentShank]['axis'].invert_yaxis()
                sessionRasterPlots[currentShank]['plot'].show()
                pass



            # plt.figure()
            # shank_0_indices = spike_positions[:, 0] < 100
            # shank_1_indices = (spike_positions[:, 0] > 100)&(spike_positions[:, 0] < 350)
            # plt.scatter(spike_times[shank_1_indices] / 30000, spike_positions[shank_1_indices, 1], s=0.0005, c="black")
            # plt.gca().invert_yaxis()
            # plt.show()
            #
            # print(f'Processing {session_name}')
            # imecFolderList = list(session.glob('*' + 'imec' + '*'))
            # metaFileData,usedImro,NASprobeFolder = getCorrectRecordingForRegion(imecFolderList,sessionSetParams['channel_map_to_use'],localData=False)
            # if metaFileData == None:
            #     with open(errorFileName, "a") as f:
            #         print('no recording at ' + session_name + ' for ' + sessionSetParams['channel_map_to_use'], file=f) ### might want to print things at additional locations...
            #     continue # nothing to do here... ### TODO print to file. Probably today. Need to figure out everythin I want to print though.
            # local_probeFolder = all_VE_config.local_session_path / Path(*NASprobeFolder.parts[-2:]) ### this is a local version of the top-evel folder of the spikeglx session
            # local_probeFolder.mkdir(parents=True, exist_ok=True)
            # if copyAuxData:
            #     if (not any(list(local_probeFolder.parent.glob('*.bin')))) | overwriteAuxData:
            #         probable_ni_file = list(NASprobeFolder.parent.glob('*.bin'))[0] ### onebox might have to do this differently
            #         probable_ni_meta_file = list(NASprobeFolder.parent.glob('*.meta'))[0] ### onebox might have to do this differently
            #         target_ni_file = local_probeFolder.parent / probable_ni_file.name ### the place where we are sending it
            #         target_ni_meta_file = local_probeFolder.parent / probable_ni_meta_file.name
            #         shutil.copy(probable_ni_file,target_ni_file)
            #         shutil.copy(probable_ni_meta_file,target_ni_meta_file)
            #     pass
            # rawFolderName = local_probeFolder / Path('catgt_CorrectedRaw')
            # if outerLoopConfigs.doSaturationReplace:
            #     NASrecording = si.read_spikeglx(NASprobeFolder, stream_id=usedImro)
            #     try:
            #         windowsToSilenceArray = nullify_saturations(NASrecording, local_probeFolder=local_probeFolder) ### a numpy array with sample ranges that we want to exclude. Will be input into OverStrike later.
            #     except:
            #         with open(errorFileName, "a") as f:
            #             print('saturation detection failed for ' + session_name + ' for ' + sessionSetParams['channel_map_to_use'], file=f)
            #             continue
            # if (not any((list(rawFolderName.glob('*.bin'))))) | overwriteRaw: # if you don't have a raw or you say you want to overwrite it, we make a new raw.
            #     try:
            #         makeAndProcessRaw(NAS_session_path = all_VE_config.NAS_session_path,session_name=session_name,stream_id=usedImro,local_session_path=all_VE_config.local_session_path,badChannelList=sessionSetParams['badChannelList'],catgt_location=outerLoopConfigs.catgt_location,rawFolderName=rawFolderName,overwriteRaw = overwriteRaw,createCompressed = createCompressed)
            #         if outerLoopConfigs.doSaturationReplace: # requires saying you will overwrite. I hope that is natural.
            #             applyOverStrike(list(rawFolderName.glob('*.bin'))[0],outerLoopConfigs.OverStrike_location,windowsToSilenceArray)
            #     except:
            #         with open(errorFileName, "a") as f:
            #             print('preprocessed raw creation failed for ' + session_name + ' for ' + sessionSetParams['channel_map_to_use'], file=f)
            #             continue
            # if saveLFP:
            #     LFP_session_folder = LFP_sessionSet_folder / session_name
            #     LFP_session_folder.mkdir(parents=True, exist_ok=True)
            #     try:
            #         if (not any((list(LFP_session_folder.glob('*.bin'))))) | overwriteLFP:
            #             getLFP(NAS_session_path = all_VE_config.NAS_session_path,session_name=session_name,stream_id=usedImro,LFP_session_folder=LFP_session_folder,badChannelList=sessionSetParams['badChannelList'],catgt_location=outerLoopConfigs.catgt_location,overwriteLFP = overwriteLFP,doSaturationReplace = outerLoopConfigs.doSaturationReplace,windowsToSilenceArray=windowsToSilenceArray)
            #
            #     except:
            #         with open(errorFileName, "a") as f:
            #             print('LFP creation failed for ' + session_name + ' for ' + sessionSetParams['channel_map_to_use'], file=f)
            #
            #     pass
            # recording = si.read_spikeglx(rawFolderName, stream_id=usedImro) ### use si just to read the meta file.
            #
            #
            # ### preparing some things specifically for ks spikesorting
            #
            # settings = {'n_chan_bin': len(recording.channel_ids)+1} ### set settings dictionary, including required nchan_bin which should be correct as written.
            #
            # ### code up to chanMap.json being saved copied from spikeinterface.
            # groups = recording.get_channel_groups()
            # positions = np.array(recording.get_channel_locations())
            # if positions.shape[1] != 2:
            #     raise RuntimeError("3D 'location' are not supported. Set 2D locations instead.")
            #
            # n_chan = recording.get_num_channels()
            # chanMap = np.arange(n_chan)
            # xc = positions[:, 0]
            # yc = positions[:, 1]
            # unique_groups = set(groups)
            # group_map = {group: idx for idx, group in enumerate(unique_groups)}
            # kcoords = np.array([group_map[group] for group in groups], dtype=int)
            #
            # probe = {
            #     "chanMap": chanMap,
            #     "xc": xc,
            #     "yc": yc,
            #     "kcoords": kcoords,
            #     "n_chan": n_chan,
            # }
            # sorter_output_folder =  all_VE_config.output_folder / sessionSet[0] / sessionSet[1] / sessionSet[2] / session_name
            # probe_name = sorter_output_folder / Path("chanMap.json")  ### I still need to figure out how to automatically generate this file. When I do, I can save it into "inputs" somewhere.
            # if (not probe_name.is_file())|(overwriteChanMap):
            #     ks.io.save_probe(probe, str(sorter_output_folder / "chanMap.json"))
            #
            # ### do things related to the construction of a file which stores the recording information.
            # multirec_info['name'].append(session_name)
            # multirec_info['fs'].append(recording.get_sampling_frequency())
            # multirec_info['n_samples'].append(recording.get_num_samples())
            # multirec_info['duration'].append(recording.get_total_duration())
            #
            # multirec_info['start_time'].append(metaFileData['fileCreateTime']) ### it is very important that this metaFileData comes from the NAS! otherwise the fileCreateTime will be the time you catGTed it.
            #
            # multirec_info['multirec_start_sample'].append(0) ### this use to be integrated into a concatenation thing. That's why we bother with this.
            #
            # # multirec_info['multirec_stop_sample'].append(int(multirec_info['multirec_start_sample'][i] + (multirec_info['duration'][i].total_seconds() * multirec_info['fs'][i])))
            # multirec_info['multirec_stop_sample'].append(
            #     multirec_info['multirec_start_sample'][0] + (multirec_info['n_samples'][0]))
            # multirec_info['fullpath_as_string'].append(list(NASprobeFolder.glob('*.bin'))[0].__str__())
            # chan_dict = get_channelmap_names(session)  ### I should figure out how to get rid of this... Works fine for now.
            # chan_map_name = chan_dict[session_name + "_" + usedImro[:-3]]
            #
            # if chan_map_name == sessionSetParams['channel_map_to_use']:  # I did this for basically no reason. The reason is because it fits the expected format of Jules and because someday I may want to organize things by the probe map.
            #     if chan_map_name in dict_of_recordings:
            #         dict_of_recordings[chan_map_name].append(recording)
            #     else:
            #         dict_of_recordings[chan_map_name] = [recording]
            #
            # multirecordings = dict_of_recordings
            # if not all_VE_config.SurveyOverride: ### If we aren't doing SurveyOverride, then we want to keep track of the channel_map we intend to use so we can see if there is a mismatch later.
            #     multirecordingInput = multirecordings[sessionSetParams['channel_map_to_use']][0]
            #
            # if saveMultirecInfoFile:  # would like to seperate this from doing the preprocessing I think...
            #     df_rec = pd.DataFrame(multirec_info)
            #     df_rec.to_csv(sorter_output_folder / 'multirec_info.csv',
            #                   index=False)  # this is the earliest phy folder around and may be a problem... This saves the multirec info... Also this stuff might be better saved in spikesortingInput...
            #
            # ### note I am currently focusing cpu us
            # if doSpikeSorting&((overwriteSpikesorting)|(not any(list(sorter_output_folder.glob('params.py'))))): ### overwrite will currently not remove bombcell results and such from the folder. It should.
            #     try:
            #         ks.run_kilosort(settings, probe=None, probe_name=probe_name, filename=None,
            #              data_dir=rawFolderName, file_object=None, results_dir=sorter_output_folder,
            #              data_dtype=None, do_CAR=True, invert_sign=False, device=None,
            #              progress_bar=None, save_extra_vars=True, clear_cache=False,
            #              save_preprocessed_copy=False, bad_channels=None, shank_idx=None,
            #              verbose_console=True, verbose_log=True, torch_thread_lim=None)
            #     except:
            #         with open(errorFileName, "a") as f:
            #             print('spikesorting failed for ' + session_name + ' for ' + sessionSetParams['channel_map_to_use'], file=f)


if __name__ == '__main__':
    main()
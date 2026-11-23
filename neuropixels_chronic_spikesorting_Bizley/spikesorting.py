from pathlib import Path
import os
import numpy as np
import spikeinterface.full as si
import matplotlib.pyplot as plt
import spikeinterface.widgets as sw

from config import get_configs
import torch
import pickle
import shutil
import subprocess

def spikeglx_visualize(recording):
    #At the moment, a function designed to be break-pointed into.
    #Basically I just want a venue to look at data in ways I want.

    ### First: plot traces. Without any processing, they will be raw; you can do CMR or bandpass or phase shift or bad channel removal to improve things.
            # by the way, if you ever want to load traces into RAM, it's "get_traces". A method on the recording object.

    data_config, run_config = get_configs()
    selected_animal = next(iter(data_config["session_sets_to_run"]))
    selected_set = data_config["session_sets_to_run"][selected_animal][0]
    selected_regions = data_config["session_sets"][selected_animal][selected_set]["regions"]
    badChannelList = next(iter(selected_regions.values())).get("bad_channels", [])
    sample_rate = recording.get_sampling_frequency()
    legacy = run_config.get("legacy_spikeinterface", {})

    recording = si.phase_shift(recording)
    new_channel_ids = recording.channel_ids[~np.in1d(recording.channel_ids, recording.channel_ids[badChannelList])]
    recording = si.channelslice.ChannelSliceRecording(recording, new_channel_ids)
    satRange = legacy.get("saturation_view_s", [191, 192])
    satRangeSamples = [int(satRange[0] * sample_rate), int(satRange[1] * sample_rate)]
    spikeViewRegion = legacy.get("spike_view_s", [317.14, 317.15])
    spikeViewRegionSamples = [int(spikeViewRegion[0] * sample_rate), int(spikeViewRegion[1] * sample_rate)]
    testData = recording.get_traces(0,spikeViewRegionSamples[0],spikeViewRegionSamples[1])
    plt.imshow(testData.T, aspect='auto', clim=legacy.get("trace_color_limits", [-2000, 2000]))
    #recording = si.blank_staturation(recording, abs_threshold=1900, direction="both")
    #w_ts = sw.plot_timeseries(recording, time_range=satRange,clim=(-1955,1955))
    plt.show()
    recording = si.bandpass_filter(recording, freq_min=legacy.get("filter_min_hz", 300), freq_max=legacy.get("filter_max_hz", 6000))

    recording = si.common_reference(recording, reference='global', operator='median')

    w_ts2 = sw.plot_timeseries(recording, time_range=spikeViewRegion, clim=legacy.get("filtered_color_limits", [-20, 20]))
    plt.show()
    fakey = 1 + 1

def makeAndProcessRaw(NAS_session_path,session_name,stream_id,local_session_path,badChannelList,catgt_location,rawFolderName,overwriteRaw=None,createCompressed=None):
    data_config, run_config = get_configs()
    catgt = run_config["catgt"]
    sorting = run_config["sorting"]
    tools = run_config["tools"]
    if overwriteRaw is None:
        overwriteRaw = sorting.get("overwrite_raw", False)
    if createCompressed is None:
        createCompressed = sorting.get("create_compressed", False)

    # catgt_command = catgt.dry_run()  ### dry_run() generates a string for you. Look at it if you want to check.
    dir_string = '-dir=' + str(NAS_session_path) ### this should be all_VE_config.NAS_session_path, though I passed it as an argument instead of importing (good decision, later I would have regretted it). It specifies where the file should come from.
    run_string = '-run=' + session_name[:-3] ### this is the name of the session folder, without the _g#.
    prb_string = '-prb=' + stream_id[-4] ### the imec number of the probe.
    g_string = '-g=' + session_name[-1] ### the number next to g. Almost always 0, unless an error happened.
    dest_string = '-dest=' + str(local_session_path)
    CMR_string = catgt.get("common_reference", "-gblcar")
    filter_string = '-apfilter="{}"'.format(catgt.get("ap_filter", "butter,12,300,6000"))
    #gfix_string = '-gfix=' ### this is the catgt style saturation replacement. I probably won't use it because I prefer the one I wrote, to be honest.

    ## make -save string, which is a bit more involved... This is the thing that remove bad channels.
    js = str(catgt.get("save_stream_type", 2))
    out_streamid_num = stream_id[-4]  ### I will want this to be the same, perhaps you won't.
    channelsToKeep_listStyle = np.setdiff1d(np.arange(0, catgt.get("n_channels_total", 385)), np.asarray(badChannelList)).tolist()
    channelsToKeepString = str(channelsToKeep_listStyle)[1:-1].replace(" ", "") ### I list them all one by one, excluding the ones we said to exclude.
    save_string = '-save=' + js + ',' + prb_string[-1] + ',' + out_streamid_num + ',' + channelsToKeepString ### the "-save" argument wants you to put js, in-imec-num, out-imec-num first before all the channels you want to save.
    chnexcl_string = '-chnexcl={'+stream_id[-4]+';'+str(badChannelList)[1:-1].replace(" ", "")+'} ' ### we also need to say we are excluding channels, because they do seperate things. save_string is about which channels you save, but this one is about which channels are exlcuded from thing like the CAR.

    catgt_command = ' '.join([
        tools.get("catgt_batch_file", "runit.bat"), dir_string, run_string, g_string,
        f'-t={catgt.get("time_range", 0)}', catgt.get("ap_flag", "-ap"), prb_string,
        dest_string, catgt.get("probe_folder_flag", "-prb_fld"), chnexcl_string,
        save_string, CMR_string, filter_string,
    ])

    catgt_output_folder_path = local_session_path / Path('catgt_' + session_name)

    if catgt_output_folder_path.exists():
        shutil.rmtree(catgt_output_folder_path) ### if an error happens, this folder may already exist... I believe it makes things hang when you allow it...


    run_in_path = str(catgt_location) + '\\' + catgt_command
    subprocess.Popen(run_in_path).wait() ### this actually runs the command.

    pass

    ### then compress
    ## catgt will have saved everything you want in a folder that looks like your target, except with catgt_ in front. We will compress from that folder, then delete the catgt folder.

    ## load an si recording as an easy way to get the metadata.
    ### currently doesn't work... Will double check if I need it to work (as possibly I will still have this problem after I compress)
    #recording = si.read_spikeglx(catgt_output_folder_path, stream_id=stream_id) ### streamid will only work if you didn't change it... If you changed your output id, figure out how to make this work.
    found_SR = run_config["sampling"].get("np_fs", 30000)


    binFileFullpath = list(catgt_output_folder_path.glob('*.bin'))[0] ### only should work if there is one bin file, but there always should be in normal use.
    metaFileFullpath = list(catgt_output_folder_path.glob('*.meta'))[0]



    if createCompressed:
        mtscomp_command = '{} {} -n {} -s {} -d {}'.format(
            catgt.get("compressor_executable", "mtscomp"), binFileFullpath,
            len(channelsToKeep_listStyle), found_SR, catgt.get("compression_dtype", "int16"),
        )
        subprocess.Popen(mtscomp_command).wait()

    ### then delete the raw that existed before compression
        ### (let's not actually do this to start with, I want to compare them...)
    ### then move everything remaining in the folder
    if overwriteRaw&rawFolderName.exists():
        shutil.rmtree(rawFolderName) ### this looks scary but the data we just created is in a different folder. We delete whatever is already in the place we want to move that
    else:
        pass ### haven't written the skip yet because I am not sure how I want to do it. By passing, you'll get an error if you don't overwrite. I imagine what I would want to do is check that the file has actually been created properly before skipping (just checking if the folder exists wouldn't do that)
    os.rename(catgt_output_folder_path,rawFolderName)

def getLFP(NAS_session_path,session_name,stream_id,LFP_session_folder,badChannelList,catgt_location,overwriteLFP=None,doSaturationReplace=None,windowsToSilenceArray=None):
    ### based off of makeAndProcessRaw,  but entirely focused on LFP.
    data_config, run_config = get_configs()
    catgt = run_config["catgt"]
    sorting = run_config["sorting"]
    tools = run_config["tools"]
    if overwriteLFP is None:
        overwriteLFP = sorting.get("overwrite_lfp", False)
    if doSaturationReplace is None:
        doSaturationReplace = run_config["saturation"].get("replace", False)
    if windowsToSilenceArray is None:
        windowsToSilenceArray = np.empty((0, 2), dtype=int)
    downsampleFactor = catgt.get("lf_downsample_factor", 30)
    dir_string = '-dir=' + str(NAS_session_path) ### this should be all_VE_config.NAS_session_path, though I passed it as an argument instead of importing (good decision, later I would have regretted it). It specifies where the file should come from.
    run_string = '-run=' + session_name[:-3] ### this is the name of the session folder, without the _g#.
    prb_string = '-prb=' + stream_id[-4] ### the imec number of the probe.
    g_string = '-g=' + session_name[-1] ### the number next to g. Almost always 0, unless an error happened.
    dest_string = '-dest=' + str(LFP_session_folder)
    CMR_string = '' ### Pretty sure we don't want this for LFP
    # filter_string = '-lffilter="butter,12,0.5,500"' # filter stopbands based on spikeGLX defaults...
    filter_string = '-lffilter="{}"'.format(catgt.get("lf_filter", "butter,12,0,400"))
    # filter_string = '-lffilter="biquad,2,0.5,500"' # filter stopbands based on spikeGLX defaults...
    ap2lf_dwnsmp_string ='-ap2lf_dwnsmp=' + str(downsampleFactor)

    ## make -save string, which is a bit more involved... This is the thing that remove bad channels.
    js = str(catgt.get("save_stream_type", 2))
    out_streamid_num = stream_id[-4]  ### I will want this to be the same, perhaps you won't.
    channelsToKeep_listStyle = np.setdiff1d(np.arange(0, catgt.get("n_channels_total", 385)), np.asarray(badChannelList)).tolist()
    channelsToKeepString = str(channelsToKeep_listStyle)[1:-1].replace(" ", "") ### I list them all one by one, excluding the ones we said to exclude.
    save_string = '-save=' + js + ',' + prb_string[-1] + ',' + out_streamid_num + ',' + channelsToKeepString ### the "-save" argument wants you to put js, in-imec-num, out-imec-num first before all the channels you want to save.
    chnexcl_string = '-chnexcl={'+stream_id[-4]+';'+str(badChannelList)[1:-1].replace(" ", "")+'} ' ### we also need to say we are excluding channels, because they do seperate things. save_string is about which channels you save, but this one is about which channels are exlcuded from thing like the CAR.

    catgt_command = ' '.join([
        tools.get("catgt_batch_file", "runit.bat"), dir_string, run_string, g_string,
        f'-t={catgt.get("time_range", 0)}', catgt.get("lf_flag", "-lf"), prb_string,
        dest_string, catgt.get("probe_folder_flag", "-prb_fld"), chnexcl_string,
        save_string, CMR_string, filter_string, ap2lf_dwnsmp_string,
    ])

    catgt_output_folder_path = LFP_session_folder / Path('catgt_' + session_name) ### This is an autogenerated folder and I might even get rid of it...


    if catgt_output_folder_path.exists():
        shutil.rmtree(catgt_output_folder_path) ### if an error happens, this folder may already exist... I believe it makes things hang when you allow it...
    if overwriteLFP&LFP_session_folder.exists(): ### overwriteLFP should actually bypass this whole code so it shouldn't be necessary in here...
        shutil.rmtree(LFP_session_folder)
        LFP_session_folder.mkdir(parents=True, exist_ok=True)

    run_in_path = str(catgt_location) + '\\' + catgt_command
    subprocess.Popen(run_in_path).wait() ### this actually runs the command.

    pass

    ### then move everything remaining in the folder
    if LFP_session_folder.exists():
        files = os.listdir(catgt_output_folder_path)
        for file in files:
            file_name = os.path.join(catgt_output_folder_path, file)
            shutil.move(file_name, LFP_session_folder)
        shutil.rmtree(catgt_output_folder_path) ### this looks scary but the data we just created is in a different folder. We delete whatever is already in the place we want to move that

    rawFileName = list(LFP_session_folder.glob('*.bin'))[0]

    file_string = '-file=' + '"' + str(rawFileName) + '"'
    linefill_string = '-linefill' ### make a blank string if you don't want.
    if doSaturationReplace:
        for i, currentWindow in enumerate(windowsToSilenceArray):
            samps_string = '-samp="' + str(int(np.floor(currentWindow[0]/downsampleFactor))) + "," + str(int(np.ceil(currentWindow[1]/downsampleFactor))) + '"'
            overStrikeCommand = 'OverStrike ' + file_string + ' ' + samps_string + ' ' + linefill_string
            overstrike_command = '{} {} {} {}'.format(
                catgt.get("overstrike_executable", "OverStrike"), file_string, samps_string,
                '-linefill' if catgt.get("overstrike_linefill", True) else '',
            )
            run_in_path = str(tools["overstrike_location"]) + '\\' + overstrike_command
            subprocess.Popen(run_in_path).wait()
            pass

def preprocessing_for_drift_correction(recording,doRemoveBadChannels=None,local_probeFolder=None,badChannelList=None,doSaturationReplace=None,silenceOrNoiseReplace=None,floatDataTypeForDriftCorrection=False):
    # before drift correction the preprocessing you want is very minimal. phase correction is probably a good idea.
    # Bad channel removal can be too, but also it can be good to keep them so that you can see if your correction is working
    # (because they will be fully horizontal lines across sessions uncorrected, which you can compare to the corrected real spikes)
    # a thing that you certainly don't want to do is CAR or filter.
    # a thing that you NEED to do is make it float32 (or 64) because spikeinterface works terribly with int data.
    recording = si.phase_shift(recording) #mandatory for NP recordings because the channels are not sampled at the same time.

    data_config, run_config = get_configs()
    drift_config = run_config["drift_correction"]
    saturation_config = run_config["saturation"]
    if doRemoveBadChannels is None:
        doRemoveBadChannels = drift_config.get("remove_bad_channels", True)
    if badChannelList is None:
        selected_animal = next(iter(data_config["session_sets_to_run"]))
        selected_set = data_config["session_sets_to_run"][selected_animal][0]
        selected_regions = data_config["session_sets"][selected_animal][selected_set]["regions"]
        badChannelList = next(iter(selected_regions.values())).get("bad_channels", [])
    if doSaturationReplace is None:
        doSaturationReplace = saturation_config.get("replace", False)
    if silenceOrNoiseReplace is None:
        silenceOrNoiseReplace = drift_config.get("saturation_mode", saturation_config.get("mode", "zeros"))
    if doRemoveBadChannels: # next remove bad channels
        #bad_channel_ids, channel_labels = si.detect_bad_channels(recording) # this seems not as good as I need it to be... Totally misses all my bad channels. Maybe just need to change parameters...
        #recording = recording.remove_channels(bad_channel_ids) # I don't want to remove them here because I am concatenating. Remove later
        new_channel_ids = recording.channel_ids[~np.in1d(recording.channel_ids, recording.channel_ids[badChannelList])]
        recording = si.channelslice.ChannelSliceRecording(recording, new_channel_ids)

    if doSaturationReplace:
        windowsToSilenceArray = nullify_saturations(recording, local_probeFolder=local_probeFolder) # find saturations before any further processing. Only finds, doesn't correct.

    if floatDataTypeForDriftCorrection:
        if not (recording.dtype == 'float32'):
            recording = recording.astype(dtype="float32")
    if doSaturationReplace:
        if windowsToSilenceArray.any():  # code breaks when no saturation
            # if global_configs.useBugFixedSilencePeriods:
            #     recording = silence_periods_file.silence_periods(recording, windowsToSilenceArray, mode=silenceOrNoiseReplace)
            # else:
            recording = si.silence_periods(recording, windowsToSilenceArray, mode=silenceOrNoiseReplace) # Doing this before whitening might cause issues... I need to understand how whitening works better.

    return recording


def spikeglx_preprocessing(recording,local_probeFolder=None,doSaturationReplace=None,silenceOrNoiseReplace=None,floatDataTypeForDriftCorrection=False):
    _, run_config = get_configs()
    drift_config = run_config["drift_correction"]
    saturation_config = run_config["saturation"]
    if doSaturationReplace is None:
        doSaturationReplace = saturation_config.get("replace", False)
    if silenceOrNoiseReplace is None:
        silenceOrNoiseReplace = drift_config.get("saturation_mode", saturation_config.get("mode", "zeros"))


    # if doSaturationReplace: ### should consider trying to get this into the local raw via catgt instead of doing it here?
    #     windowsToSilenceArray = nullify_saturations(recording, local_probeFolder=local_probeFolder) # find saturations before any further processing. Only finds, doesn't correct.

    if floatDataTypeForDriftCorrection:
        if not (recording.dtype == 'float32'):
            recording = recording.astype(dtype="float32")
    # if doSaturationReplace:
    #     if windowsToSilenceArray.any():  # code breaks when no saturation
    #         if global_configs.useBugFixedSilencePeriods:
    #             recording = silence_periods_file.silence_periods(recording, windowsToSilenceArray, mode=silenceOrNoiseReplace)
    #         else:
    #             recording = si.silence_periods(recording, windowsToSilenceArray, mode=silenceOrNoiseReplace) # Doing this before whitening might cause issues... I need to understand how whitening works better.
            # recording = recording.astype('int16') ### reportedly converting back in this way is dangerous, and I should look into it. I need to do it for harddrive space, but otherwise I shouldn't bother.
        # spikeglx_visualize(recording)
    return recording


def spikeglx_preprocessing_historical(recording,doRemoveBadChannels =1,skipStuffThatKSGUIDoes = 0,local_probeFolder=None,badChannelList=[],bin_s_sessionCat=6.0,skipStuffThatMightBeInPresavedRaw=False,doSaturationReplace=False,silenceOrNoiseReplace='noise',floatDataTypeForDriftCorrection=False):
    if not skipStuffThatMightBeInPresavedRaw:
        recording = si.phase_shift(recording) #mandatory for NP recordings because the channels are not sampled at the same time.

        if doRemoveBadChannels: # next remove bad channels
            #bad_channel_ids, channel_labels = si.detect_bad_channels(recording) # this seems not as good as I need it to be... Totally misses all my bad channels. Maybe just need to change parameters...
            #recording = recording.remove_channels(bad_channel_ids) # I don't want to remove them here because I am concatenating. Remove later
            new_channel_ids = recording.channel_ids[~np.in1d(recording.channel_ids, recording.channel_ids[badChannelList])]
            recording = si.channelslice.ChannelSliceRecording(recording, new_channel_ids)


    if doSaturationReplace: ### moved to after RemoveBadChannels without checking the consequences, but thinking them through, it should be fine.
        windowsToSilenceArray = nullify_saturations(recording, local_probeFolder=local_probeFolder) # find saturations before any further processing. Only finds, doesn't correct.

    ### at roughly this spot, I should save raw data locally. Need to consider whether I also want any other preprocessing, but I don't think so.

    if not skipStuffThatKSGUIDoes: # I actually might move this to after the concatenation?
        recording = si.bandpass_filter(recording, freq_min=300, freq_max=6000) # filter each
        if False: # here I do peak detection and localization early because it is quicker with one session... I do this to test a processing method.
            ### make a subselection of the recording so you can do this faster
            low_bound_temp = int(round(960*recording.sampling_frequency))
            high_bound_temp = int(round(975*recording.sampling_frequency))
            recording_preCMR = recording.frame_slice(low_bound_temp,high_bound_temp)
            recording_CMR = si.common_reference(recording_preCMR, reference='global', operator='median')
            si.highpass_spatial_filter(recording)
            #recording_localRef = si.common_reference(recording_preCMR, reference='local', operator='median',local_radius=(60,200)) ### I don't know if local radius is in units of channels or microns.
            recording_localRef = si.highpass_spatial_filter(recording_preCMR)
            desired_n_jobs = 16
            from spikeinterface.sortingcomponents.peak_detection import detect_peaks
            from spikeinterface.sortingcomponents.peak_selection import select_peaks
            from spikeinterface.sortingcomponents.peak_localization import localize_peaks
            from spikeinterface.sortingcomponents.motion import estimate_motion, interpolate_motion

            job_kwargs = dict(chunk_duration='1s', n_jobs=desired_n_jobs, progress_bar=True)  # ,
            ### KS defaults, which I am using
            peaks_CMR = detect_peaks(recording=recording_CMR, method="locally_exclusive", peak_sign="neg",
                                 detect_threshold=8.0, exclude_sweep_ms=0.1, radius_um=50,
                                 **job_kwargs)  # seems like there isn't a unique peak detection algorithm for ks? I don't actually think that's true, I believe they use templates... But with SI, maybe not. I should maybe just look into the high level function and see what is done
            peak_locations_CMR = localize_peaks(recording=recording_CMR, peaks=peaks_CMR, method="grid_convolution",
                                            weight_method={"mode": "gaussian_2d",
                                                           "sigma_list_um": np.linspace(5, 25, 5)}, **job_kwargs)
            peaks_localRef = detect_peaks(recording=recording_localRef, method="locally_exclusive", peak_sign="neg",
                                 detect_threshold=8.0, exclude_sweep_ms=0.1, radius_um=50,
                                 **job_kwargs)  # seems like there isn't a unique peak detection algorithm for ks? I don't actually think that's true, I believe they use templates... But with SI, maybe not. I should maybe just look into the high level function and see what is done
            peak_locations_localRef = localize_peaks(recording=recording_localRef, peaks=peaks_localRef, method="grid_convolution",
                                            weight_method={"mode": "gaussian_2d",
                                                           "sigma_list_um": np.linspace(5, 25, 5)}, **job_kwargs)
            if False: # here I do plotting

                import matplotlib
                import matplotlib.pyplot as plt
                matplotlib.use('TkAgg')
                scatterArray_CMR = np.zeros((len(peak_locations_CMR), 2))
                for iiii in range(0, len(peak_locations_CMR)):
                    scatterArray_CMR[iiii, 0] = peaks_CMR[iiii][0]
                    scatterArray_CMR[iiii, 1] = peak_locations_CMR[iiii][1]
                scatterArray_localRef = np.zeros((len(peak_locations_localRef), 2))
                for iiii in range(0, len(peak_locations_localRef)):
                    scatterArray_localRef[iiii, 0] = peaks_localRef[iiii][0]
                    scatterArray_localRef[iiii, 1] = peak_locations_localRef[iiii][1]
                plt.figure()
                plt.scatter([1, 2, 3], [2, 4, 3])  # for some reason this helps the other figures load...
                plt.show()
                plt.figure()
                plt.scatter(scatterArray_CMR[:, 0] / recording.sampling_frequency, scatterArray_CMR[:, 1], s=0.01, c="black")
                plt.gca().invert_yaxis()
                plt.show()
                plt.figure()
                plt.scatter(scatterArray_localRef[:, 0] / recording.sampling_frequency, scatterArray_localRef[:, 1], s=0.01, c="black")
                plt.gca().invert_yaxis()
                plt.show()
                breakPointSpot = "here"
        recording = si.common_reference(recording, reference='global',operator='median')  # common reference, I think it's much better to do this after removing bad channels. IBL does a spatial highpass with very low cutoff, butI will keep median for now.
    if floatDataTypeForDriftCorrection:
        if not (recording.dtype == 'float32'):
            recording = recording.astype(dtype="float32")
    if doSaturationReplace:
        if windowsToSilenceArray.any():  # code breaks when no saturation
            recording = si.silence_periods(recording, windowsToSilenceArray, mode=silenceOrNoiseReplace)
            # recording = recording.astype('int16') ### reportedly converting back in this way is dangerous, and I should look into it. I need to do it for harddrive space, but otherwise I shouldn't bother.
        # spikeglx_visualize(recording)
    return recording

def nullify_saturations(recording,surrondingToAlsoNullify=None,local_probeFolder=None,beginningAndEndToCutOff=None,loadSatsFromFile=None):
    # The idea behind this function is to:
    #     - Detect saturated periods like si.blank_saturation
    #           (in fact, this program does this channel by channel I think. I will actually want to apply my threshold on the
    #           average of all channels, which will greatly help with avoiding false positives)
    #     -  mark these times for all later analyses to ignore
    #     -  save and load those times so that silence_periods can later be used to target them
    #
    # The idea is that it because it is impossible to recover spikes in saturated periods, we simply want to
    # prevent them from annoying us in our processing steps. I may write additional "nullify" functions
    # in the future should other excludable periods turn up.

    # it's important to run this functionon the raw data, but I prefer to apply the silence_periods function at the end'
    #    'of the processing chain.

    # additionally: this function is useful for nullifying *any* sort of problem. I therefore also include functionality
    # to notice particular sessions and silence particular ranges for them.

    # Arguments:
    #
    #     -recording (the si recording)
    #     -surroundingToAlsoNullify (in ms. So input 10 here and 10 ms on each end of each null period will also be null.
    #                The intention here is to deal with the up and down ramps involved in saturation conservatively.


    data_config, run_config = get_configs()
    saturation = run_config["saturation"]
    if surrondingToAlsoNullify is None:
        surrondingToAlsoNullify = saturation.get("surrounding_ms", 2)
    if beginningAndEndToCutOff is None:
        beginningAndEndToCutOff = saturation.get("begin_end_cutoff_s", [0, 0])
    if loadSatsFromFile is None:
        loadSatsFromFile = saturation.get("load_from_file", True)
    local_probeFolder.mkdir(parents=True, exist_ok=True)
    fileNameSat = local_probeFolder / Path("saturatedZones.csv")
    if (fileNameSat.is_file())&loadSatsFromFile:
        windowsToSilenceArray = np.loadtxt(fileNameSat)
        if windowsToSilenceArray.size == 0:
            windowsToSilenceArray = np.zeros((0, 2))
        if (not (windowsToSilenceArray.ndim == 2))&(windowsToSilenceArray.shape[0]==2):
            windowsToSilenceArray = windowsToSilenceArray.reshape(1, 2)
    else:
        nullSat_init_args = (
            recording, surrondingToAlsoNullify, saturation.get("abs_min", -1900),
            saturation.get("abs_max", 1900), saturation.get("fraction_channels", 0.1),
        )
        nullSat = si.ChunkRecordingExecutor(
            recording, func=nullify_saturations_loopImplementation,
            init_func=nullify_saturations_init_func, init_args=nullSat_init_args,
            n_jobs=saturation.get("n_jobs", 1),
            chunk_size=saturation.get("chunk_size", 30000),
            handle_returns=True, progress_bar=saturation.get("progress_bar", True),
        )
        windowsToSilence = nullSat.run()
        windowsToSilenceArray = np.zeros((0,2))
        for chunkSet in windowsToSilence: # yes it's silly to do this afterward instead of during, but it's really not a big deal. Default function outputs list.
            windowsToSilenceArray = np.concatenate((windowsToSilenceArray,chunkSet))
        np.savetxt(fileNameSat, windowsToSilenceArray)
    if any(beginningAndEndToCutOff):
        secondsToCutBeginning = beginningAndEndToCutOff[0]
        secondsToCutEnd = beginningAndEndToCutOff[1]
        windowsToSilenceArray = np.concatenate(([[0,int(recording.sampling_frequency*secondsToCutBeginning)]],windowsToSilenceArray))
        windowsToSilenceArray = np.concatenate((windowsToSilenceArray,  [[(recording.get_num_frames()-int(recording.sampling_frequency*secondsToCutEnd)),recording.get_num_frames()]]))
    return windowsToSilenceArray
def applyOverStrike(rawFileName,OverStrike_location,windowsToSilenceArray):
    run_config = get_configs()[1]
    catgt = run_config["catgt"]
    file_string = '-file=' + '"' + str(rawFileName) + '"'
    linefill_string = '-linefill' if catgt.get("overstrike_linefill", True) else ''
    for i, currentWindow in enumerate(windowsToSilenceArray):
        samps_string = '-samp="' + str(int(currentWindow[0])) + "," + str(int(currentWindow[1])) + '"'
        overStrikeCommand = catgt.get("overstrike_executable", "OverStrike") + ' ' + file_string + ' ' + samps_string + ' ' + linefill_string
        run_in_path = str(OverStrike_location) + '\\' + overStrikeCommand
        subprocess.Popen(run_in_path).wait()
        pass

def nullify_saturations_init_func(recording,surrondingToAlsoNullify,abs_sat_min=-1900,abs_sat_max=1900,fraction_channels=0.1):
    # It seems like the only place you can put any information about the recording or w/e is here.
    worker_ctx = {}
    worker_ctx["recording"] = recording
    worker_ctx["surrondingToAlsoNullify_samples"] = round(((recording.sampling_frequency))*(surrondingToAlsoNullify/1000))
    worker_ctx["kernelForSurroundingConvolution"] = np.ones((worker_ctx["surrondingToAlsoNullify_samples"]*2 + 1))
    worker_ctx["abs_sat_min"] = abs_sat_min
    worker_ctx["abs_sat_max"] = abs_sat_max
    worker_ctx["fractionChannelsSatToEnforceExclusion"] = fraction_channels
    return worker_ctx
def nullify_saturations_loopImplementation(segment_index, frame_start, frame_stop, worker_ctx):
    # function to pass to ChunkRecordingExecutor.
    working_chunk = worker_ctx["recording"].get_traces(segment_index, frame_start, frame_stop)
    overMax = working_chunk > worker_ctx["abs_sat_max"]
    underMin = working_chunk < worker_ctx["abs_sat_min"]
    fractionChannelsOverMaxPerTime = np.sum(overMax.astype(int),axis=1)/working_chunk.shape[1]
    fractionChannelsUnderMinPerTime = np.sum(underMin.astype(int),axis=1)/working_chunk.shape[1]
    if any(fractionChannelsUnderMinPerTime > worker_ctx["fractionChannelsSatToEnforceExclusion"]) | any(fractionChannelsOverMaxPerTime > worker_ctx["fractionChannelsSatToEnforceExclusion"]):

        timeTrace = ((fractionChannelsUnderMinPerTime > worker_ctx["fractionChannelsSatToEnforceExclusion"]) | (fractionChannelsOverMaxPerTime > worker_ctx["fractionChannelsSatToEnforceExclusion"])).astype(int)
        extendedTimeTrace = np.convolve(timeTrace, worker_ctx["kernelForSurroundingConvolution"],mode="same")
        extendedTimeTrace = (extendedTimeTrace.astype(bool)).astype(int)
        difftrace = np.diff(extendedTimeTrace)
        ups = np.where(difftrace>0)[0] + frame_start
        downs = np.where(difftrace<0)[0] + frame_start

        # some visualization code for debugging. Comment out most of the time.

        # satRange = [frame_start / worker_ctx["recording"].sampling_frequency,
        #             frame_stop / worker_ctx["recording"].sampling_frequency]
        # plt.plot(extendedTimeTrace)
        # w_ts = sw.plot_timeseries(worker_ctx["recording"], time_range=satRange, clim=(-1955, 1955))
        # plt.show()
        #
        # hhhhh=1+1

        if extendedTimeTrace[0] & extendedTimeTrace[-1]:
            if (any(ups)|any(downs)):
                # then both the front and the back are saturated.
                rangesToSilence = np.zeros((len(ups) + 1, 2))
                rangesToSilence[0] = [frame_start, downs[0]]
                for i in range(0,len(ups)):
                    if not i== len(ups)-1:
                        rangesToSilence[i+1] = [ups[i],downs[i+1]]
                    else:
                        rangesToSilence[i+1] = [ups[i], frame_stop]
            else:
                rangesToSilence = np.zeros((1, 2))
                rangesToSilence[0] = [frame_start, frame_stop]
        elif extendedTimeTrace[0]:
            #then we need to connect a range later.
            rangesToSilence = np.zeros((len(ups) + 1, 2))
            rangesToSilence[0] = [frame_start, downs[0]]
            for i in range(0,len(ups)):
                rangesToSilence[i+1] = [ups[i],downs[i+1]]
        elif extendedTimeTrace[-1]:
            #then we need to connect a range later.
            rangesToSilence = np.zeros((len(ups),2))
            for i in range(0,len(ups)):
                if not i == len(ups)-1:
                    rangesToSilence[i] = [ups[i],downs[i]]
                else:
                    rangesToSilence[i] = [ups[i], frame_stop]
        elif not len(ups) == len(downs):
            raise "unequal number of raises and lowers, but not because of one of them starting at the edge"
        elif len(ups) | len(downs):
            rangesToSilence = np.zeros((len(ups), 2))
            for i in range(0,len(ups)):
                rangesToSilence[i] = [ups[i],downs[i]]
            bluhah = 1
        else:
            raise "hit something weird"
    else:
        rangesToSilence = np.zeros((0, 2))
    for ranges in rangesToSilence:
        if ranges[0] > ranges[1]:
            raise "see what is up"
    return rangesToSilence

def size_pad_to_add(recording, bin_s=None):
    """ Function computing the size of the pad to add to a recording in to make it an integer multiple of bin_s
    Parameters:
        recording: recording object (cf spikeinterface doc)
        bin_s: int (in seconds)
    Returns:
        pad_size: int, size of the pad to add to the recording (in number of samples)
        pad_bounds: list, future boundaries of the pad once it's added to be able to replace it with noise
        """
    if bin_s is None:
        bin_s = get_configs()[1].get("legacy_spikeinterface", {}).get("bin_s", 6.0)
    sampling_freq =recording.get_sampling_frequency()
    bin_samples = int(np.round(bin_s* sampling_freq))
    size_recording = recording.get_num_samples() -1
    pad_size = bin_samples - (size_recording % bin_samples)
    pad_bounds= [size_recording, size_recording + pad_size]
    return pad_size, pad_bounds

def spikesorting_pipeline(recording, output_folder, sorter=None,concatenated=False):
    _, run_config = get_configs()
    legacy = run_config.get("legacy_spikeinterface", {})
    if sorter is None:
        sorter = legacy.get("sorter", "kilosort4")
    working_directory = Path(output_folder) / 'tempDir'
    # if (working_directory / 'binary.json').exists():
    #     recording = si.load_extractor(working_directory)
    # else:
    # job_kwargs = dict(n_jobs=-1, chunk_duration='1s', progress_bar=True)
    # recording = recording.save(folder = working_directory, format='binary', **job_kwargs)
    # pickleName = 'preSorting.pkl'
    # pickleJar = dict(recording = recording)
    # with open(picklePath / pickleName, 'wb') as file:
    #     pickle.dump(pickleJar, file)
    if sorter != 'kilosort4':
        raise ValueError('Unsupported Spikesorter.')
    sorter_kwargs = dict(legacy.get("sorter_run_kwargs", {}))
    sorter_kwargs.setdefault("verbose", True)
    sorting = si.run_sorter(
        sorter_name=sorter,
        recording=recording,
        folder=working_directory / f'{sorter}_output',
        **sorter_kwargs,
    )
    return sorting


def spikesorting_postprocessing(sorting, output_folder):
    _, run_config = get_configs()
    legacy = run_config.get("legacy_spikeinterface", {})

    ### It has been a long time since I looked at this and it is basically irrelevant to the unitmatch pipeline. So, watch out.



    output_folder.mkdir(exist_ok=True, parents=True)
    rec = sorting._recording # grab the recording object
    outDir = output_folder / sorting.name
    censored_period_ms = legacy.get("censored_period_ms", 0.3)
    si.set_global_job_kwargs(n_jobs=legacy.get("n_jobs", 15))
    jobs_kwargs = dict(chunk_duration=legacy.get("chunk_duration", "1s"), n_jobs=legacy.get("n_jobs", 15), progress_bar=True)
    sorting = si.remove_duplicated_spikes(sorting, censored_period_ms=censored_period_ms)
    sorting = si.remove_excess_spikes(sorting, rec)

    if (outDir / 'sortings_folder').exists():
        # we = si.load_waveforms(
        #     outDir / 'sortings_folder',
        #     sorting=sorting,
        #     with_recording=True,
        # )
        we = si.load_sorting_analyzer(outDir / 'sortings_folder', load_extensions=True, format="auto", backend_options=None)
    else:
        # we = si.create_sorting_analyzer() # need to figure this out later.
        # check https://spikeinterface.readthedocs.io/en/latest/tutorials/waveform_extractor_to_sorting_analyzer.html
        # The reason for the update was to not have to extract waveforms for things that didn't need them.
        #
        we = si.create_sorting_analyzer(recording=rec, sorting=sorting, folder=outDir / 'sortings_folder',
                                        format="binary_folder",
                                        sparse=legacy.get("create_sparse_analyzer", True)
                                        )

        ### I've basically translated the compatibility code below.

        # other_kwargs, new_job_qwargs = split_job_kwargs(**jobs_kwargs)

    if not we.has_extension("random_spikes"):
        we.compute("random_spikes",max_spikes_per_unit=legacy.get("max_spikes_per_unit", 300))
        print('Marker 3')
    if not we.has_extension("waveforms"):
        we.compute("waveforms",ms_before=legacy.get("waveforms_ms_before", 2.0),ms_after=legacy.get("waveforms_ms_after", 3.0))
        print('Marker 4')
    # if not we.has_extension("templates"):
    we.compute("templates")  ### used for downstream analysis and are useful to look at to see if your results make sense.
    print('Marker 5')
    if not we.has_extension("noise_levels"):
        we.compute("noise_levels") ### I worry how useful this would be for my concatenated data...
        print('Marker 6')
    # if not we.has_extension("spike_amplitudes"):
    print('Marker 6.5')
    we.compute("spike_amplitudes")
    print('Marker 7')
    # if not we.has_extension("template_similarity"):
    we.compute("template_similarity")
    print('Marker 8')
    if not (outDir / 'report').exists():
        si.export_to_phy(we, outDir / 'phy_folder',
                         verbose=True,
                         compute_pc_features=legacy.get("compute_pc_features", False),
                         copy_binary=False,
                         remove_if_exists=True,
                         **jobs_kwargs,
                         )

        si.export_report(we, outDir / 'report',
                         format='png',
                         force_computation=True,
                         **jobs_kwargs,
                         )
        # metrics = si.compute_quality_metrics( #### this seems defunct. Seems like I want something related to "ComputeQualityMetrics" here.
        #     we,
        #     n_jobs=jobs_kwargs['n_jobs'],
        #     verbose=True,
        # )

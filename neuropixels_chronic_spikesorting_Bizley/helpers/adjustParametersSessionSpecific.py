### this function is designed to adjust the parameters from the defaults depending on who you are and what session it is
## the basic idea is that you just overwrite whatever was previously there.

## when I first am making this, I don't know how I will end up using it. It has easy functionality to handle specific
## whole session sets (just put those parameters into SpecifySessionSetParameters.py)
## The name of the current session is also transferred, so you can do session specific stuff like that.
## in the future I might want to do something algorithmic based on some property of the session... It is difficult
## to predict a-priori what those factors might be. The hope is that they can just be added into sessionSetParams


import neuropixels_chronic_spikesorting_Bizley.all_VE_config as all_VE_config


def adjustParametersSessionSpecific(param,sessionSetParams):
    if all_VE_config.projectLabel == 'listOfParametersIThinkAreWorthAdjusting':
        pass ### these will all be commented-ut copy pastes, meant for reference not for use.
        # plottingParameters = True
        # if plottingParameters:
        #     "plotDetails": True,  # show step-by-step plots
        #     "plotGlobal": True,  # Summary plots of quality metrics
        #     "savePlots": True,  # If True will save plots to disk...
        #     "plotsSaveDir": None,  # Directory to save plots to (if None, saves to kilosort_path/bombcell_plots/)
        # parametersWorthAdjusting = True
        # if parametersWorthAdjusting:
        #     "duplicateSpikeWindow_s": 0.000034 ### might be worth increasing this window to remove more duplicates?
        #     "joblib_n_jobs": -1 ### -1 for all cores.
        #     ## Refractory period parameters ### not certainany of these will actually be worth looking at yet, but they have my interest
        #     # New recommended parameters:
        #     "rpv_method": "ibl_sliding",  # Method for RPV computation: 'hill', 'llobet', or 'ibl_sliding'
        #     "tauR_values": np.arange(4, 41) * 0.25 / 1000,  # Refractory period values to test (s):
        #                                         # 1 to 10 ms in 0.25 ms steps. Shorter values let
        #                                         # units hold off a fail by having a barely testable
        #                                         # sub-ms refractory period. For 'hill'/'llobet' a
        #                                         # single value, e.g. np.array([0.002])
        #     "keepUncertainRPVUnits": False,  # For ibl_sliding: units with too few spikes to confirm
        #                                      # they are below maxRPVviolations, and no evidence they
        #                                      # are above it (RPV_status == 0), pass the RPV criterion
        #                                      # if True, and are classified as MUA if False
        #     "tauC": 0.1 / 1000,  # Censored period time (s): spike pairs closer than this are
        #                          # ignored. Set below to Kilosort 4's duplicate spike window,
        #                          # and raised to duplicateSpikeWindow_s at run time if
        #                          # removeDuplicateSpikes is True (see effective_tauC)
        #     "contamination_values": None,  # For ibl_sliding: contamination values to test
        #                                    # If None, uses np.arange(0.5, 35.5, 0.5) / 100
        #     "confidence_threshold": 0.9,  # For ibl_sliding: confidence threshold for contamination estimate
        #     "tauR_reject": 0.5 / 1000,  # For ibl_sliding: refractory periods <= this (s) are not tested
        #
        #     ##
        #
        #     "maxNPeaks": 2,  # maximum number of peaks
        #     "maxNTroughs": 1,
        #     "minSpatialDecaySlopeExp": 0.0037,
        #     "maxWvBaselineFraction": 0.36,  ### 0.25 default (though new default is 0.3 actually). I put it to 0.36 to be more permissive because a lot of good units were getting excluded.  # maximum absolute value in waveform baseline should not exceed this fraction of the waveforms's absolute peak
        #
        #     Most of the other waveform ones are of interest honestly, but these were the ons I have already adjusted.
        #
        #
        #     "minAmplitude": 10, ### default 40 apparently.  # in uV
        #     "maxRPVviolations": 0.3, ### default 0.1 apparently. # max fraction of refractory period violations
        #     "maxPercSpikesMissing": 20,  # max percentage of missing spikes
        #     "minNumSpikes": 300,  ### changed from 500 because my sessions are short... # minimum number of total spikes recorded

        pass
    if all_VE_config.projectLabel == 'before2027Defaults':
        param["computeTimeChunks"]= True # no clue why this was changed from default, either by us or bombcell. But it used to be true.
        param['deltaTimeChunk'] = 120
        param['maxNTroughs'] = 1
        param['minSpatialDecaySlopeExp'] = 0.0037 ### changed from 0.005... New default is actually 0.01... It actually seems to have been 0.006 based on the graph...   # in a.u / um
        param['maxWvBaselineFraction'] = 0.36
        param['minAmplitude'] = 10
        param['maxRPVviolations'] = 0.3
        param['minNumSpikes'] = 300


        pass
    if all_VE_config.projectLabel == 'Jeffrey':
        param["computeTimeChunks"]= True # no clue why this was changed from default, either by us or bombcell. But it used to be true.
        param['deltaTimeChunk'] = 120
        param['maxNTroughs'] = 1
        param['minSpatialDecaySlopeExp'] = 0.0037 ### changed from 0.005... New default is actually 0.01... It actually seems to have been 0.006 based on the graph...   # in a.u / um
        param['maxWvBaselineFraction'] = 0.36
        param['minAmplitude'] = 10
        param['maxRPVviolations'] = 0.3
        param['minNumSpikes'] = 300
        pass
    pass
    return param
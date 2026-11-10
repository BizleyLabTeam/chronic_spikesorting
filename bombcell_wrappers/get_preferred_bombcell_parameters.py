### parameters first recommended by UnitMatch then altered by Louise and Jeff, leading to spikes we liked.


import numpy as np
from pathlib import Path

from bombcell.loading_utils import get_gain_spikeglx


def get_preferred_bombcell_parameters(
    kilosort_path,
    raw_file=None,
    kilosort_version=4,
    meta_file=None,
    gain_to_uV=None,
):
    """
    Creates the parameters dictionary

    Parameters
    ----------
    kilosort_path : str
        The path to the KiloSort directory
    raw_file : str, optional
        The path to the raw data, by default None
    kilosort_version : int, optional
        Changes parameters based on if KS4 or earlier version were used, by default None
    ephys_meta_dir : str, optional
        The path to the meta file of the raw recording, by default None
    gain_to_uV : float, optional
        The gain to micro volts if needed to give manually, by default None

    Returns
    -------
    param : dictionary
        The full param dictionary need to run BombCell
    """
    param = {
        # Quality metric computation and display parameters
        ## general
        "plotDetails": True,  # show step-by-step plots
        "plotGlobal": True,  # Summary plots of quality metrics
        "savePlots": True,  # If True will save plots to disk...
        "plotsSaveDir": None,  # Directory to save plots to (if None, saves to kilosort_path/bombcell_plots/)
        "verbose": True,  # If True will update user on progress
        "reextractRaw": True,  # If True will re extract raw waveforms
        "saveAsTSV": True,  # save outputs as a .tsv file, useful for using phy after bombcell
        "unit_type_for_phy": True,  # save a unit_type .tsv file for phy
        "ephysKilosortPath": str(kilosort_path),  # path to the KiloSort directory

        ## Duplicate spike parameters
        "removeDuplicateSpikes": True,
        "duplicateSpikeWindow_s": 0.000034,  # in seconds ### default 0.000034. This means slightly more than one sample.
        "saveSpikes_withoutDuplicates": True,
        "recomputeDuplicateSpikes": True, ### Just keep this as true, it doesn't take very long.

        ## Excess spike parameters. Custom added, written by Louise.
        "removeExcessSpikes": True,
        "recomputeExcessSpikes": True, ### Just keep this as true, it doesn't take very long. The validity also depends on what recomputeDuplicateSpikes does, so it is more reliable to just run them in a chain.
        "saveSpikes_withoutExcess": True,

        ## Amplitude / raw waveform parameters
        "detrendWaveform": True,  # If True will linearly de-trend the average waveforms for BombCell
        "detrendForUnitMatch": False,  # If True will linearly de-trend raw waveforms saved for UnitMatch ### supposed to be false because UnitMatch does it for you.
        "nRawSpikesToExtract": 1000,  # Number of raw spikes per unit. Normal default 100, UnitMatch default 1000.
        "decompress_data": False,  # whether to decompress .cbin data
        "extractRaw": True,
        "joblib_n_jobs": -1,  # workers used to extract raw waveforms in parallel.
        # -1 is one per core; lower it if extraction runs out of memory
        "joblib_backend_preference": "processes",  # 'processes' or 'threads'. joblib's
        # process pool is the faster option, but cannot start on some setups (cluster
        # schedulers, containers with a small /dev/shm, some notebook environments) -
        # use 'threads' there

        "probeType": 2,  # If you are using spikeGLX and your meta files does not ### a great reason to use meta files
        # contain information on your probe type specify it here
        # '1' for 1.0 (3Bs) and '2' for 2.0 (single or 4-shanks)
        ## Refractory period parameters
        # New recommended parameters:
        "rpv_method": "ibl_sliding",  # Method for RPV computation: 'hill', 'llobet', or 'ibl_sliding'
        "tauR_values": np.arange(4, 41) * 0.25 / 1000,  # Refractory period values to test (s):
                                            # 1 to 10 ms in 0.25 ms steps. Shorter values let
                                            # units hold off a fail by having a barely testable
                                            # sub-ms refractory period. For 'hill'/'llobet' a
                                            # single value, e.g. np.array([0.002])
        "keepUncertainRPVUnits": False,  # For ibl_sliding: units with too few spikes to confirm
                                         # they are below maxRPVviolations, and no evidence they
                                         # are above it (RPV_status == 0), pass the RPV criterion
                                         # if True, and are classified as MUA if False
        "tauC": 0.1 / 1000,  # Censored period time (s): spike pairs closer than this are
                             # ignored. Set below to Kilosort 4's duplicate spike window,
                             # and raised to duplicateSpikeWindow_s at run time if
                             # removeDuplicateSpikes is True (see effective_tauC)
        "contamination_values": None,  # For ibl_sliding: contamination values to test
                                       # If None, uses np.arange(0.5, 35.5, 0.5) / 100
        "confidence_threshold": 0.9,  # For ibl_sliding: confidence threshold for contamination estimate
        "tauR_reject": 0.5 / 1000,  # For ibl_sliding: refractory periods <= this (s) are not tested

        # Legacy parameters (still supported for backward compatibility): ###(our lab briefly used these)
        "tauR_valuesMin": 2 / 1000,  # refractory period time (s), usually 0.002 s
        "tauR_valuesMax": 2 / 1000,  # refractory period time (s)
        "tauR_valuesStep": 0.5 / 1000,  # step size for tauR sweep
        "hillOrLlobetMethod": True,  # use hill if 1, else use Llobet et al. (legacy)


        ## Percentage spikes missing parameters
        "computeTimeChunks": False,  ### False by default for some reason, though prior to downloading this version we had it as True...# compute fraction refractory period violations and
        # percent spikes missing for different time chunks
        "deltaTimeChunk": 360,  # time in seconds

        ## Presence  ratio
        "presenceRatioBinSize": 60,  # in seconds

        ## Drift estimate
        "driftBinSize": 60,  # in seconds
        "computeDrift": False,  # If True computes drift per unit

        ## Waveform parameters
        "minThreshDetectPeaksTroughs": 0.2,  # this is multiples by the max value in a units
        # waveform to give the minimum prominence to detect peaks

        # it must be at least this many times larger than the peak after the trough
        # to qualify as a non-somatic unit
        "normalizeSpDecay": True,  # If True, will normalize spatial decay points relative to maximum
        # this makes the spatial decay more invariant to the spike-sorting
        "spDecayLinFit": False, # if True, use a linear fit for spatial decay. If false, use exponential (preferred)
        "computeSpatialDecay": True,

        ## Recording parameters - !!WARNINGS!! :
        # 1. if you modify any of these after having already run bombcell, you
        # will need to set 'reextractRaw' to true to update the raw waveforms
        # 2. if you also specify a meta file as input & you are using spikeGLX or
        # OpenEphys to record your probes, these values will be over-ridden by the ones
        # in your provided meta file (bombcell reads them in)
        "ephys_sample_rate": 30000,  # samples per second
        "nChannels": 385,  # Number of recorded channels (including any sync channels) in raw data ### within bombcell's code, things are designed such that this is the default which is changed if the meta file disagrees. I think it should be named to reflect that, but alas. Anyway, keep it 385 and never use it to refer to your actual channel number.
        "nSyncChannels": 1, # Number of recorded SYNC channels in raw data

        ## Distance metric parameters
        "computeDistanceMetrics": False,  # If True computes distance metics NOTE is slow in ML
        "nChannelsIsoDist": 4,  # Number of nearby channels to use in distance metric computation

        ## ADDED BY LOUISE, Spatial spreak of spikes ### need to revise on where they are used. I think maybe they are only used in UnitMatch...
        "computeSpatialSpreadSpikes": True,
        "maxSpread": 25,

        # Quality metric classification parameters
        "splitGoodAndMua_NonSomatic": False,  # whether to classify non-somatic units
        ## Waveform-based
        "maxNPeaks": 2,  # maximum number of peaks
        "maxNTroughs": 1,
        "minWvDuration": 100,  # in us
        "maxWvDuration": 1150,  # in us
        "minSpatialDecaySlope": -0.008,
        "minSpatialDecaySlopeExp": 0.01,
        "maxSpatialDecaySlopeExp": 0.1,  # in a.u / um
        "maxWvBaselineFraction": 0.3,
        "maxScndPeakToTroughRatio_noise": 0.8,
        "minTroughToPeak2Ratio_nonSomatic": 5,
        "minWidthFirstPeak_nonSomatic": 4,
        "minWidthMainTrough_nonSomatic": 5,
        "maxPeak1ToPeak2Ratio_nonSomatic": 3,
        "maxMainPeakToTroughRatio_nonSomatic": 0.8,

        ## Distance metrics
        "isoDmin": 20,  # minimum isolation distance value
        "lratioMax": 0.3,  # maximum l-ratio value
        "ss_min": np.nan,  # minimum silhouette score, not currently implemented

        ## Other classification parameters
        "minAmplitude": 40, # in uV
        "maxRPVviolations": 0.1, ### default 0.1 apparently. # max fraction of refractory period violations
        "maxPercSpikesMissing": 20,  # max percentage of missing spikes
        "minNumSpikes": 500,  ### changed from 500 because my sessions are short... # minimum number of total spikes recorded
        "maxDrift": 100,  # in um
        "minPresenceRatio": 0.7,  # minimum fraction of time chunks unit must be present for
        "minSNR": 5,  # min SNR for a good unit

        ### parameters within the "For UnitMatch" section
            ## note that many of these are just repeats of above parameters. They are commented out if so, and should remain commented out.

        ## parameters that are new
        "saveMultipleRaw": True,
        ## commented out parameters.
        # "detrendWaveform": True,
        # "detrendForUnitMatch": False,
        # "nRawSpikesToExtract": 1000,
        #
        # "decompress_data": True, ### Not using this actually because I dn't have cbin files.

    }


    # Fetch metadata uV conversion factor
    if meta_file is not None and gain_to_uV is None:
        gain_to_uV = get_gain_spikeglx(meta_file)

    # Add to param dictionnary
    if meta_file is not None:
        param["ephys_meta_file"] = str(meta_file)
        if gain_to_uV is not None and not np.isnan(gain_to_uV):
            param["gain_to_uV"] = gain_to_uV
        else:
            param["gain_to_uV"] = np.nan
    else:
        param["ephys_meta_file"] = None
        param["gain_to_uV"] = gain_to_uV

    if raw_file != None:
        param["raw_data_file"] = str(raw_file)
    else:
        param["raw_data_file"] = None

    if kilosort_version == 4:
        param["spike_width"] = 61 # width of spike in samples
        param["waveformBaselineNoiseWindow"] = 10  # time in samples at the beginning, with no signal
        param["waveform_baseline_window_start"] = 0  # 0-indexed, in samples
        param["waveform_baseline_window_stop"] = 10  # 0-indexed, in samples

    else:
        param["spike_width"] = 82 # width of spike in samples
        param["waveformBaselineNoiseWindow"] = 20  # time in samples at the beginning, with no signal
        param["waveform_baseline_window_start"] = 21  # in samples
        param["waveform_baseline_window_stop"] = 31  # in samples

    return param

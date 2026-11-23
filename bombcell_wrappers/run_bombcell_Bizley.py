#### adjusted copy of the bombcell run_bombcell code. Has key new features such as removal of spikes outside session.
import time
from pathlib import Path
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from tqdm.auto import tqdm

from bombcell.extract_raw_waveforms import manage_data_compression, extract_raw_waveforms
from bombcell.loading_utils import load_ephys_data
from bombcell.helper_functions import create_quality_metrics_dict, get_all_quality_metrics

# import matplotlib.pyplot as plt
import bombcell.quality_metrics as qm
from bombcell.save_utils import get_metric_keys, save_results
from bombcell.plot_functions import *

from neuropixels_chronic_spikesorting_Bizley.helpers.remove_excess_spikes import remove_excess_spikes


def run_bombcell_Bizley(ks_dir, save_path, param):
    """
    This function runs the entire bombcell pipeline from input data paths

    Parameters
    ----------
    ks_dir : string
        The path to the KiloSort (or equivalent) save directory
    save_path : string
        The path to the directory to save the bombcell results
    param : dict
        The param dictionary

    Returns
    -------
    quality_metrics : dict
        The quality metrics for each unit
    param : dict
        The parameters
    unit_type : ndarray
        The unit classifications as numbers
    unit_type_string: ndarray
        The unit classifications as names
    """

    if param.get("verbose", False):
        print("🚀 Starting BombCell quality metrics pipeline...")
        print(f"📁 Processing data from: {ks_dir}")
        print(f"Results will be saved to: {save_path}")
        print("\nLoading ephys data...")

    (
        spike_times_samples,
        spike_clusters, # actually spike_templates, but they're the same in bombcell
        template_waveforms,
        template_amplitudes,
        pc_features,
        pc_features_idx,
        channel_positions,
    ) = load_ephys_data(ks_dir)

    if param.get("verbose", False):
        print(f"Loaded ephys data: {len(np.unique(spike_clusters))} units, {len(spike_times_samples):,} spikes")

    # Extract or load in raw waveforms
    if param["raw_data_file"] is not None:
        # Handle data decompression if needed
        if param.get("decompress_data", False):
            if param.get("verbose", False):
                print("\n📦 Checking for compressed data...")
            from bombcell.extract_raw_waveforms import decompress_data_if_needed
            param["raw_data_file"] = decompress_data_if_needed(
                param["raw_data_file"],
                decompress_data=param["decompress_data"]
            )

        if param.get("verbose", False):
            print("\n🔍 Extracting raw waveforms...")
        (
        raw_waveforms_full,
        raw_waveforms_peak_channel,
        signal_to_noise_ratio,
        raw_waveforms_id_match,
        ) = extract_raw_waveforms(
            param,
            spike_clusters,
            spike_times_samples,
            param["reextractRaw"],
            save_path,
        )
    else:
        raw_waveforms_full = None
        raw_waveforms_peak_channel = None
        signal_to_noise_ratio = None
        raw_waveforms_id_match = None
        param["extractRaw"] = False  # No waveforms to extract!

    # pre-load peak channels
    maxChannels = qm.get_waveform_peak_channel(template_waveforms)



    # Remove duplicate spikes
    if param["removeDuplicateSpikes"]: ### it will remove them literally from further analysis but nondestructively. So if you load spikes elsewhere without running this, you will still have them.
        (
            unique_templates,
            empty_unit_idx,
            spike_times_samples,
            spike_clusters,
            template_amplitudes,
            pc_features,
            raw_waveforms_full,
            raw_waveforms_peak_channel,
            signal_to_noise_ratio,
            maxChannels,
        ) = qm.remove_duplicate_spikes(
            spike_times_samples,
            spike_clusters,
            template_amplitudes,
            maxChannels,
            save_path,
            param,
            pc_features=pc_features,
            raw_waveforms_full=raw_waveforms_full,
            raw_waveforms_peak_channel=raw_waveforms_peak_channel,
            signal_to_noise_ratio=signal_to_noise_ratio,
        )


    else:
        unique_templates = np.unique(spike_clusters)

    # Remove excess spikes
    if param["removeExcessSpikes"]:
        (
            unique_templates,
            empty_unit_idx_Postexcess,
            spike_times_samples,
            spike_clusters,
            template_amplitudes,
            pc_features,
            raw_waveforms_full,
            raw_waveforms_peak_channel,
            signal_to_noise_ratio,
            maxChannels,
        ) = remove_excess_spikes(
            spike_times_samples,
            spike_clusters,
            template_amplitudes,
            maxChannels,
            save_path,
            param,
            pc_features=pc_features,
            raw_waveforms_full=raw_waveforms_full,
            raw_waveforms_peak_channel=raw_waveforms_peak_channel,
            signal_to_noise_ratio=signal_to_noise_ratio,
        )
    else:
        unique_templates = np.unique(spike_clusters)

    # Divide recording into time chunks
    spike_times_seconds = spike_times_samples / param["ephys_sample_rate"]
    if param["computeTimeChunks"]:
        time_chunks = np.arange(
            np.min(spike_times_seconds),
            np.max(spike_times_seconds),
            param["deltaTimeChunk"],
        )
    else:
        time_chunks = np.array(
            (np.min(spike_times_seconds), np.max(spike_times_seconds))
        )

    param['unique_templates'] = unique_templates

    # Initialize quality metrics dictionary
    n_units = unique_templates.size
    quality_metrics = create_quality_metrics_dict(n_units, snr=signal_to_noise_ratio)
    quality_metrics["maxChannels"] = maxChannels

    # Complete with remaining quality metrics
    if param.get("verbose", False):
        print(f"\n⚙️ Computing quality metrics for {n_units} units...")
        print("   (Progress bar will appear below)")

    quality_metrics, times = get_all_quality_metrics(
        unique_templates,
        spike_times_seconds,
        spike_clusters,
        template_amplitudes,
        time_chunks,
        pc_features,
        pc_features_idx,
        quality_metrics,
        raw_waveforms_full,
        channel_positions,
        template_waveforms,
        param,
        save_path,
    )

    if param.get("verbose", False):
        print("\n🏷️ Classifying units (good/MUA/noise/non-soma)...")

    unit_type, unit_type_string = qm.get_quality_unit_type(
        param, quality_metrics
    )  # JF: this should be inside bc.get_all_quality_metrics
    if param.get("verbose", False):
        print("\nGenerating summary plots...")

    # plot_summary_data(quality_metrics, template_waveforms, unit_type, unit_type_string, param) ### you don't really want to plot stuff when you are just running the code batch style. I think we want this code to be higher up in the hierarchy, under better control

    if param.get("verbose", False):
        print("\nSaving results...")

    save_results(
        quality_metrics,
        unit_type_string,
        unique_templates,
        param,
        raw_waveforms_full,
        raw_waveforms_peak_channel,
        raw_waveforms_id_match,
        save_path,
        ks_dir,
    )

    return (
        quality_metrics,
        param,
        unit_type,
        unit_type_string,
        template_waveforms
    )

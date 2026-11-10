### Louise's function to remove spikes outisde the sessin range from consderation. Based on the bombcell remove_duplicate_spikes, updated by Jeff.

import warnings

import numpy as np
from numba import njit

from scipy.optimize import curve_fit
from scipy.signal import medfilt, find_peaks
from scipy.stats import norm, chi2

import matplotlib.pyplot as plt

from bombcell.extract_raw_waveforms import path_handler
from bombcell.default_parameters import check_parameter_fields

from pathlib import Path
from bombcell.extract_raw_waveforms import read_meta
import os


def remove_excess_spikes(
    spike_times_samples,
    spike_clusters,
    template_amplitudes,
    maxChannels,
    save_path,
    param,
    pc_features=None,
    raw_waveforms_full=None,
    raw_waveforms_peak_channel=None,
    signal_to_noise_ratio=None,
                         ):

    save_path = path_handler(save_path)

    if param["recomputeExcessSpikes"] or not(save_path/Path('spikes._bc_excessSpikes.npy')) in list(save_path.glob('*')):### used to be the following but os breaks for unknown reasons. I believe mine is the same. #not(os.path.isdir(os.path.join(save_path, "spikes._bc_excessSpikes.npy"))):

        # GET SIZE RAW FILE

        # Get necessary info from param
        raw_data_file = param["raw_data_file"]
        meta_path = Path(param["ephys_meta_file"]) if param["ephys_meta_file"] is not None else None
        n_channels = param["nChannels"] ### don't worry this is changed if not what it says in the meta file
        spike_width = param["spike_width"]

        # half_width is the number of sample before spike_time which are recorded,
        # then will take spike_width - half_width after
        if spike_width == 82:  # kilosort < 4, baseline 0:41
            half_width = spike_width / 2
        elif spike_width == 61:  # kilosort = 4, baseline 0:20
            half_width = 20

        if meta_path is not None and meta_path.exists():
            meta_dict = read_meta(meta_path)
            n_elements = (int(meta_dict["fileSizeBytes"]) / 2)  # int16 so 2 bytes per data point
            n_channels_rec = int(meta_dict["nSavedChans"])  # Total channels including sync
            param["n_channels_rec"] = n_channels_rec
            maxSize = int(n_elements / n_channels_rec)
        else:
            # Use default values when no metafile is available
            print("Warning: No meta file found. Using default parameters...")
            # Get file size directly from the raw data file
            import os
            file_size_bytes = os.path.getsize(raw_data_file)
            n_elements = file_size_bytes / 2  # int16 so 2 bytes per data point

            # When no metafile, nChannels already includes sync channels
            n_channels_rec = n_channels  # Should be 385 (384 neural + 1 sync)
            print(f"Using {n_channels_rec} total channels in recording")
            param["n_channels_rec"] = n_channels_rec
            maxSize = int(n_elements / n_channels_rec)
        maxSize = maxSize -spike_width + half_width


        # parameters
        num_spikes_full = spike_times_samples.shape[0]

        # initialize and re-allocate
        excess_spike_idx = np.zeros(num_spikes_full)

        for i,spike_time in enumerate(spike_times_samples):
            if spike_time > maxSize: ### this is the key bit of code. If spike times (in samples) are greater than the maxSize as defined above (in samples), then put into the exclude vector.
                excess_spike_idx[i] = 1


        # rename the spike templates according to the remaining templates
        good_templates_idx = np.unique(spike_clusters)
        new_spike_idx = np.full(max(good_templates_idx) + 1, np.nan)
        new_spike_idx[good_templates_idx] = np.arange(good_templates_idx.shape[0])
        spike_clusters_flat = (new_spike_idx[spike_clusters].astype(np.int32))



        if param["saveSpikes_withoutExcess"]:
            np.save(save_path / "spikes._bc_excessSpikes.npy",excess_spike_idx,) ### so there is a problem with these, and it is that it wholly depends on the result of the duplicate spikes being the same.

    else:
        excess_spike_idx = np.load(save_path / "spikes._bc_excessSpikes.npy")

    # check if there are any empty units
    unique_templates = np.unique(spike_clusters)
    non_empty_units = np.unique(spike_clusters[excess_spike_idx == 0])
    empty_unit_idx = np.isin(unique_templates, non_empty_units, invert=True)
    spike_idx_to_keep = np.argwhere(excess_spike_idx == 0).squeeze()

    # remove any empty units and duplicate spikes
    spike_times_samples = spike_times_samples[spike_idx_to_keep]
    spike_clusters = spike_clusters[spike_idx_to_keep]
    template_amplitudes = template_amplitudes[spike_idx_to_keep]
    if pc_features is not None:
        pc_features = pc_features[spike_idx_to_keep, :, :]

    if raw_waveforms_full is not None:
        raw_waveforms_full = raw_waveforms_full[empty_unit_idx == False, :, :]
        raw_waveforms_peak_channel = raw_waveforms_peak_channel[empty_unit_idx == False]

    if signal_to_noise_ratio is not None:
        signal_to_noise_ratio = signal_to_noise_ratio[empty_unit_idx == False]

    return (
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
    )
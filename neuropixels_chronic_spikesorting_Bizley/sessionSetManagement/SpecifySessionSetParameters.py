"""Build region-specific session parameters from the selected data config."""

from datetime import timedelta

import pandas as pd

from config import get_configs, selected_session_set, parse_config_date


def SpecifySessionSetParameters(ferret, SessionSetName, BrainRegion):
    data_config, _ = get_configs()
    session_set, region = selected_session_set(ferret, SessionSetName, BrainRegion, data_config)
    date_format = data_config.get("date_glob_format", "%Y%m%d")
    dates = []
    if session_set.get("date_start") and session_set.get("date_end"):
        start = parse_config_date(session_set["date_start"])
        end = parse_config_date(session_set["date_end"])
        dates = pd.date_range(start, end - timedelta(days=1), freq="D").strftime(date_format)
    prefixes = session_set.get("session_folders", session_set.get("folder_prefixes", []))

    return {
        "ferret": ferret,
        "ferret_no_id": session_set.get("animal_label", ferret),
        "DateStart": str(session_set.get("date_start", "")),
        "DateEnd": str(session_set.get("date_end", "")),
        "IncludedDates": dates,
        "IncludedSessionPrefixes": prefixes,
        "sessionSetLabel": SessionSetName,
        "channel_map_to_use": region.get("channel_map", ""),
        "badChannelList": region.get("bad_channels", []),
        "stream_id": region.get("stream_id", "imec0.ap"),
        "recording_format": data_config.get("recording_format", "spikeglx"),
        "session_discovery": data_config["session_discovery"],
        "nas_root": data_config["paths"]["nas_root"],
        "local_root": data_config["paths"]["local_root"],
        "output_root": data_config["paths"]["output_root"],
        "lfp_root": data_config["paths"].get("lfp_root", data_config["paths"]["output_root"]),
    }


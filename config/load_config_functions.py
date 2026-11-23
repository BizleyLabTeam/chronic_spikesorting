"""Load the repository's data and run YAML configuration files."""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator

try:
    import yaml
except ImportError as exc:  # pragma: no cover - depends on installation
    raise ImportError("PyYAML is required to load pipeline configuration. Install pyyaml.") from exc


REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_CONFIG = CONFIG_DIR / "data_config.yaml"
DEFAULT_RUN_CONFIG = CONFIG_DIR / "run_config.yaml"


def _load_yaml(path: str | Path) -> dict[str, Any]:
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"Configuration file must contain a YAML mapping: {path}")
    return data


def _resolve_path(value: Any, base: Path) -> Any:
    if isinstance(value, dict):
        return {key: _resolve_path(item, base) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_path(item, base) for item in value]
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        variable = value[2:-1]
        expanded = os.environ.get(variable)
        return Path(expanded).expanduser() if expanded else Path(value)
    if isinstance(value, str):
        path = Path(value).expanduser()
        return path if path.is_absolute() else (base / path).resolve()
    return value


def load_data_config(config_file_path: str | Path | None = None) -> dict[str, Any]:
    """Load and validate dataset paths and selected session sets."""
    path = Path(config_file_path or os.environ.get("NEUROPIXELS_DATA_CONFIG", DEFAULT_DATA_CONFIG))
    config = _load_yaml(path)
    required = ("paths", "session_discovery", "session_sets_to_run", "session_sets")
    for key in required:
        if not isinstance(config.get(key), dict):
            raise ValueError(f"Data config section '{key}' must be a YAML mapping: {path}")
    config["paths"] = _resolve_path(config["paths"], path.resolve().parent)
    config["recording_format"] = str(config.get("recording_format", "spikeglx")).lower()
    if config["recording_format"] != "spikeglx":
        raise ValueError(f"Unsupported recording_format {config['recording_format']!r}; currently supported: spikeglx")
    for key in ("nas_root", "local_root", "output_root"):
        if key not in config["paths"]:
            raise ValueError(f"Data config paths must define '{key}': {path}")
    if not config["session_sets_to_run"]:
        raise ValueError("session_sets_to_run must select at least one animal and session set")
    return config


def load_run_config(config_file_path: str | Path | None = None) -> dict[str, Any]:
    """Load and validate processing settings."""
    path = Path(config_file_path or os.environ.get("NEUROPIXELS_RUN_CONFIG", DEFAULT_RUN_CONFIG))
    config = _load_yaml(path)
    required = ("tools", "sampling", "catgt", "saturation", "sorting", "drift_correction", "workflow")
    for key in required:
        if not isinstance(config.get(key), dict):
            raise ValueError(f"Run config section '{key}' must be a YAML mapping: {path}")
    for key in ("catgt_location", "overstrike_location"):
        if key in config["tools"]:
            config["tools"][key] = _resolve_path(config["tools"][key], path.resolve().parent)
    return config


_DATA_CONFIG: dict[str, Any] | None = None
_RUN_CONFIG: dict[str, Any] | None = None


def load_configs(data_config_path: str | Path | None = None, run_config_path: str | Path | None = None):
    """Load the shared data/run configuration pair."""
    global _DATA_CONFIG, _RUN_CONFIG
    _DATA_CONFIG = load_data_config(data_config_path)
    _RUN_CONFIG = load_run_config(run_config_path)
    return _DATA_CONFIG, _RUN_CONFIG


def get_configs():
    """Return active configs, loading the project-root files on first use."""
    global _DATA_CONFIG, _RUN_CONFIG
    if _DATA_CONFIG is None or _RUN_CONFIG is None:
        return load_configs()
    return _DATA_CONFIG, _RUN_CONFIG


def selected_animal_session_sets(data_config: dict[str, Any] | None = None) -> dict[str, list[str]]:
    data_config = data_config or get_configs()[0]
    selected = data_config["session_sets_to_run"]
    return {animal: list(session_sets or []) for animal, session_sets in selected.items()}


def iter_selected_session_sets(data_config: dict[str, Any] | None = None) -> Iterator[tuple[str, str, str]]:
    """Yield (animal, session-set, region) selections in config order."""
    data_config = data_config or get_configs()[0]
    configured = data_config["session_sets"]
    for animal, session_sets in selected_animal_session_sets(data_config).items():
        if animal not in configured:
            raise KeyError(f"Selected animal {animal!r} is not defined under session_sets")
        for session_set_name in session_sets:
            session_set = configured[animal].get(session_set_name)
            if session_set is None:
                raise KeyError(f"Selected session set {animal}/{session_set_name} is not defined")
            for region in session_set.get("regions", {}):
                yield animal, session_set_name, region


def parse_config_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return datetime.strptime(str(value), "%Y%m%d").date()


def get_legacy_data_values() -> dict[str, Any]:
    data, run = get_configs()
    paths = data["paths"]
    selected = selected_animal_session_sets(data)
    animal = next(iter(selected))
    session_set_name = selected[animal][0]
    session_set = data["session_sets"][animal][session_set_name]
    region = next(iter(session_set["regions"]))
    region_config = session_set["regions"][region]
    animal_label = session_set.get("animal_label", animal)
    animal_path = paths["nas_root"] / animal
    local_animal_path = paths["local_root"] / animal
    output_root = paths["output_root"]
    values = {
        "NAS_neural_data": paths["nas_root"],
        "NAS_session_path": animal_path,
        "local_neural_data": paths["local_root"],
        "local_session_path": local_animal_path,
        "output_folder": output_root,
        "LFP_folder": paths.get("lfp_root", output_root),
        "behavior_path": paths.get("behavior_root"),
        "figure_folder": paths.get("figures_root"),
        "stimuli_path": paths.get("stimuli_root"),
        "catgt_location": run["tools"]["catgt_location"],
        "OverStrike_location": run["tools"]["overstrike_location"],
        "ferret": animal,
        "ferret_no_id": animal_label,
        "channel_map_to_use": region_config.get("channel_map", ""),
        "badChannelList": region_config.get("bad_channels", []),
        "stream_id": region_config.get("stream_id", "imec0.ap"),
        "regionLabels": list(session_set.get("regions", {})),
        "sessionString": "*",
        "frequencyOfConcatenation": run["workflow"].get("frequency_of_concatenation", "do_everything"),
        "sessionsToDo": "all",
        "SurveyOverride": data.get("survey_override", False),
        "dateFormat": data.get("date_glob_format", "%Y%m%d"),
        "np_fs": run["sampling"].get("np_fs", 30000),
        "bhv_fs": run["sampling"].get("behavior_fs", 24414.0625),
        "sessionSetLabel": session_set_name,
        "sessionSet_aux_folders": animal_path,
        "sessionDiscovery": data["session_discovery"],
        "sessionSetsToRun": selected,
        "selectedSessionSets": data["session_sets"],
        "paths": paths,
    }
    return values


def get_legacy_run_values() -> dict[str, Any]:
    _, run = get_configs()
    tools = run["tools"]
    catgt = run["catgt"]
    saturation = run["saturation"]
    sorting = run["sorting"]
    drift = run["drift_correction"]
    workflow = run["workflow"]
    legacy = run.get("legacy_spikeinterface", {})
    return {
        "desired_n_jobs": drift.get("n_jobs", 1),
        "doRemoveBadChannels": drift.get("remove_bad_channels", True),
        "skipStuffThatKSGUIDoes": workflow.get("skip_kilosort_preprocessing", False),
        "beginningAndEndToCutOff": saturation.get("begin_end_cutoff_s", [0, 0]),
        "loadSatsFromFile": saturation.get("load_from_file", True),
        "doSaturationReplace": saturation.get("replace", True),
        "silenceOrNoiseReplace_sessionwise": drift.get("saturation_mode", saturation.get("mode", "zeros")),
        "silenceOrNoiseReplace_within": legacy.get("silence_mode", saturation.get("mode", "zeros")),
        "silenceOrNoiseReplace": saturation.get("mode", "zeros"),
        "bin_s_sessionCat": drift.get("bin_s", 6.0),
        "doSpikeSorting": sorting.get("do_spike_sorting", True),
        "createCompressed": sorting.get("create_compressed", False),
        "copyAuxData": sorting.get("copy_aux_data", False),
        "saveMultirecInfoFile": sorting.get("save_multirecording_info", True),
        "saveLFP": sorting.get("save_lfp", False),
        "overwriteRaw": sorting.get("overwrite_raw", False),
        "overwriteChanMap": sorting.get("overwrite_chan_map", True),
        "overwriteSpikesorting": sorting.get("overwrite_spikesorting", False),
        "overwriteAuxData": sorting.get("overwrite_aux_data", False),
        "overwriteLFP": sorting.get("overwrite_lfp", True),
        "savePreprocessing": drift.get("save_preprocessing", True),
        "overwritePreprocessing": drift.get("overwrite_preprocessing", True),
        "resaveMotionIfLoadingPreprocessing": drift.get("resave_motion_if_loading", False),
        "checkMotionPlotsOnline": drift.get("plot_online", False),
        "calculateSessionMotionDisplacement": drift.get("calculate_session_displacement", True),
        "doPreprocessing": workflow.get("do_preprocessing", False),
        "testingThings": workflow.get("testing", False),
        "ap_common_reference": catgt.get("common_reference", "-gblcar"),
        "ap_filter": catgt.get("ap_filter", "butter,12,300,6000"),
        "lf_filter": catgt.get("lf_filter", "butter,12,0,400"),
        "lfp_downsample_factor": catgt.get("lf_downsample_factor", 30),
        "np_fs": run["sampling"].get("np_fs", 30000),
        "saturation": saturation,
        "sorting": sorting,
        "drift_correction": drift,
        "workflow": workflow,
        "catgt": catgt,
        "tools": tools,
    }


def configure_from_cli():
    """Load optional config paths passed to any pipeline script."""
    import argparse

    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--data-config", help="Path to the data YAML file")
    parser.add_argument("--run-config", help="Path to the processing YAML file")
    args, _ = parser.parse_known_args()
    data, run = load_configs(args.data_config, args.run_config)
    config_path = Path(args.data_config or os.environ.get("NEUROPIXELS_DATA_CONFIG", DEFAULT_DATA_CONFIG))
    required_paths = ("nas_root", "local_root", "output_root")
    for key in required_paths:
        if data["paths"].get(key) is None:
            raise ValueError(f"Set paths.{key} in {config_path}")
    return data, run


def selected_session_set(ferret: str, session_set_name: str, region: str, data_config=None):
    data_config = data_config or get_configs()[0]
    try:
        session_set = data_config["session_sets"][ferret][session_set_name]
        region_config = session_set["regions"][region]
    except KeyError as exc:
        raise KeyError(f"Incomplete data config for {ferret}/{session_set_name}/{region}") from exc
    return session_set, region_config


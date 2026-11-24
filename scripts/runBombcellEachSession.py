"""Run Bombcell for each configured animal/session-set/region selection."""

from pathlib import Path
import traceback

from bombcell.plot_functions import plot_summary_data

from config import configure_from_cli, get_configs, iter_selected_session_sets
from generally_useful_functions_Bizley.getCorrectRecordingForRegion import getCorrectRecordingForRegion
from neuropixels_chronic_spikesorting_Bizley.run_bombcell_session import run_bombcell_session
from neuropixels_chronic_spikesorting_Bizley.sessionSetManagement.SpecifySessionSetParameters import (
    SpecifySessionSetParameters,
)
from neuropixels_chronic_spikesorting_Bizley.sessionSetManagement.getSessionsWithinMapForSessionSet import (
    getSessionsWithinMapForSessionSet,
)


def main():
    _, run_config = get_configs()
    bombcell_config = run_config.get("bombcell", {})
    kilosort_version = bombcell_config.get("kilosort_version", 4)
    reload_existing_results = bombcell_config.get("reload_existing_results", False)
    skip_if_already_done = bombcell_config.get("skip_if_already_done", True)
    plot_with_breakpoints = bombcell_config.get("plot_with_breakpoints", False)

    selected_sets = sorted(iter_selected_session_sets(), key=lambda selection: (selection[1], selection[2]))
    for animal, session_set_name, region in selected_sets:
        params = SpecifySessionSetParameters(animal, session_set_name, region)
        nas_sessions, local_sessions = getSessionsWithinMapForSessionSet(params)
        for index, (session, local_session) in enumerate(zip(nas_sessions, local_sessions), start=1):
            session_name = session.name
            print(
                f"\n{'=' * 60}\nSESSION {index}/{len(nas_sessions)} {session_name}\n"
                f"Selection: {animal}/{session_set_name}/{region}\n{'=' * 60}",
                flush=True,
            )

            imec_folders = list(session.glob("*imec*"))
            meta_data, used_stream, nas_probe_folder = getCorrectRecordingForRegion(
                imec_folders, params["channel_map_to_use"], localData=False
            )
            if used_stream is None:
                print(
                    f"Skipping {session_name}: no probe matches channel map "
                    f"{params['channel_map_to_use']!r}.",
                    flush=True,
                )
                continue

            local_probe_folders = list(local_session.glob(f"*{used_stream[:-3]}"))
            if not local_probe_folders:
                raise FileNotFoundError(
                    f"No local probe folder matching {used_stream[:-3]!r} under {local_session}. "
                    "Run spikesort_folder.py for this session first."
                )
            local_probe_folder = local_probe_folders[0]
            raw_folder = local_probe_folder / "catgt_CorrectedRaw"
            raw_files = list(raw_folder.glob("*.bin"))
            meta_files = list(raw_folder.glob("*.meta"))
            if not raw_files or not meta_files:
                raise FileNotFoundError(
                    f"Bombcell needs the preprocessed .bin and .meta files in {raw_folder}. "
                    "Run spikesort_folder.py for this session first."
                )

            sorter_output_folder = (
                params["output_root"] / animal / session_set_name / region / session_name
            )
            if not sorter_output_folder.is_dir():
                raise FileNotFoundError(
                    f"Kilosort output folder does not exist: {sorter_output_folder}. "
                    "Run spikesort_folder.py for this session first."
                )
            if not (sorter_output_folder / "spike_times.npy").is_file():
                raise FileNotFoundError(
                    f"Kilosort output is missing spike_times.npy: {sorter_output_folder}"
                )

            session_config = {
                "name": session_name,
                "ks_dir": sorter_output_folder,
                "raw_file": raw_files[0],
                "meta_file": meta_files[0],
                "save_path": sorter_output_folder,
                "sessionSetParams": {**params, "currentSession": session_name},
            }

            existing_results = sorter_output_folder / "cluster_bc_unitType.tsv"
            if skip_if_already_done and existing_results.is_file():
                print(f"Skipping {session_name}: Bombcell results already exist at {existing_results}.", flush=True)
                continue

            try:
                result, template_waveforms = run_bombcell_session(
                    session_config, kilosort_version, reload_existing_results
                )
            except Exception:
                print(f"Bombcell failed for {session_name}:", flush=True)
                traceback.print_exc()
                raise

            if plot_with_breakpoints and result and result.get("quality_metrics") is not None:
                plot_summary_data(
                    result["quality_metrics"],
                    template_waveforms,
                    result["unit_type"],
                    result["unit_type_string"],
                    result["param"],
                )


if __name__ == "__main__":
    configure_from_cli()
    main()

"""Discover matching acquisition folders from the configured date/template."""

from neuropixels_chronic_spikesorting_Bizley.helpers.helpers_spikesorting_scripts import sort_np_sessions


def getSessionsWithinMapForSessionSet(sessionSetParams):
    discovery = sessionSetParams["session_discovery"]
    period_setting = discovery.get("period", "both")
    periods = ["AM", "PM"] if period_setting == "both" else (
        list(period_setting) if isinstance(period_setting, list) else [period_setting]
    )
    folder_template = discovery["folder_glob"]
    animal = sessionSetParams["ferret"]
    animal_label = sessionSetParams["ferret_no_id"]
    nas_session_path = sessionSetParams["nas_root"] / animal
    local_session_path = sessionSetParams["local_root"] / animal

    sessions = []
    prefixes = sessionSetParams.get("IncludedSessionPrefixes", [])
    if prefixes:
        sessions.extend(
            session
            for prefix in prefixes
            for session in nas_session_path.glob(prefix)
        )
    else:
        for session_date in sessionSetParams["IncludedDates"]:
            for period in periods:
                pattern = folder_template.format(
                    animal=animal,
                    animal_label=animal_label,
                    date=session_date,
                    period=period,
                )
                sessions.extend(nas_session_path.glob(pattern))
    sessions = sort_np_sessions(sessions) if sessions else []
    if not sessions:
        raise FileNotFoundError(
            f"No session folders matched the configured template beneath {nas_session_path} "
            f"for {sessionSetParams['DateStart']}–{sessionSetParams['DateEnd']}"
        )

    local_sessions = []
    for session in sessions:
        local_session = local_session_path / session.name
        local_session.mkdir(parents=True, exist_ok=True)
        local_sessions.append(local_session)
    return sessions, local_sessions


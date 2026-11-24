"""Apply optional Bombcell parameter overrides from the run configuration."""

from config import get_configs


def adjustParametersSessionSpecific(param, sessionSetParams):
    _, run_config = get_configs()
    param.update(run_config.get("bombcell", {}).get("parameters", {}))
    return param


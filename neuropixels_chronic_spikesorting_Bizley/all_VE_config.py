"""Compatibility facade exposing values from the active YAML configuration."""

from config import (
    get_legacy_data_values,
    get_legacy_run_values,
)


def __getattr__(name):
    data = get_legacy_data_values()
    if name in data:
        return data[name]
    run = get_legacy_run_values()
    if name in run:
        return run[name]
    raise AttributeError(f"Configuration has no setting named {name!r}")


def __dir__():
    return sorted(set(get_legacy_data_values()) | set(get_legacy_run_values()))


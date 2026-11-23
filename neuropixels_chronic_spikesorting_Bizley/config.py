"""Compatibility facade for the legacy package-level configuration module."""

from config import get_legacy_data_values, get_legacy_run_values


def __getattr__(name):
    data = get_legacy_data_values()
    if name in data:
        return data[name]
    run = get_legacy_run_values()
    if name in run:
        return run[name]
    raise AttributeError(f"Configuration has no setting named {name!r}")


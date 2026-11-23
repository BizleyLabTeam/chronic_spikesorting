"""Return selected session sets for an animal from data_config.yaml."""

from config import selected_animal_session_sets


def gatherSessionSetListForFerret(ferret):
    selected = selected_animal_session_sets()
    if ferret not in selected:
        raise ValueError(f"Animal {ferret!r} has no selected session sets in data_config.yaml")
    return selected[ferret]


### based on run_bombcell_session from the unitmatch code.
### framework all still there, but with many custom adjustments.
###
### The reason I did this was because UnitMatch is somewhat seperate from bombcell in a lot of ways and
### there was already at least one version assumption problem wrt bombcell and unitmatch when I used Unitmatch's
### code directly... So instead, we will have our bombcell framework and can run Unitmatch on top of it.

### when reading it... Try not to get overwhelmed with all the "prints", there isn't actually all that much to it otherwise.

import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


import bombcell as bc
from neuropixels_chronic_spikesorting_Bizley.helpers.get_unit_types_bombcell_from_file import get_unit_types_bombcell_from_file
from bombcell_wrappers.get_preferred_bombcell_parameters import get_preferred_bombcell_parameters
from bombcell_wrappers.run_bombcell_Bizley import run_bombcell_Bizley


def run_bombcell_session(session_config,kilosort_version=4,reloadExistingResults = True):

    name = session_config['name']
    ks_dir = session_config['ks_dir']
    raw_file = session_config.get('raw_file')
    meta_file = session_config.get('meta_file')

    # Create save path in the kilosort directory
    save_path = Path(session_config['save_path'])

    print(f"🔬 Analyzing session: {name}")
    print(f"   📁 Kilosort directory: {ks_dir}")
    print(f"   🗂️  Raw file: {Path(raw_file).name if raw_file else 'Not specified'}")
    print(f"   📄 Meta file: {Path(meta_file).name if meta_file else 'Not specified'}")
    print(f"   💾 Results will be saved to: {save_path}")

    # Check if BombCell has already been run
    existing_results = save_path / "cluster_bc_unitType.tsv" ### hardcoded name

    if existing_results.exists()&reloadExistingResults:
        ### haven't checked if this works in this VE
        print(f"   ✅ Found existing BombCell results - loading from disk")

        # Load existing results
        try:
            param, quality_metrics, _ = bc.load_bc_results(str(save_path)) ### the third argument isn't unit_type_string so this can't work...
            unit_type,unit_type_string = get_unit_types_bombcell_from_file(ks_dir=ks_dir)
            print(f"   📊 Loaded results - Total units: {len(unit_type)}")

        except Exception as e:
            raise ### comment this if you want errors to be skipped over
            print(f"   ⚠️  Error loading existing results: {e}")
            print(f"   🔄 Will re-run BombCell analysis...")
            existing_results = None
    else:
        existing_results = None

    # Run BombCell if no existing results or loading failed
    if not existing_results or not existing_results.exists():
        print("   🚀 Running BombCell analysis...")
        param = get_preferred_bombcell_parameters(ks_dir, raw_file, kilosort_version, meta_file, gain_to_uV=None) ### I will soon want to change this to potentially be session specific... # also re: gain_to_uV being none, so as long as you have the meta file available, which you must, you'll get the meta file's gain_to_uV automatically
        if param.get("verbose", False):
            print("🚀 Running BombCell with UnitMatch parameters...")
            print(f"   - Extracting {param['nRawSpikesToExtract']} raw spikes per unit")
            print(f"   - Detrending waveforms: {param['detrendWaveform']}")
        quality_metrics, param, unit_type, unit_type_string,template_waveforms = run_bombcell_Bizley(ks_dir, save_path, param) ### Bizley style because need to remove spikes outside window. And solve other problems.

        if quality_metrics == None:
            print(f"   ✅ Analysis failed because none of the clusters have enough spikes! Either it is a shit session or you need to lower your standards")
        else:
            print(f"   ✅ Analysis complete!")
            print(f"   📊 Total units: {len(unit_type)}")

    # Check UnitMatch waveforms
    raw_waveforms_dir = save_path / "RawWaveforms"
    if raw_waveforms_dir.exists():
        waveform_files = list(raw_waveforms_dir.glob("Unit*_RawSpikes.npy"))
        print(f"   🎯 UnitMatch waveforms: {len(waveform_files)} files saved")
    else:
        print(f"   ⚠️  No UnitMatch waveforms - check raw file access")

    return {
        'name': name,
        'ks_dir': ks_dir,
        'save_path': str(save_path),
        'quality_metrics': quality_metrics,
        'param': param,
        'unit_type': unit_type,
        'unit_type_string': unit_type_string
    },template_waveforms


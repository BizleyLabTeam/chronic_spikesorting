"""Legacy runtime names backed by the selected YAML configuration."""

import spikeinterface.full as si

from config import get_legacy_data_values, get_legacy_run_values


data_values = get_legacy_data_values()
run_values = get_legacy_run_values()

catgt_location = data_values["catgt_location"]
OverStrike_location = data_values["OverStrike_location"]
desired_n_jobs = run_values["desired_n_jobs"]
si.set_global_job_kwargs(n_jobs=desired_n_jobs)

doRemoveBadChannels = run_values["doRemoveBadChannels"]
skipStuffThatKSGUIDoes = run_values["skipStuffThatKSGUIDoes"]
beginningAndEndToCutOff = run_values["beginningAndEndToCutOff"]
loadSatsFromFile = run_values["loadSatsFromFile"]
doSaturationReplace = run_values["doSaturationReplace"]
bin_s_sessionCat = run_values["bin_s_sessionCat"]
silenceOrNoiseReplace_sessionwise = run_values["silenceOrNoiseReplace_sessionwise"]
silenceOrNoiseReplace_within = run_values["silenceOrNoiseReplace_within"]
doPreprocessing = run_values["doPreprocessing"]
savePreprocessing = run_values["savePreprocessing"]
overwritePreprocessing = run_values["overwritePreprocessing"]
resaveMotionIfLoadingPreprocessing = run_values["resaveMotionIfLoadingPreprocessing"]
checkMotionPlotsOnline = run_values["checkMotionPlotsOnline"]
calculateSessionMotionDisplacement = run_values["calculateSessionMotionDisplacement"]
testingThings = run_values["testingThings"]

# Kept for modules that still import the legacy inventory names.
NAS_SessionsInOrder = []
Local_SessionsInOrder = []
NAS_SetsOfConcatenatedSessions = []
Local_SetsOfConcatenatedSessions = []
record_motion_sessions = []
record_motion_weeks = []
record_space_bins_sessions = []
record_space_bins_weeks = []
week_session_correspondance = []
week = 0
last_session_previous_week = 0


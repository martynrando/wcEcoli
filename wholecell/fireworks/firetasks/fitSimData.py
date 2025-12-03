import time
import os
import pickle
import shutil
import sys

from fireworks import FiretaskBase, explicit_serialize

from reconstruction.ecoli.fit_sim_data_1 import fitSimData_1
from wholecell.sim.simulation import DEFAULT_SIMULATION_KWARGS
from runscripts.metrics.behavior_metrics.metrics_pickle import (
	get_metrics_data_dict
)


@explicit_serialize
class FitSimDataTask(FiretaskBase):

	_fw_name = "FitSimDataTask"
	required_params = [
		"cached",
		"debug",
		"input_data",
		"output_data",
		"cpus",
		"disable_ribosome_capacity_fitting",
		"disable_rnapoly_capacity_fitting",
		"output_metrics_data",
	]
	optional_params = [
		'load_intermediate',
		'save_intermediates',
		'intermediates_directory',
		"cached_data",
		"sim_out_dir",
		'variable_elongation_transcription',
		'variable_elongation_translation',
	]

	def _get_default(self, key):
		return self.get(key, DEFAULT_SIMULATION_KWARGS[key])

	def run_task(self, fw_spec):
		print("{}: Calculating sim_data parameters".format(time.ctime()))

		if self["cached"]:
			try:
				shutil.copyfile(self["cached_data"], self["output_data"])
				with open(self["output_data"], "rb") as f:
					sim_data = pickle.load(f)
				self.save_metrics_data(sim_data)
				mod_time = time.ctime(os.path.getctime(self["cached_data"]))
				print("Copied sim data from cache (last modified {})".format(mod_time))
				return
			except Exception as exc:
				print("Warning: Could not copy cached sim data due to"
					  " exception ({}). Running Parca.".format(exc))

		cpus = self["cpus"]

		with open(self["input_data"], "rb") as f:
			raw_data = pickle.load(f)

		sim_data = fitSimData_1(
			raw_data, cpus=cpus, debug=self["debug"],
			load_intermediate=self.get('load_intermediate', None),
			save_intermediates=self.get('save_intermediates', False),
			intermediates_directory=self.get('intermediates_directory', ''),
			variable_elongation_transcription=self._get_default('variable_elongation_transcription'),
			variable_elongation_translation=self._get_default('variable_elongation_translation'),
			disable_ribosome_capacity_fitting=self['disable_ribosome_capacity_fitting'],
			disable_rnapoly_capacity_fitting=self['disable_rnapoly_capacity_fitting'],
		)

		sys.setrecursionlimit(4000)  # limit found manually
		with open(self["output_data"], "wb") as f:
			pickle.dump(sim_data, f, protocol=pickle.HIGHEST_PROTOCOL)
		self.save_metrics_data(sim_data)

	def save_metrics_data(self, sim_data):
		metrics_data = get_metrics_data_dict(sim_data)
		with open(self["output_metrics_data"], "wb") as f:
			pickle.dump(metrics_data, f, protocol=pickle.HIGHEST_PROTOCOL)

	def describe(self):
		return dict({
			"name": "FitSimDataTask",
			"task": "Fit simulation data parameters and save to {}".format(self["output_data"]),
			"comment": """
				This task uses the raw data in the knowledge base to fit simulation data parameters
				used in whole-cell simulations. You probably won't need to modify this task unless
				you are changing how simulation data is fit.
			""",
			"inputs": [
				{
					"input": "cached",
					"value": self["cached"],
					"description": "Whether to use cached sim data if available"
				},
				{
					"input": "debug",
					"value": self["debug"],
					"description": "Whether to run in debug mode"
				},
				{
					"input": "input_data",
					"value": self["input_data"],
					"description": "Path to input raw data file"
				},
				{
					"input": "cpus",
					"value": self["cpus"],
					"description": "Number of CPUs to use for fitting"
				},
				{
					"input": "disable_ribosome_capacity_fitting",
					"value": self["disable_ribosome_capacity_fitting"],
					"description": "Whether to disable ribosome capacity fitting"
				},
				{
					"input": "disable_rnapoly_capacity_fitting",
					"value": self["disable_rnapoly_capacity_fitting"],
					"description": "Whether to disable RNA polymerase capacity fitting"
				},
			],
			"outputs": [
				{
					"output": self["output_data"],
					"description": "Path to output sim data file",
					"format": "pickle"
				},
				{
					"output": self["output_metrics_data"],
					"description": "Path to output metrics data file",
					"format": "pickle"
				},
			],
			"methods": [
				"fitSimData_1 from reconstruction.ecoli.fit_sim_data_1"
			],
			"categories": [
				"data processing",
				"simulation setup"
			]
		})
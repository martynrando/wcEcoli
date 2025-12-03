import pickle
import time

from fireworks import FiretaskBase, explicit_serialize
from validation.ecoli.validation_data import ValidationDataEcoli


@explicit_serialize
class InitValidationDataTask(FiretaskBase):

	_fw_name = "InitValidationDataTask"
	required_params = [
		"validation_data_input",
		"knowledge_base_raw",
		"output_data"]

	def run_task(self, fw_spec):
		print("{}: Initializing Validation Data".format(time.ctime()))

		with open(self["validation_data_input"], "rb") as data:
			raw_validation_data = pickle.load(data)
		with open(self["knowledge_base_raw"], "rb") as raw:
			knowledge_base_raw = pickle.load(raw)
		validation_data = ValidationDataEcoli()
		validation_data.initialize(raw_validation_data, knowledge_base_raw)

		with open(self["output_data"], "wb") as fh:
			pickle.dump(validation_data, fh, protocol=pickle.HIGHEST_PROTOCOL)
	
	def describe(self):
		return dict({
			"name": "InitValidationDataTask",
			"task": "Processes validation data and save to a single object {}".format(self["output_data"]),
			"comment": """
				This is just for processing the raw validation data into a format
				usable by the simulation. You probably won't need to modify this function,
				but you may want to if you are changing how validation data is processed.
				It might also be useful to see the inner workings of the simulation.
			""",
			"inputs": [
				{
					"input": self["validation_data_input"],
					"description": "Path to raw validation data file",
					"format": "pickle"
				},
				{
					"input": self["knowledge_base_raw"],
					"description": "Path to raw knowledge base data file",
					"format": "pickle"
				}
			],
			"outputs": [
				{
					"output": self["output_data"],
					"description": "Path to output validation data file",
					"format": "pickle"
				}
			],
			"methods": [
				'ValidationDataEcoli from validation.ecoli.validation_data'
			],
			"categories": [
				"initialization",
				"validation",
			]
		})

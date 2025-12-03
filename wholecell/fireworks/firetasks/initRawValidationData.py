import pickle
import time

from fireworks import FiretaskBase, explicit_serialize
from validation.ecoli.validation_data_raw import ValidationDataRawEcoli


@explicit_serialize
class InitRawValidationDataTask(FiretaskBase):

	_fw_name = "InitRawValidationDataTask"
	required_params = ["output"]

	def run_task(self, fw_spec):
		print("%s: Instantiating validation_data_raw" % (time.ctime()))

		validation_data_raw = ValidationDataRawEcoli()

		print("%s: Saving validation_data_raw" % (time.ctime()))

		with open(self["output"], "wb") as fh:
			pickle.dump(validation_data_raw, fh, protocol=pickle.HIGHEST_PROTOCOL)

	def describe(self):
		return dict({
			"name": "InitRawValidationDataTask",
			"task": "Initialize all raw validation data and save to a single object {}".format(self["output"]),
			"comment": """
				This is probably the function you'll want to modify to change raw validation data parameters
				such as adding new validation datasets or updating existing ones. See the list of 
				experimental data files loaded in validation/ecoli/validation_data_raw.py for reference.
			""",
			"inputs": [],
			"outputs": [
				{
					"output": self["output"],
					"description": "Path to output raw validation data file",
					"format": "pickle"
				}
			],
			"methods": [
				'ValidationDataRawEcoli from validation.ecoli.validation_data_raw'
			],
			"categories": [
				"initialization",
				"validation",
			]
		})
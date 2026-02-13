import collections
import os
import sys
from typing import Any, Dict, List, Optional, Union

from fireworks import LaunchPad, Workflow, Firework, ScriptTask, FiretaskBase
from models.ecoli.sim.variants.new_gene_internal_shift import (NEW_GENE_EXPRESSION_FACTORS,
	NEW_GENE_TRANSLATION_EFFICIENCY_VALUES, NEW_GENE_INDUCTION_GEN,
	NEW_GENE_KNOCKOUT_GEN)
from wholecell.fireworks.firetasks import InitRawDataTask
from wholecell.fireworks.firetasks import InitRawValidationDataTask
from wholecell.fireworks.firetasks import InitValidationDataTask
from wholecell.fireworks.firetasks import FitSimDataTask
from wholecell.fireworks.firetasks import VariantSimDataTask
from wholecell.fireworks.firetasks import SimulationTask
from wholecell.fireworks.firetasks import SimulationDaughterTask
from wholecell.fireworks.firetasks import AnalysisParcaTask
from wholecell.fireworks.firetasks import AnalysisVariantTask
from wholecell.fireworks.firetasks import AnalysisCohortTask
from wholecell.fireworks.firetasks import AnalysisSingleTask
from wholecell.fireworks.firetasks import AnalysisMultiGenTask
from wholecell.fireworks.firetasks import AnalysisComparisonTask
from wholecell.fireworks.firetasks import BuildCausalityNetworkTask
from wholecell.sim.simulation import DEFAULT_SIMULATION_KWARGS
from wholecell.utils import constants
from wholecell.utils import filepath

#from models.ecoli.sim.variants import variants

variants = [
	'aa_synthesis_ko',
	'aa_synthesis_ko_shift',
	'aa_synthesis_sensitivity',
	'aa_uptake_sensitivity',
	'add_one_aa',
	'add_one_aa_shift',
	'condition',
	'gene_knockout',
	'mene_params',
	'metabolism_kinetic_objective_weight',
	'metabolism_secretion_penalty',
	'new_gene_internal_shift',
	'param_sensitivity',
	'ppgpp_conc',
	'ppgpp_limitations',
	'ppgpp_limitations_ribosome',
	'remove_aa_inhibition',
	'remove_aas_shift',
	'remove_one_aa',
	'remove_one_aa_shift',
	'rrna_operon_knockout',
	'rrna_location',
	'rrna_orientation',
	'tf_activity',
	'time_step',
	'timelines',
	'wildtype',
	]


WF_RULES = {
    # -------------------------
    # Description / Metadata
    # -------------------------
    "DESC": {
        "type": str,
        "default": "",
        "maxlen": 200,
        "removed_chars": r"[^a-zA-Z0-9 _\.,-]",
        "description": "A description of the simulation, used to name output folder.",
    },

    # -------------------------
    # Variant variables
    # -------------------------
    "VARIANT": {
        "type": str,
        "default": "wildtype",
        "allowed": variants,
        "description": "Specifies the environmental condition. See models/ecoli/sim/variants/*.py.",
    },
    "FIRST_VARIANT_INDEX": {
        "type": int,
        "default": 0,
        "min": 0,
        "max": 1000,
        "description": "First variant index to run.",
    },
    "LAST_VARIANT_INDEX": {
        "type": int,
        "default": 0,
        "min": 0,
        "max": 1000,
        "description": "Last variant index to run (must be >= FIRST_VARIANT_INDEX).",
    },

    # -------------------------
    # Workflow options (mostly flags)
    # -------------------------
    "CACHED_SIM_DATA": {
        "type": bool, "default": 0, "allowed": [0, 1],
        "description": "If 1, use cached parca data instead of recomputing.",
    },
    "PARALLEL_PARCA": {
        "type": bool, "default": 0, "allowed": [0, 1],
        "description": "If 1, run parca steps in parallel.",
    },
    "DEBUG_PARCA": {
        "type": bool, "default": 0, "allowed": [0, 1],
        "description": "Debug mode: compute only one TF-condition adjustment.",
    },
    "COMPRESS_OUTPUT": {
        "type": bool, "default": 0, "allowed": [0, 1],
        "description": "If 1, compress output files via bz2.",
    },
    "RUN_AGGREGATE_ANALYSIS": {
        "type": bool, "default": 1, "allowed": [0, 1],
        "description": "If 1, run aggregate and single-generation analyses.",
    },
    "PLOTS": {
        "type": list,
        "default": [],
        "allowed_set": {"DEFAULT", "CORE", "ACTIVE", "VARIANT"},
        "description": "Which analyses to run. Accepts tags such as CORE, ACTIVE, VARIANT, DEFAULT.",
    },
    "EXPORT_ECOCYC_FILES": {
        "type": bool, "default": 0, "allowed": [0, 1],
        "description": "If 1, export EcoCyc model files (requires rclone).",
    },
    "DISABLE_RIBOSOME_CAPACITY_FITTING": {
        "type": bool, "default": 0, "allowed": [0, 1],
        "description": "Disable fitting ribosome expression to protein synthesis demand.",
    },
    "DISABLE_RNAPOLY_CAPACITY_FITTING": {
        "type": bool, "default": 0, "allowed": [0, 1],
        "description": "Disable fitting RNAP expression to RNA synthesis demand.",
    },
    "WC_ANALYZE_FAST": {
        "type": bool, "default": 0, "allowed": [0, 1],
        "description": "Run each analysis plot in a separate process.",
    },
    "BUILD_CAUSALITY_NETWORK": {
        "type": bool, "default": 0, "allowed": [0, 1],
        "description": "Generate a causality network from the first sim’s output.",
    },
    "RAISE_ON_TIME_LIMIT": {
        "type": bool, "default": 0, "allowed": [0, 1],
        "description": "If 1, raise an exception if WC_LENGTHSEC is reached prematurely.",
    },

    # -------------------------
    # Simulation parameters
    # -------------------------
    "N_GENS": {
        "type": int,
        "default": 1,
        "min": 1,
        "max": 1000,
        "description": "Number of generations to simulate.",
    },
    "N_INIT_SIMS": {
        "type": int,
        "default": 1,
        "min": 1,
        "max": 100,
        "description": "Number of initial simulations.",
    },
    "SEED": {
        "type": int,
        "default": 0,
        "min": 0,
        "max": 2**31 - 1,
        "description": "Starting random seed.",
    },
    "SINGLE_DAUGHTERS": {
        "type": bool, "default": 1, "allowed": [0, 1],
        "description": "If 1, generate a single daughter instead of two.",
    },

    "TIMELINE": {
        "type": str,
        "default": "0 minimal",
        "maxlen": 200,
        "removed_chars": r"[^a-zA-Z0-9 _\.\-]",
        "description": "Timeline definition for environmental changes.",
    },

    "WC_LENGTHSEC": {
        "type": int,
        "default": 10800,
        "min": 1,
        "max": 10**7,
        "description": "Max simulation time in seconds.",
    },

    "TIMESTEP_MAX": {
        "type": float,
        "default": 1.0,
        "min": 1e-6,
        "max": 10,
        "description": "Maximum allowed timestep.",
    },
    "TIMESTEP_SAFETY_FRAC": {
        "type": float,
        "default": 1.3,
        "min": 0.1,
        "max": 10,
        "description": "Multiplier for increasing timestep when conditions are stable.",
    },
    "TIMESTEP_UPDATE_FREQ": {
        "type": int,
        "default": 5,
        "min": 1,
        "max": 1000,
        "description": "Update frequency for timestep adjustment.",
    },

    "ADJUST_TIMESTEP_FOR_CHARGING": {
        "type": bool, "default": 0, "allowed": [0, 1],
        "description": "Enable timestep adjustment during charging events.",
    },
    "LOG_TO_DISK_EVERY": {
        "type": int,
        "default": 1,
        "min": 1,
        "max": 10000,
        "description": "Frequency of writing simulation logs to disk.",
    },
    "JIT": {
        "type": bool,
        "default": 0,
        "allowed": [0, 1],
        "description": "No-op (kept for legacy compatibility).",
    },

    # -------------------------
    # Modelling options
    # -------------------------
    "MASS_DISTRIBUTION": {
        "type": bool, "default": 1, "allowed": [0, 1],
        "description": "If 1, draw a mass coefficient from N(1, σ); if 0, set mass to 1.",
    },
    "D_PERIOD_DIVISION": {
        "type": bool, "default": 1, "allowed": [0, 1],
        "description": "If 1, terminate simulation after D period instead of mass cutoff.",
    },
    "OPERONS": {
        "type": str,
        "default": "on",
        "allowed": ["off", "on", "both"],
        "description": "Control operon behaviour: monocistronic, polycistronic, or both.",
    },
    "NEW_GENES": {
        "type": str,
        "default": "off",
        "maxlen": 200,
        "removed_chars": r"[^a-zA-Z0-9_\-/]",
        "description": "Off or a folder name specifying new_gene_data inputs.",
    },
    "PDR_COMBOS": {
        "type": str,
        "default": "PDR_combo_2022",
        "allowed": ["PDR_combo_2020", "PDR_combo_2022", "PDR_combo_2025"],
        "description": "Protein degradation combination set.",
    },
    "REMOVE_RRNA_OPERONS": {
        "type": bool, "default": 0, "allowed": [0, 1],
        "description": "If 1, remove rRNA operons and express rRNAs individually.",
    },
    "REMOVE_RRFF": {
        "type": bool, "default": 0, "allowed": [0, 1],
        "description": "If 1, remove rrfF gene (and from rrnD operon if OPERONS=on).",
    },
    "STABLE_RRNA": {
        "type": bool, "default": 0, "allowed": [0, 1],
        "description": "If 1, set mature rRNA half-life to 48 hours.",
    },
    "VARIABLE_ELONGATION_TRANSCRIPTION": {
        "type": bool, "default": 1, "allowed": [0, 1],
        "description": "Enable variable transcription elongation rates.",
    },
    "VARIABLE_ELONGATION_TRANSLATION": {
        "type": bool, "default": 0, "allowed": [0, 1],
        "description": "Enable variable translation elongation rates.",
    },
    "TRANSLATION_SUPPLY": {
        "type": bool, "default": 1, "allowed": [0, 1],
        "description": "If 1, ribosome elongation is supply-limited.",
    },
    "TRNA_CHARGING": {
        "type": bool, "default": 1, "allowed": [0, 1],
        "description": "Enable tRNA charging reactions.",
    },
    "AA_SUPPLY_IN_CHARGING": {
        "type": bool, "default": 1, "allowed": [0, 1],
        "description": "Use AA supply function during charging.",
    },
    "PPGPP_REGULATION": {
        "type": bool, "default": 1, "allowed": [0, 1],
        "description": "Enable ppGpp regulation of transcription and translation.",
    },
    "DISABLE_PPGPP_ELONGATION_INHIBITION": {
        "type": bool, "default": 0, "allowed": [0, 1],
        "description": "Disable ppGpp inhibition of ribosome GTPase activity.",
    },
    "SUPERHELICAL_DENSITY": {
        "type": bool, "default": 0, "allowed": [0, 1],
        "description": "Dynamically compute DNA superhelical density.",
    },
    "RECYCLE_STALLED_ELONGATION": {
        "type": bool, "default": 0, "allowed": [0, 1],
        "description": "Recycle RNAP and fragments during stalled transcription.",
    },
    "MECHANISTIC_REPLISOME": {
        "type": bool, "default": 0, "allowed": [0, 1],
        "description": "Require correct number of subunits for replication initiation.",
    },
    "MECHANISTIC_TRANSLATION_SUPPLY": {
        "type": bool, "default": 1, "allowed": [0, 1],
        "description": "Mechanistic AA supply for translation.",
    },
    "MECHANISTIC_AA_TRANSPORT": {
        "type": bool, "default": 1, "allowed": [0, 1],
        "description": "Mechanistic amino acid transport (uptake/export).",
    },
    "TRNA_ATTENUATION": {
        "type": bool, "default": 1, "allowed": [0, 1],
        "description": "Enable transcriptional attenuation by charged tRNA.",
    },

    # -------------------------
    # Additional variables
    # -------------------------
    "LAUNCHPAD_FILE": {
        "type": str,
        "default": "my_launchpad.yaml",
        "maxlen": 200,
        "removed_chars": r"[^a-zA-Z0-9_\./-]",
        "description": "Location of FireWorks launchpad config.",
    },
    "VERBOSE_QUEUE": {
        "type": bool,
        "default": 1,
        "allowed": [0, 1],
        "description": "If 1, print detailed messages during workflow setup.",
    },

    # -------------------------
    # Environment for workflow runtime
    # -------------------------
    "DEBUG_GC": {
        "type": bool,
        "default": 0,
        "allowed": [0, 1],
        "description": "Enable leak detection in analysis plots.",
    },
}


def get_param_defaults():
    return {k: v["default"] for k, v in WF_RULES.items()}

def get_param_types():
    return {k: v["type"] for k, v in WF_RULES.items()}

def get_param_descriptions():
    return {k: v["description"] for k, v in WF_RULES.items()}


def clean_user_params(raw):
    cleaned_params = {}

    for key, rules in WF_RULES.items():
        val = raw.get(key, rules.get("default"))

        # Type coercion
        try:
            val = rules["type"](val)
        except Exception:
            raise ValueError(f"Invalid type for {key}")

        # Min & Max
        if "min" in rules and val < rules["min"]:
            raise ValueError(f"{key} must be >= {rules['min']}")
        if "max" in rules and val > rules["max"]:
            raise ValueError(f"{key} must be <= {rules['max']}")

        # Length check
        if isinstance(val, str) and "maxlen" in rules:
            if len(val) > rules["maxlen"]:
                raise ValueError(f"{key} is too long")

        # Allowed list
        if "allowed" in rules and rules["allowed"] is not None:
            if val not in rules["allowed"]:
                raise ValueError(f"{key} must be one of {rules['allowed']}")

        # Allowed tag sets like PLOTS
        if isinstance(val, list) and "allowed_set" in rules:
            bad = [t for t in val if t not in rules["allowed_set"]]
            if bad:
                raise ValueError(f"Invalid PLOTS tag(s): {bad}")

        cleaned_params[key] = val

    return cleaned_params


def prep_user_params(user_params):
    user_params["SEED"] = int(user_params["SEED"])
    user_params["N_INIT_SIMS"] = int(user_params["N_INIT_SIMS"])
    user_params["N_GENS"] = int(user_params["N_GENS"])
    user_params["WC_LENGTHSEC"] = int(user_params["WC_LENGTHSEC"])
    user_params["LOG_TO_DISK_EVERY"] = int(user_params["LOG_TO_DISK_EVERY"])
    user_params["TIMESTEP_MAX"] = float(user_params["TIMESTEP_MAX"])
    user_params["TIMESTEP_SAFETY_FRAC"] = float(user_params["TIMESTEP_SAFETY_FRAC"])
    user_params["TIMESTEP_UPDATE_FREQ"] = float(user_params["TIMESTEP_UPDATE_FREQ"])


    user_params["FIRST_VARIANT_INDEX"] = int(user_params["FIRST_VARIANT_INDEX"])
    user_params["LAST_VARIANT_INDEX"] = int(user_params["LAST_VARIANT_INDEX"])
    user_params["variants_to_run"] = list(range(
        user_params["FIRST_VARIANT_INDEX"],
        user_params["LAST_VARIANT_INDEX"] + 1
    ))
    assert user_params["OPERONS"] in constants.EXTENDED_OPERON_OPTIONS, f'{user_params["OPERONS"]=} needs to be in {constants.EXTENDED_OPERON_OPTIONS}'
    assert user_params["PDR_COMBOS"] in constants.PROTEIN_DEGRADATION_COMBO_OPTIONS, f'{user_params["PDR_COMBOS"]=} needs to be in {constants.PROTEIN_DEGRADATION_COMBO_OPTIONS}'
    user_params["sim_description"] = user_params["DESC"].replace(" ", "_")
    if not user_params["RUN_AGGREGATE_ANALYSIS"]:
        user_params["COMPRESS_OUTPUT"] = False
    
    user_params["out_dir"] = filepath.makedirs(filepath.ROOT_PATH, "out")
    user_params["cached_dir"] = os.path.join(filepath.ROOT_PATH, "cached")
    user_params["submission_time"] = filepath.timestamp()
    if "ANALYZE_FAST" in user_params:
        if user_params["ANALYZE_FAST"]:
            user_params["analysis_cpus"] = 8
        else:
            user_params["analysis_cpus"] = 1
    else:
        user_params["analysis_cpus"] = 1
    return user_params

def log_info(
        message: str, 
        indent: int = 0, 
        verbose_flag: bool = False,
        message_level: int = 0
    ) -> None:
    """Log an informational message with indentation.

    Args:
        message: The message to log.
        indent: The number of spaces to indent the message.
        verbose_flag: If True, print the message; otherwise, do nothing.
        message_level: Level of the message (0=info, 1=warning, >1=error).
    """
    if verbose_flag:
        if message_level == 0:
            print(f"{' ' * indent}{message}",  file=sys.stdout, flush=True)
            pass
        if message_level == 1:
            print(f"{' ' * indent}[Warning {message_level}] {message}",  file=sys.stdout, flush=True)
            pass
    if message_level > 1:
        print(f"{' ' * indent}[Error {message_level}] {message}",  file=sys.stdout, flush=True)
        pass
    if True:
        # For when we want to print absolutely every message regardless of verbosity
        print(f"{'>' * indent}{message}",  file=sys.stdout, flush=True)
        pass

class WorkflowBuilder:
    def __init__(self, user_params: Dict) -> None:
        self.fireworks: List[Firework] = [] # List of Fireworks in the workflow
        self.dependencies: Dict[Firework, List[Firework]] = collections.defaultdict(list) # Dependencies between Fireworks
        self.operons = ''
        self.name_suffix = ''
        self.user_params = user_params
        self.user_params["indiv_out_directory"] = filepath.makedirs(
            user_params["out_dir"], 
            f"{user_params['submission_time']}__{user_params['sim_description']}{self.name_suffix}"
        )

        log_info(f"Initialized WorkflowBuilder with user_params:", verbose_flag=self.user_params["VERBOSE_QUEUE"], message_level=-1)
        for key, value in self.user_params.items():
            log_info(f"  {key}: {value}", verbose_flag=self.user_params["VERBOSE_QUEUE"], message_level=-1)

        # AnalysisComparisonTask depends on AnalysisVariantTask
        #   and so, indirectly, on simulation tasks
        self.fw_variant_analysis = None

    def add_firework(self,
        firetask: FiretaskBase,
        name: str,
        parents: Union[None, Firework, List[Firework]] = None,
        cpus: int = 1,
        priority: Optional[int] = None,
        indent: int = 0
    ) -> Firework:
        """Add a Firework to the workflow.

        Args:
            firetask: The FiretaskBase instance to run in this Firework.
            name: Name of the Firework.
            parents: Parent Firework(s) that this Firework depends on.
            cpus: Number of CPUs to allocate for this Firework.
            priority: Priority of the Firework. Larger numbers indicate higher priority. None means lowest priority.
            indent: Indentation level for logging output.
        """
        name += self.name_suffix
        log_info(f"Adding Firework: {name}", indent=indent, verbose_flag=self.user_params["VERBOSE_QUEUE"])
        
        queue_spec = {
            'job_name': name,
            'cpus_per_task': cpus
        }
        spec: Dict[str, Any] = {
            '_queueadapter': queue_spec
        }
        if priority is not None:
            spec['_priority'] = priority

        fw = Firework(
            firetask,
            name=name,
            spec=spec,
            parents=parents
        )
        self.fireworks.append(fw)
        return fw

    def add_dependency(self, parent: Firework, *children: Firework) -> None:
        """Add a dependency between parent and child Fireworks.

        Args:
            parent: The parent Firework.
            children: The child Firework that depends on the parent.
        """
        self.dependencies[parent].extend(children)

    def build_workflow(self, operons: str) -> Workflow:
        """
            Build and return the Whole Cell Model Workflow object.
            Includes Parca, sims, analysis and output file compression.
        """
        self.operons = operons
        self.name_suffix = (
            constants.OPERON_SUFFIX if self.user_params["OPERONS"] == "both" and operons == "on"
            else ""
        )
        log_info(f"\n--- Building WCM workflow with operons={operons} ---", verbose_flag=True)
        
        self.make_output_directories()
        self.write_metadata()
        return self.build_wcm_firetasks()
    
    def make_output_directories(self, 
            SUBMISSION_TIME = filepath.timestamp()
        ) -> None:
        """
            Create output directories for the workflow and
            set self.* fields to some of those paths.
        """
        log_info("Creating output directories...", verbose_flag=self.user_params["VERBOSE_QUEUE"])
        self.INDIV_OUT_DIRECTORY = filepath.makedirs(
            self.user_params["out_dir"], 
            f"{self.user_params['submission_time']}__{self.user_params['sim_description']}{self.name_suffix}"
        )
        self.KB_DIRECTORY = filepath.makedirs(
            self.user_params["indiv_out_directory"],
            constants.KB_DIR
        )
        self.VARIANT_PLOT_DIRECTORY = filepath.makedirs(
            self.user_params["indiv_out_directory"],
            constants.PLOTOUT_DIR
        )

        number_of_individual_cells = 0
        for i in self.user_params["variants_to_run"]:
            VARIANT_DIRECTORY = filepath.makedirs(
                self.user_params["indiv_out_directory"],
                f"variant_{i:03d}"
            )
            for j in range(self.user_params["SEED"], self.user_params["SEED"] + self.user_params["N_INIT_SIMS"]):
                SEED_DIRECTORY = filepath.makedirs(
                    VARIANT_DIRECTORY,
                    f"sim_{j:03d}"
                )
                for k in range(self.user_params["N_GENS"]):
                    GEN_DIRECTORY = filepath.makedirs(
                        SEED_DIRECTORY,
                        f"gen_{k+1:03d}"
                    )
                    for l in range(2**k) if not self.user_params["SINGLE_DAUGHTERS"] else range(1):
                        CELL_DIRECTORY = filepath.makedirs(
                            GEN_DIRECTORY,
                            f"daughter_{l+1:03d}"
                        )
                        number_of_individual_cells += 1
        log_info(f"Created output directories for {number_of_individual_cells} individual cells.")
        pass  # Implementation goes here

    def write_metadata(self) -> None:
        """
            Write metadata about the workflow to the output directory.
        """
        self.metadata = {
			"git_hash": filepath.git_hash(),
			"git_branch": filepath.git_branch(),
			"description": os.environ.get("DESC", ""),
			"operons": self.operons,
			"new_genes": self.user_params["NEW_GENES"],
			"pdr_combos": self.user_params["PDR_COMBOS"],
			"remove_rrna_operons": self.user_params["REMOVE_RRNA_OPERONS"],
			"remove_rrff": self.user_params["REMOVE_RRFF"],
			"stable_rrna": self.user_params["STABLE_RRNA"],
			"time": self.user_params["submission_time"],
			"python": sys.version.splitlines()[0],
			"total_gens": self.user_params["N_GENS"],
			"total_init_sims": self.user_params["N_INIT_SIMS"],
			"analysis_type": None,
			"variant": self.user_params["VARIANT"],
			"total_variants": str(len(self.user_params["variants_to_run"])),
			"mass_distribution": self.user_params["MASS_DISTRIBUTION"],
			"d_period_division": self.user_params["D_PERIOD_DIVISION"],
			"variable_elongation_transcription": self.user_params["VARIABLE_ELONGATION_TRANSCRIPTION"],
			"variable_elongation_translation": self.user_params["VARIABLE_ELONGATION_TRANSLATION"],
			"translation_supply": self.user_params["TRANSLATION_SUPPLY"],
			"trna_charging": self.user_params["TRNA_CHARGING"],
			"aa_supply_in_charging": self.user_params["AA_SUPPLY_IN_CHARGING"],
			"ppgpp_regulation": self.user_params["PPGPP_REGULATION"],
			"disable_ppgpp_elongation_inhibition": self.user_params["DISABLE_PPGPP_ELONGATION_INHIBITION"],
			"superhelical_density": self.user_params["SUPERHELICAL_DENSITY"],
			"recycle_stalled_elongation": self.user_params["RECYCLE_STALLED_ELONGATION"],
			"mechanistic_replisome": self.user_params["MECHANISTIC_REPLISOME"],
			"mechanistic_translation_supply": self.user_params["MECHANISTIC_TRANSLATION_SUPPLY"],
			"mechanistic_aa_transport": self.user_params["MECHANISTIC_AA_TRANSPORT"],
			"trna_attenuation": self.user_params["TRNA_ATTENUATION"],
			"adjust_timestep_for_charging": self.user_params["ADJUST_TIMESTEP_FOR_CHARGING"],
		}
        METADATA_DIRECTORY = filepath.makedirs(
            self.user_params["indiv_out_directory"],
            constants.METADATA_DIR
        )
        filepath.write_json_file(
            os.path.join(METADATA_DIRECTORY, constants.JSON_METADATA_FILE),
            self.metadata
        )
        log_info("Wrote workflow metadata.", verbose_flag=self.user_params["VERBOSE_QUEUE"])
        git_diff = None # filepath.run_cmd_line("git diff HEAD", trim=False)
        if git_diff:
            filepath.write_text_file(
                os.path.join(METADATA_DIRECTORY, "git_diff.txt"),
                git_diff
            )
            log_info("Wrote git diff to metadata.", verbose_flag=self.user_params["VERBOSE_QUEUE"])
        pass  # Implementation goes here

    def build_wcm_firetasks(self) -> Workflow:
        """
            Build the Fireworks workflow for the Whole Cell Model.
            This includes all Firetasks and their dependencies.

            Call convert_to_fireworks_workflow() to get the Workflow object.
            Returns a parent for comparison analysis.
        """
        # Initialise knowledge base
        log_info("Initializing knowledge base...", verbose_flag=self.user_params["VERBOSE_QUEUE"])
        fw_init_raw_data = self.add_firework(
            InitRawDataTask(
                operons = self.operons,
                new_genes = self.user_params["NEW_GENES"],
                protein_degradation_combo = self.user_params["PDR_COMBOS"],
                remove_rrna_operons = self.user_params["REMOVE_RRNA_OPERONS"],
                remove_rrff = self.user_params["REMOVE_RRFF"],
                stable_rrna = self.user_params["STABLE_RRNA"],
                output=os.path.join(
                    self.KB_DIRECTORY,
                    constants.SERIALIZED_RAW_DATA
                )
            ),
            name="InitRawData",
            priority=12
        )

        # Calculate simulated data for variants
        log_info("Building variant simulation tasks...", verbose_flag=self.user_params["VERBOSE_QUEUE"])
        cpus_for_parca = 8 if self.user_params["PARALLEL_PARCA"] else 1
        fw_calculate_sim_data = self.add_firework(
            FitSimDataTask(
                input_data=os.path.join(
                    self.KB_DIRECTORY,
                    constants.SERIALIZED_RAW_DATA
                ),
                output_data=os.path.join(
                    self.KB_DIRECTORY,
                    constants.SERIALIZED_SIM_DATA_FILENAME
                ),
                cached = self.user_params["cached_dir"],
                cached_data = os.path.join(
                    self.user_params["cached_dir"],
                    constants.SERIALIZED_SIM_DATA_FILENAME
                ),
                cpus = cpus_for_parca,
                debug = self.user_params["DEBUG_PARCA"],
                disable_ribosome_capacity_fitting = self.user_params["DISABLE_RIBOSOME_CAPACITY_FITTING"],
                disable_rnapoly_capacity_fitting = self.user_params["DISABLE_RNAPOLY_CAPACITY_FITTING"],
                output_metrics_data=os.path.join(
                    self.KB_DIRECTORY,
                    constants.SERIALIZED_METRICS_DATA_FILENAME
                )
            ),
            name="CalculateSimData",
            parents=fw_init_raw_data,
            cpus=cpus_for_parca,
            priority=10
        )

        # Raw Knowledge Base compression
        fw_raw_data_compress = None
        if self.user_params["COMPRESS_OUTPUT"]:
            log_info("Building knowledge base compression task...", verbose_flag=self.user_params["VERBOSE_QUEUE"])
            fw_raw_data_compress = self.add_firework(
                ScriptTask(
                    script=f"bzip2 -v {os.path.join(self.KB_DIRECTORY, constants.SERIALIZED_RAW_DATA)}"
                ),
                name="CompressRawData",
                parents=fw_calculate_sim_data
            )

        # Simulation data compression
        log_info("Building simulation data compression task...", verbose_flag=self.user_params["VERBOSE_QUEUE"])
        fw_sim_data_1_compress = None
        if self.user_params["COMPRESS_OUTPUT"]:
            fw_sim_data_1_compress = self.add_firework(
                ScriptTask(
                    script=f"bzip2 -v {os.path.join(self.KB_DIRECTORY, constants.SERIALIZED_SIM_DATA_FILENAME)}"
                ),
                name="CompressSimData",
                parents=fw_calculate_sim_data
            )
        
        # Initialise raw validation data
        log_info("Initializing raw validation data...", verbose_flag=self.user_params["VERBOSE_QUEUE"])
        fw_init_raw_validation_data = self.add_firework(
            InitRawValidationDataTask(
                output=os.path.join(
                    self.KB_DIRECTORY,
                    constants.SERIALIZED_RAW_VALIDATION_DATA
                )
            ),
            name="InitRawValidationData",
            priority=12
        )

        # Raw validation data compression
        fw_raw_validation_data_compress = None
        if self.user_params["COMPRESS_OUTPUT"]:
            log_info("Building raw validation data compression task...", verbose_flag=self.user_params["VERBOSE_QUEUE"])
            fw_raw_validation_data_compress = self.add_firework(
                ScriptTask(
                    script=f"bzip2 -v {os.path.join(self.KB_DIRECTORY, constants.SERIALIZED_RAW_VALIDATION_DATA)}"
                ),
                name="CompressRawValidationData",
                parents=fw_init_raw_validation_data
            )
        
        # Initialise validation data
        log_info("Initializing validation data...", verbose_flag=self.user_params["VERBOSE_QUEUE"])
        fw_init_validation_data = self.add_firework(
            InitValidationDataTask(
                validation_data_input=os.path.join(
                    self.KB_DIRECTORY,
                    constants.SERIALIZED_RAW_VALIDATION_DATA
                ),
                knowledge_base_raw=os.path.join(
                    self.KB_DIRECTORY,
                    constants.SERIALIZED_RAW_DATA
                ),
                output_data=os.path.join(
                    self.KB_DIRECTORY,
                    constants.SERIALIZED_VALIDATION_DATA
                )
            ),
            name="InitValidationData",
            parents=[fw_init_raw_validation_data, fw_init_raw_data],
            priority=12
        )

        # Validation data compression
        fw_validation_data_compress = None
        if self.user_params["COMPRESS_OUTPUT"]:
            log_info("Building validation data compression task...", verbose_flag=self.user_params["VERBOSE_QUEUE"])
            fw_validation_data_compress = self.add_firework(
                ScriptTask(
                    script=f"bzip2 -v {os.path.join(self.KB_DIRECTORY, constants.SERIALIZED_VALIDATION_DATA)}"
                ),
                name="CompressValidationData"
            )
            self.add_dependency(
                fw_init_validation_data,
                fw_raw_validation_data_compress,
                fw_raw_data_compress
            )
        
        # Parca analysis
        fw_variant_analysis = None
        if self.user_params["RUN_AGGREGATE_ANALYSIS"]:
            log_info("Building variant analysis task...", verbose_flag=self.user_params["VERBOSE_QUEUE"])
            fw_parca_analysis = self.add_firework(
                AnalysisParcaTask(
                    input_directory=self.KB_DIRECTORY,
                    input_sim_data=os.path.join(
                        self.KB_DIRECTORY,
                        constants.SERIALIZED_SIM_DATA_FILENAME
                    ),
                    input_validation_data=os.path.join(
                        self.KB_DIRECTORY,
                        constants.SERIALIZED_VALIDATION_DATA
                    ),
                    output_plots_directory=os.path.join(
                        self.user_params["indiv_out_directory"],
                        constants.KB_PLOT_OUTPUT_DIR
                    ),
                    plot=self.user_params["PLOTS"],
                    cpus=self.user_params["analysis_cpus"],
                    metadata=self.metadata
                ),
                name="ParcaAnalysis",
                parents=[
                    fw_calculate_sim_data,
                    fw_init_validation_data
                ],
                cpus=self.user_params["analysis_cpus"],
                priority=5
            )
            if self.user_params["COMPRESS_OUTPUT"]:
                self.add_dependency(
                    fw_parca_analysis,
                    fw_sim_data_1_compress
                )
                self.add_dependency(
                    fw_parca_analysis,
                    fw_validation_data_compress
                )
        
        # Variant analysis
        log_info("Building variant analysis task...", verbose_flag=self.user_params["VERBOSE_QUEUE"])
        self.fw_variant_analysis = fw_variant_analysis = self.add_firework(
            AnalysisVariantTask(
                input_directory=self.KB_DIRECTORY,
                input_sim_data=os.path.join(
                    self.KB_DIRECTORY,
                    constants.SERIALIZED_SIM_DATA_FILENAME
                ),
                input_validation_data=os.path.join(
                    self.KB_DIRECTORY,
                    constants.SERIALIZED_VALIDATION_DATA
                ),
                output_plots_directory=self.VARIANT_PLOT_DIRECTORY,
                plot=self.user_params["PLOTS"],
                cpus=self.user_params["analysis_cpus"],
                metadata=self.metadata
            ),
            name="VariantAnalysis",
            cpus=self.user_params["analysis_cpus"],
            priority=5
        )

        # EcoCyc export
        fw_ecocyc_export = None
        if self.user_params["EXPORT_ECOCYC_FILES"]:
            log_info("Building EcoCyc export task...", verbose_flag=self.user_params["VERBOSE_QUEUE"])
            fw_ecocyc_export = self.add_firework(
                ScriptTask(
                    script=f"bash {os.path.join(filepath.ROOT_PATH, 'runscripts', 'ecocyc', 'export_ecocyc_files.sh')} " + self.user_params["indiv_out_directory"]
                ),
                name="EcoCycExport"
            )
        
        # Create variants and simulations
        log_info("Building variant and simulation tasks...", verbose_flag=self.user_params["VERBOSE_QUEUE"])
        fw_this_variant_sim_data_compression = None
        fw_this_variant_this_gen_this_sim_compression = None
        for i in self.user_params["variants_to_run"]:
            VARIANT_DIRECTORY = os.path.join(
                self.user_params["indiv_out_directory"],
                f"variant_{i:03d}"
            )
            VARIANT_SIM_DATA_DIRECTORY = os.path.join(
                VARIANT_DIRECTORY,
                constants.VKB_DIR,
            )
            VARIANT_METADATA_DIRECTORY = os.path.join(
                VARIANT_DIRECTORY,
                constants.METADATA_DIR
            )
            md_cohort = dict(
                self.metadata,
                variant_function = self.user_params["VARIANT"],
                variant_index = i
            )

            # Create variant-specific sim data
            # Note: this task doesn't depend on fw_validation_data but such a link
            # is lightweight compared to making every analysis task depend on it. (I don't know what this note means!)
            fw_this_variant_sim_data = self.add_firework(
                VariantSimDataTask(
                    variant_function=self.user_params["VARIANT"],
                    variant_index=i,
                    input_sim_data=os.path.join(
                        self.KB_DIRECTORY,
                        constants.SERIALIZED_SIM_DATA_FILENAME
                    ),
                    output_sim_data=os.path.join(
                        VARIANT_SIM_DATA_DIRECTORY,
                        constants.SERIALIZED_SIM_DATA_MODIFIED
                    ),
                    variant_metadata_directory=VARIANT_METADATA_DIRECTORY
                ),
                name=f"VariantSimData_variant_{i:03d}",
                parents=[fw_calculate_sim_data, fw_init_validation_data],
                priority=12
            )

            if self.user_params["COMPRESS_OUTPUT"]:
                self.add_dependency(
                    fw_this_variant_sim_data,
                    fw_sim_data_1_compress
                )
                fw_this_variant_sim_data_compression = self.add_firework(
                    ScriptTask(
                        script=f"bzip2 -v {os.path.join(VARIANT_SIM_DATA_DIRECTORY, constants.SERIALIZED_SIM_DATA_MODIFIED)}"
                    ),
                    name=f"CompressVariantSimData_variant_{i:03d}",
                    parents=fw_this_variant_sim_data
                )
            
            # Cohort analysis for this variant
            COHORT_PLOT_DIRECTORY = os.path.join(
                VARIANT_DIRECTORY,
                constants.PLOTOUT_DIR
            )
            fw_this_variant_analysis = None
            if self.user_params["RUN_AGGREGATE_ANALYSIS"]:
                fw_this_variant_cohort_analysis = self.add_firework(
                    AnalysisCohortTask(
                        input_variant_directory=VARIANT_DIRECTORY,
                        input_sim_data=os.path.join(
                            VARIANT_SIM_DATA_DIRECTORY,
                            constants.SERIALIZED_SIM_DATA_MODIFIED
                        ),
                        input_validation_data=os.path.join(
                            self.KB_DIRECTORY,
                            constants.SERIALIZED_VALIDATION_DATA
                        ),
                        output_plots_directory=COHORT_PLOT_DIRECTORY,
                        plot=self.user_params["PLOTS"],
                        cpus=self.user_params["analysis_cpus"],
                        metadata=md_cohort
                    ),
                    name=f"CohortAnalysis_variant_{i:03d}",
                    cpus=self.user_params["analysis_cpus"],
                    priority=5
                )

                fw_this_variant_ecocyc_analysis = None
                if self.user_params["EXPORT_ECOCYC_FILES"]:
                    fw_this_variant_ecocyc_analysis = self.add_firework(
                        AnalysisCohortTask(
                            input_variant_directory=VARIANT_DIRECTORY,
                            input_sim_data=os.path.join(
                                VARIANT_SIM_DATA_DIRECTORY,
                                constants.SERIALIZED_SIM_DATA_MODIFIED
                            ),
                            input_validation_data=os.path.join(
                                self.KB_DIRECTORY,
                                constants.SERIALIZED_VALIDATION_DATA
                            ),
                            output_plots_directory=COHORT_PLOT_DIRECTORY,
                            plot=["ecocyc"],
                            cpus=16,
                            metadata=md_cohort
                        ),
                        name=f"EcoCycAnalysis_variant_{i:03d}",
                        cpus=16,
                        priority=5
                    )
                    self.add_dependency(
                        fw_this_variant_ecocyc_analysis,
                        fw_ecocyc_export
                    )
                
                fw_this_variant_this_seed_multigen_analysis = None
                for j in range(self.user_params["SEED"], self.user_params["SEED"] + self.user_params["N_INIT_SIMS"]):
                    SEED_DIRECTORY = os.path.join(
                        VARIANT_DIRECTORY,
                        f"sim_{j:03d}"
                    )
                    SEED_PLOT_DIRECTORY = os.path.join(
                        SEED_DIRECTORY,
                        constants.PLOTOUT_DIR
                    )
                    md_multigen = dict(
                        md_cohort,
                        seed=j
                    )

                    if self.user_params["RUN_AGGREGATE_ANALYSIS"]:
                        fw_this_variant_this_seed_multigen_analysis = self.add_firework(
                            AnalysisMultiGenTask(
                                input_seed_directory=SEED_DIRECTORY,
                                input_sim_data=os.path.join(
                                    VARIANT_SIM_DATA_DIRECTORY,
                                    constants.SERIALIZED_SIM_DATA_MODIFIED
                                ),
                                input_validation_data=os.path.join(
                                    self.KB_DIRECTORY,
                                    constants.SERIALIZED_VALIDATION_DATA
                                ),
                                output_plots_directory=SEED_PLOT_DIRECTORY,
                                plot=self.user_params["PLOTS"],
                                cpus=self.user_params["analysis_cpus"],
                                metadata=md_multigen
                            ),
                            name=f"MultigenAnalysis_variant_{i:03d}_seed_{j:03d}",
                            cpus=self.user_params["analysis_cpus"],
                            priority=3,
                            indent=1
                        )
                        if self.user_params["COMPRESS_OUTPUT"]:
                            self.add_dependency(
                                fw_this_variant_this_seed_multigen_analysis,
                                fw_this_variant_sim_data_compression
                            )
                    
                    sims_this_seed = collections.defaultdict(list)

                    for k in range(self.user_params["N_GENS"]):
                        GEN_DIRECTORY = os.path.join(
                            SEED_DIRECTORY,
                            f"gen_{k:03d}"
                        )
                        md_single = dict(
                            md_multigen,
                            gen=k
                        )

                        for l in range(2**k) if not self.user_params["SINGLE_DAUGHTERS"] else range(1):
                            CELL_DIRECTORY = os.path.join(
                                GEN_DIRECTORY,
                                f"daughter_{l:03d}"
                            )
                            CELL_SIM_OUT_DIRECTORY = os.path.join(
                                CELL_DIRECTORY,
                                "simOut"
                            )
                            CELL_PLOT_OUT_DIRECTORY = os.path.join(
                                CELL_DIRECTORY,
                                constants.PLOTOUT_DIR
                            )
                            CELL_SERIES_OUT_DIRECTORY = os.path.join(
                                CELL_DIRECTORY,
                                "seriesOut"
                            )

                            # Simulation task for this cell
                            sim_fw_name = f"Sim_variant_{i:03d}_seed_{j:03d}_gen_{k:03d}_daughter_{l:03d}"
                            sim_task_args = dict(
                                input_sim_data=os.path.join(
                                    VARIANT_SIM_DATA_DIRECTORY,
                                    constants.SERIALIZED_SIM_DATA_MODIFIED
                                ),
                                output_directory=CELL_SIM_OUT_DIRECTORY,
                                timeline = self.user_params["TIMELINE"],
                                length_sec = self.user_params["WC_LENGTHSEC"],
                                timestep_safety_frac = self.user_params["TIMESTEP_SAFETY_FRAC"],
                                timestep_max = self.user_params["TIMESTEP_MAX"],
                                timestep_update_freq = self.user_params["TIMESTEP_UPDATE_FREQ"],
                                adjust_timestep_for_charging = self.user_params["ADJUST_TIMESTEP_FOR_CHARGING"],
                                log_to_disk_every = self.user_params["LOG_TO_DISK_EVERY"],
                                jit = self.user_params["JIT"],
                                mass_distribution = self.user_params["MASS_DISTRIBUTION"],
                                d_period_division = self.user_params["D_PERIOD_DIVISION"],
                                variable_elongation_transcription = self.user_params["VARIABLE_ELONGATION_TRANSCRIPTION"],
                                variable_elongation_translation = self.user_params["VARIABLE_ELONGATION_TRANSLATION"],
                                translation_supply = self.user_params["TRANSLATION_SUPPLY"],
                                trna_charging = self.user_params["TRNA_CHARGING"],
                                aa_supply_in_charging = self.user_params["AA_SUPPLY_IN_CHARGING"],
                                ppgpp_regulation = self.user_params["PPGPP_REGULATION"],
                                disable_ppgpp_elongation_inhibition = self.user_params["DISABLE_PPGPP_ELONGATION_INHIBITION"],
                                superhelical_density = self.user_params["SUPERHELICAL_DENSITY"],
                                recycle_stalled_elongation = self.user_params["RECYCLE_STALLED_ELONGATION"],
                                mechanistic_replisome = self.user_params["MECHANISTIC_REPLISOME"],
                                mechanistic_translation_supply = self.user_params["MECHANISTIC_TRANSLATION_SUPPLY"],
                                mechanistic_aa_transport = self.user_params["MECHANISTIC_AA_TRANSPORT"],
                                trna_attenuation = self.user_params["TRNA_ATTENUATION"],
                                raise_on_time_limit = self.user_params["RAISE_ON_TIME_LIMIT"]
                            )
                        
                            if k==0:
                                fw_this_variant_this_gen_this_sim = self.add_firework(
                                    SimulationTask(
                                        seed = j,
                                        **sim_task_args
                                    ),
                                    name=sim_fw_name,
                                    cpus=1,
                                    priority=10,
                                    indent=2
                                )
                            elif k>0:
                                PARENT_GEN_DIRECTORY = os.path.join(
                                    SEED_DIRECTORY,
                                    f"gen_{k-1:03d}"
                                )
                                PARENT_CELL_DIRECTORY = os.path.join(
                                    PARENT_GEN_DIRECTORY,
                                    f"daughter_{l//2:03d}"
                                )
                                PARENT_CELL_SIM_OUT_DIRECTORY = os.path.join(
                                    PARENT_CELL_DIRECTORY,
                                    "simOut"
                                )
                                DAUGHTER_STATE_PATH = os.path.join(
                                    PARENT_CELL_SIM_OUT_DIRECTORY,
                                    constants.SERIALIZED_INHERITED_STATE % (l%2+1)
                                )

                                fw_this_variant_this_gen_this_sim = self.add_firework(
                                    SimulationDaughterTask(
                                        inherited_state_path = DAUGHTER_STATE_PATH,
                                        seed = (j+1) * ((2**k-1)+l),
                                        **sim_task_args
                                    ),
                                    name=sim_fw_name,
                                    cpus=1,
                                    priority=10,
                                    indent=2
                                )
                            else:
                                raise ValueError(f"Unexpected generation number: {k}")
                            
                            # add the last generation as dependencies for the multiple sim analysis
                            if k == self.user_params["N_GENS"] - 1 and self.user_params["RUN_AGGREGATE_ANALYSIS"]:
                                self.add_dependency(
                                    fw_this_variant_this_gen_this_sim,
                                    fw_this_variant_this_seed_multigen_analysis,
                                    fw_this_variant_cohort_analysis,
                                    fw_variant_analysis
                                )
                            if self.user_params["EXPORT_ECOCYC_FILES"]:
                                self.add_dependency(
                                    fw_this_variant_this_gen_this_sim,
                                    fw_this_variant_ecocyc_analysis
                                )
                            sims_this_seed[k].append(fw_this_variant_this_gen_this_sim)
                            if k==0:
                                self.add_dependency(
                                    fw_this_variant_sim_data,
                                    fw_this_variant_this_gen_this_sim
                                )
                            elif k>0:
                                fw_parent_sim = sims_this_seed[k-1][l//2]
                                self.add_dependency(
                                    fw_parent_sim,
                                    fw_this_variant_this_gen_this_sim
                                )
                            
                            if self.user_params["COMPRESS_OUTPUT"]:
                                fw_this_variant_this_gen_this_sim_compression = self.add_firework(
                                    ScriptTask(
                                        script='for dir in %s; do echo "Compressing $dir"; find "$dir" -type f| xargs bzip2; done' % os.path.join(
                                            CELL_SIM_OUT_DIRECTORY,
                                            "*"
                                        )
                                    ),
                                    name=f"CompressSim_variant_{i:03d}_seed_{j:03d}_gen_{k:03d}_daughter_{l:03d}",
                                    priority=0
                                )
                            
                            if self.user_params["RUN_AGGREGATE_ANALYSIS"]:
                                fw_this_variant_this_gen_this_sim_analysis = self.add_firework(
                                    AnalysisSingleTask(
                                        input_results_directory=CELL_SIM_OUT_DIRECTORY,
                                        input_sim_data=os.path.join(
                                            VARIANT_SIM_DATA_DIRECTORY,
                                            constants.SERIALIZED_SIM_DATA_MODIFIED
                                        ),
                                        input_validation_data=os.path.join(
                                            self.KB_DIRECTORY,
                                            constants.SERIALIZED_VALIDATION_DATA
                                        ),
                                        output_plots_directory=CELL_PLOT_OUT_DIRECTORY,
                                        plot=self.user_params["PLOTS"],
                                        cpus=self.user_params["analysis_cpus"],
                                        metadata=md_single
                                    ),
                                    name=f"SingleSimAnalysis_variant_{i:03d}_seed_{j:03d}_gen_{k:03d}_daughter_{l:03d}",
                                    cpus=self.user_params["analysis_cpus"],
                                    priority=1,
                                    indent=3
                                )
                            
                                if self.user_params["COMPRESS_OUTPUT"]:
                                    data_fws = [
                                        fw_this_variant_this_gen_this_sim_analysis,
                                        fw_this_variant_this_seed_multigen_analysis,
                                        fw_this_variant_cohort_analysis,
                                        fw_variant_analysis
                                    ]
                                    for data in data_fws:
                                        self.add_dependency(
                                            data,
                                            fw_this_variant_sim_data_compression,
                                            fw_validation_data_compress,
                                            fw_this_variant_this_gen_this_sim_compression
                                        )
                            
                            if self.user_params["BUILD_CAUSALITY_NETWORK"]:
                                self.user_params["BUILD_CAUSALITY_NETWORK"] = False # only do it once per model run!
                                fw_this_variant_this_gen_this_sim_causality_network = self.add_firework(
                                    BuildCausalityNetworkTask(
                                        input_results_directory=CELL_SIM_OUT_DIRECTORY,
                                        input_sim_data=os.path.join(
                                            VARIANT_SIM_DATA_DIRECTORY,
                                            constants.SERIALIZED_SIM_DATA_MODIFIED
                                        ),
                                        output_dynamics_directory=CELL_SERIES_OUT_DIRECTORY,
                                        metadata=md_single
                                    ),
                                    name=f"CausalityNetwork_variant_{i:03d}_seed_{j:03d}_gen_{k:03d}_daughter_{l:03d}",
                                    cpus=self.user_params["analysis_cpus"],
                                    priority=2,
                                    indent=3
                                )

                                if self.user_params["COMPRESS_OUTPUT"]:
                                    self.add_dependency(
                                        fw_this_variant_this_gen_this_sim_causality_network,
                                        fw_this_variant_sim_data_compression,
                                        fw_this_variant_this_gen_this_sim_compression
                                    )

        pass  # Implementation goes here

    def add_comparison_analysis(
        self,
        reference_sim_dir: str,
        reference_variant_analysis: Firework
    ) -> None:
        """
        Add an AnalysisComparisonTask that compares the WCM workflow results to a reference simulation.
        """
        log_info("Building comparison analysis task...", verbose_flag=self.user_params["VERBOSE_QUEUE"])
        if self.user_params["RUN_AGGREGATE_ANALYSIS"]:
            plot_out_dir = os.path.join(
                self.user_params["indiv_out_directory"],
                constants.COMPARISON_PLOTOUT_DIR
            )
            self.add_firework(
                AnalysisComparisonTask(
                    reference_sim_dir=reference_sim_dir,
                    input_sim_dir=self.user_params["indiv_out_directory"],
                    output_plots_directory=plot_out_dir,
                    plot=self.user_params["PLOTS"],
                    cpus=self.user_params["analysis_cpus"],
                    metadata=self.metadata
                ),
                name="ComparisonAnalysis",
                parents=[reference_variant_analysis, self.fw_variant_analysis],
                cpus=self.user_params["analysis_cpus"],
                priority=4
            )
    
    def convert_to_fireworks_workflow(self) -> Workflow:
        """
        Convert the internal representation to a FireWorks Workflow object
        using the Firetask and dependency information stored in the builder.
        """
        return Workflow(self.fireworks, links_dict=self.dependencies)



    def describe(self) -> None:
        """
            Print a description of the workflow.
        """
        log_info("\n--- Workflow Summary ---")
        log_info(f"Total Fireworks: {len(self.wf_fws)}")
        total_links = sum(len(v) for v in self.wf_links.values())
        log_info(f"Total Dependency Links: {total_links}")
        log_info("------------------------\n")
        log_info("\n--- Task List ---")
        for fw in self.wf_fws:
            log_info(f"\nFirework: {fw.name}, Parents: {[p.name for p in fw.parents]}, Children: {[c.name for c in self.wf_links.get(fw, [])]}")
            log_info(f"\nDescribe: \n")
            desc = "\n".join(f"  {key}: {value}" for key, value in fw.describe().items())
            log_info(desc)
            log_info("\n------------------------")
    
    def convert_to_fireworks_workflow(self) -> Workflow:
        """
            Convert the internal representation to a FireWorks Workflow object
            using the Firetask and dependency information stored in the builder.
        """
        return Workflow(self.wf_fws, links_dict=self.wf_links)

def upload(fireworks_workflow, launchpad_file) -> None:
    """
        Upload the workflow to the FireWorks launchpad.
    """
    lpad = LaunchPad.from_file(launchpad_file)
    lpad.add_wf(fireworks_workflow)
    log_info("Workflow uploaded to launchpad.", verbose_flag=True)
    #self.lpad = LaunchPad.from_file(self.user_params["LAUNCHPAD_FILE"])

def build_and_submit(user_params = None):
    if not user_params:
        user_params = clean_user_params(get_param_defaults())
    user_params = prep_user_params(user_params=user_params)
    builder = WorkflowBuilder(user_params=user_params)

    if user_params["OPERONS"] == 'both':
        builder.build_workflow(operons='off')
        sim_dir1 = builder.user_params["indiv_out_directory"]
        variant_analysis1 = builder.fw_variant_analysis
        builder.build_workflow(operons='on')
        #builder.add_comparison_analysis(reference_sim_dir=sim_dir1, reference_variant_analysis=variant_analysis1)
    else:
        builder.build_workflow(operons=user_params["OPERONS"])
    wf = builder.convert_to_fireworks_workflow()
    upload(wf, user_params["LAUNCHPAD_FILE"])

if __name__ == "__main__":
    build_and_submit()
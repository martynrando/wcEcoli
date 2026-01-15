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


def launch_workflow(user_params):
    variants_to_run = list(range(
        user_params["FIRST_VARIANT_INDEX"],
        user_params["LAST_VARIANT_INDEX"] + 1
    ))
    assert user_params["OPERONS"] in constants.EXTENDED_OPERON_OPTIONS, f'{user_params["OPERONS"]=} needs to be in {constants.EXTENDED_OPERON_OPTIONS}'
    assert user_params["PDR_COMBOS"] in constants.PROTEIN_DEGRADATION_COMBO_OPTIONS, f'{user_params["PDR_COMBOS"]=} needs to be in {constants.PROTEIN_DEGRADATION_COMBO_OPTIONS}'
    sim_description = user_params["DESC"].replace(" ", "_")
    if not user_params["RUN_AGGREGATE_ANALYSIS"]:
        user_params["COMPRESS_OUTPUT"] = False
    
    out_dir = filepath.makedirs(filepath.ROOT_PATH, "out")
    cached_dir = os.path.join(filepath.ROOT_PATH, "cached")
    submission_time = filepath.timestamp()
    if user_params["ANALYZE_FAST"]:
        analysis_cpus = 8
    else:
        analysis_cpus = 1

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
            print(f"{' ' * indent}{message}")
        elif message_level == 1:
            print(f"{' ' * indent}[Warning {message_level}] {message}")
    if message_level > 1:
        print(f"{' ' * indent}[Error {message_level}] {message}")

class WorkflowBuilder:
    def __init__(self, user_params: Dict) -> None:
        self.fireworks: List[Firework] = [] # List of Fireworks in the workflow
        self.dependencies: Dict[Firework, List[Firework]] = collections.defaultdict(list) # Dependencies between Fireworks
        self.operons = ''
        self.name_suffix = ''
        self.user_params = user_params

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
        self.wf_links[parent].extend(children)

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
        log_info(f"\n--- Building WCM workflow with operons={operons} ---", indent=0, verbose_flag=True)
        
        self.make_output_directories()
        self.write_metadata()
        return self.build_wcm_firetasks()
    
    def make_output_directories(self) -> None:
        """
            Create output directories for the workflow and
            set self.* fields to some of those paths.
        """
        pass  # Implementation goes here

    def write_metadata(self) -> None:
        """
            Write metadata about the workflow to the output directory.
        """
        pass  # Implementation goes here

    def build_wcm_firetasks(self) -> Workflow:
        """
            Build the Fireworks workflow for the Whole Cell Model.
        """
        pass  # Implementation goes here

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
    
    def upload(self) -> None:
        """
            Upload the workflow to the FireWorks launchpad.
        """
        #lpad = LaunchPad.from_file(self.user_params["LAUNCHPAD_FILE"])
        #lpad.add_wf(self.convert_to_fireworks_workflow())
        log_info("Workflow uploaded to launchpad.", verbose_flag=True)
        self.lpad = LaunchPad.from_file(self.user_params["LAUNCHPAD_FILE"])
    
    def convert_to_fireworks_workflow(self) -> Workflow:
        """
            Convert the internal representation to a FireWorks Workflow object
            using the Firetask and dependency information stored in the builder.
        """
        return Workflow(self.wf_fws, links_dict=self.wf_links)
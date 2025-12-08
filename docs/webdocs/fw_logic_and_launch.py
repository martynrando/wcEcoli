from models.ecoli.sim.variants import variants


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
    cleaned = {}

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

        cleaned[key] = val

    return cleaned